"""在独立桌面验证真实运行时的图标更新与失败保留行为。"""

import argparse
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import time

from PIL import Image
import websocket
import win32gui
import win32ui


def make_bundle(output, config, icon):
    files = {
        "neutralino.config.json": json.dumps(config).encode("utf-8"),
        "index.html": b'<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>',
        "icon.png": icon.read_bytes(),
    }
    entries, data = {}, bytearray()
    for name, content in files.items():
        entries[name] = {"size": len(content), "offset": str(len(data))}
        data.extend(content)
    header = json.dumps({"files": entries}, separators=(",", ":")).encode("utf-8")
    header_length = len(header)
    header += b" " * (-len(header) % 4)
    # resources.cpp 从第 16 字节读取 JSON，文件数据紧随完整头部。
    prefix = struct.pack("<4I", 4, len(header) + 8, len(header) + 4, header_length)
    (output / "resources.neu").write_bytes(prefix + header + data)


def icon_details(handle):
    if not handle:
        return {"handle": 0, "size": None, "alpha_nonempty": False}
    info = win32gui.GetIconInfo(handle)
    try:
        bitmap = win32ui.CreateBitmapFromHandle(info[4])
        meta = bitmap.GetInfo()
        image = Image.frombytes(
            "RGBA", (meta["bmWidth"], meta["bmHeight"]), bitmap.GetBitmapBits(True),
            "raw", "BGRA", meta["bmWidthBytes"], 1,
        )
        return {"handle": handle, "size": list(image.size),
                "alpha_nonempty": bool(image.getchannel("A").getbbox()),
                "rgba_extrema": [list(bounds) for bounds in image.getextrema()]}
    finally:
        for bitmap in info[3:]:
            if bitmap:
                win32gui.DeleteObject(bitmap)


def window_icons(capture, hwnd):
    icons = {}
    for label, kind in (("small", 0), ("big", 1)):
        handle = C.c_size_t()
        status = capture.USER32.SendMessageTimeoutW(hwnd, 0x007F, kind, None, 2, 500, C.byref(handle))
        if not status:
            raise RuntimeError("读取窗口图标超时")
        icons[label] = icon_details(handle.value)
    return icons


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError("图标验证超过 40 秒")
    return min(3, seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "capture-module", "output", "icon"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    runtime, source = args.runtime.resolve(strict=True), args.icon.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("capture", args.capture_module.resolve(strict=True))
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    title = "窗口图标更新验证"
    config = {
        "applicationId": "dlcv.icon.updates", "defaultMode": "window", "port": 0,
        "url": "/index.html", "documentRoot": "/", "enableServer": True,
        "enableNativeAPI": True, "nativeAllowList": ["window.*"], "exportAuthInfo": True,
        "logging": {"enabled": False, "writeToLogFile": False},
        "modes": {"window": {"title": title, "width": 640, "height": 480,
                             "hidden": False, "useSavedState": False, "enableInspector": False}},
    }
    with Image.open(source) as image:
        assert image.format == "PNG", "输入文件必须为 PNG"
        input_size = list(image.size)
        assert image.convert("RGBA").getchannel("A").getbbox(), "输入 PNG 完全透明"
    local_icon, unicode_icon = output / "local.png", output / "中文图标.png"
    shutil.copyfile(source, local_icon)
    unicode_color = (31, 133, 201, 255)
    Image.new("RGBA", input_size, unicode_color).save(unicode_icon)
    (output / "invalid.png").write_bytes(b"not a PNG")
    (output / "empty.png").write_bytes(b"")
    make_bundle(output, config, local_icon)
    environment = os.environ.copy()
    for key in ("APPDATA", "LOCALAPPDATA", "USERPROFILE", "HOME", "TEMP", "TMP", "TMPDIR"):
        environment[key] = str(output)
    name = "DLCV_icon_updates_" + secrets.token_hex(8)
    desktop = job = connection = None
    handles = []
    result = {"passed": False, "stage": "初始化", "input_size": input_size, "cases": []}
    auth_path = output / ".tmp" / "auth_info.json"
    previous_dpi = capture.USER32.SetThreadDpiAwarenessContext(C.c_void_p(-4))
    deadline = time.monotonic() + 40
    try:
        assert previous_dpi, "设置采集线程 DPI 模式失败"
        desktop = capture.USER32.CreateDesktopW(name, None, None, 0, capture.DESKTOP_ACCESS, None)
        assert desktop, "创建独立桌面失败"
        input_name = capture.ensure_desktop(desktop, name)
        job = capture.create_job("Local\\" + name)
        explorer, explorer_pid = capture.start_in_job(
            Path(os.environ["SystemRoot"]) / "explorer.exe", [], output, environment, name, job,
        )
        handles.append(explorer)
        process, pid = capture.start_in_job(runtime, ["--path=."], output, environment, name, job)
        handles.append(process)
        result.update(pid=pid, explorer_pid=explorer_pid)
        windows = []
        callback_type = C.WINFUNCTYPE(capture.BOOL, capture.PTR, C.c_ssize_t)

        def collect(hwnd, unused):
            owner = capture.DWORD()
            capture.USER32.GetWindowThreadProcessId(hwnd, C.byref(owner))
            if (owner.value == pid and win32gui.GetClassName(hwnd) == "Neutralinojs_webview"
                    and capture.USER32.IsWindowVisible(hwnd)):
                windows.append(hwnd)
                return False
            return True

        callback = callback_type(collect)
        while (not windows or not auth_path.is_file()
               or win32gui.GetWindowText(windows[0]) != title):
            remaining(deadline)
            if capture.KERNEL32.WaitForSingleObject(process, 0) == capture.WAIT_OBJECT_0:
                raise RuntimeError("原生运行时在初始化完成前退出")
            if not windows:
                capture.USER32.EnumDesktopWindows(desktop, callback, 0)
                if windows:
                    result["first_visible_icons"] = window_icons(capture, windows[0])
            time.sleep(0.05)
        assert capture.in_job(pid, job), "目标进程不属于本次 Job"
        hwnd = windows[0]
        result["hwnd"] = hwnd
        dpi = capture.USER32.GetDpiForWindow(hwnd)
        assert dpi, "读取目标窗口 DPI 失败"
        metric = capture.USER32.GetSystemMetricsForDpi
        metric.argtypes, metric.restype = [C.c_int, C.c_uint], C.c_int
        expected_size = {"small": [metric(49, dpi), metric(50, dpi)],
                         "big": [metric(11, dpi), metric(12, dpi)]}
        assert all(size > 0 for dimensions in expected_size.values() for size in dimensions)
        result.update(dpi=dpi, expected_size=expected_size)
        result["initial_icons"] = window_icons(capture, hwnd)
        result["initial_passed"] = all(
            icon["handle"] and icon["size"] == expected_size[kind] and icon["alpha_nonempty"]
            for stage in ("first_visible_icons", "initial_icons")
            for kind, icon in result[stage].items()
        )
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
        result["stage"] = "连接原生 API"
        connection = websocket.create_connection(
            f"ws://127.0.0.1:{auth['nlPort']}?connectToken={auth['nlConnectToken']}",
            timeout=remaining(deadline), http_no_proxy=["127.0.0.1"],
        )
        cases = (
            ("包内 PNG", "/icon.png", None),
            ("本地绝对路径 PNG", str(local_icon), None),
            ("中文绝对路径 PNG", str(unicode_icon), None),
            ("缺失本地文件", str(output / "missing.png"), "NE_FS_FILRDER"),
            ("缺失包内资源", "/missing.png", "NE_RS_TREEGER"),
            ("非法 PNG", str(output / "invalid.png"), "NE_WI_ICONERR"),
            ("零字节 PNG", str(output / "empty.png"), "NE_WI_ICONERR"),
        )
        for index, (label, path, expected_error) in enumerate(cases):
            result["stage"] = label
            remaining(deadline)
            assert capture.ensure_desktop(desktop, name) == input_name, "输入桌面发生变化"
            record = {"name": label, "passed": False}
            result["cases"].append(record)
            record["before"] = window_icons(capture, hwnd)
            connection.settimeout(remaining(deadline))
            connection.send(json.dumps({"id": str(index), "method": "window.setIcon",
                                       "data": {"icon": path}, "accessToken": auth["nlToken"]}))
            while True:
                connection.settimeout(remaining(deadline))
                response = json.loads(connection.recv())
                if response.get("id") == str(index):
                    break
            record["response"] = response["data"]
            record["after"] = window_icons(capture, hwnd)
            if expected_error:
                record["expected_error"] = expected_error
                record["passed"] = (
                    response["data"].get("error", {}).get("code") == expected_error
                    and "success" not in response["data"]
                    and all(record["before"][kind]["handle"] == record["after"][kind]["handle"]
                            for kind in ("small", "big"))
                )
            else:
                record["passed"] = response["data"].get("success") is True and all(
                    icon["handle"] and icon["size"] == expected_size[kind] and icon["alpha_nonempty"]
                    and icon["handle"] != record["before"][kind]["handle"]
                    for kind, icon in record["after"].items()
                )
                if path == str(unicode_icon):
                    record["expected_rgba"] = list(unicode_color)
                    record["passed"] = record["passed"] and all(
                        icon.get("rgba_extrema") == [[value, value] for value in unicode_color]
                        for icon in record["after"].values()
                    )
        result["passed"] = result["initial_passed"] and all(record["passed"] for record in result["cases"])
        result["stage"] = "验证完成"
    except Exception as exc:
        # WebSocket 异常可能携带握手 URL，只记录异常类型以免写出凭证。
        result["error_type"] = type(exc).__name__
    finally:
        if job:
            capture.KERNEL32.TerminateJobObject(job, 0)
        if connection:
            try:
                connection.close(timeout=0)
            except Exception:
                pass
        for handle in handles:
            capture.KERNEL32.WaitForSingleObject(handle, 1000)
            capture.KERNEL32.CloseHandle(handle)
        if job:
            capture.KERNEL32.CloseHandle(job)
        if desktop:
            capture.USER32.CloseDesktop(desktop)
        if previous_dpi:
            capture.USER32.SetThreadDpiAwarenessContext(previous_dpi)
        try:
            auth_path.unlink(missing_ok=True)
        except OSError:
            pass
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
