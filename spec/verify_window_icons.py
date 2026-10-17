"""读取本次隔离窗口首次创建时的类图标，不操作输入桌面。"""

import argparse
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import time

from PIL import Image
import win32gui
import win32ui


def save_icon(handle, output):
    info = win32gui.GetIconInfo(handle)
    try:
        bitmap = win32ui.CreateBitmapFromHandle(info[4])
        meta = bitmap.GetInfo()
        image = Image.frombytes(
            "RGBA", (meta["bmWidth"], meta["bmHeight"]), bitmap.GetBitmapBits(True),
            "raw", "BGRA", meta["bmWidthBytes"], 1,
        )
        assert image.getchannel("A").getbbox(), "窗口类图标完全透明"
        image.save(output)
        return list(image.size)
    finally:
        for bitmap in info[3:]:
            if bitmap:
                win32gui.DeleteObject(bitmap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--capture-module", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-missing", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("capture", args.capture_module)
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    config = {
        "applicationId": "dlcv.icon.check", "defaultMode": "window", "port": 0,
        "url": "/", "documentRoot": "/", "enableServer": True,
        "logging": {"enabled": False, "writeToLogFile": False},
        "modes": {"window": {"title": "图标验证", "width": 640, "height": 480}},
    }
    (output / "neutralino.config.json").write_text(json.dumps(config), encoding="utf-8")
    environment = os.environ.copy()
    environment["APPDATA"] = str(output / "profile")
    Path(environment["APPDATA"]).mkdir()
    environment.update(TEMP=str(output), TMP=str(output), TMPDIR=str(output))
    name = "DLCV_icon_" + secrets.token_hex(8)
    desktop = capture.USER32.CreateDesktopW(name, None, None, 0, capture.DESKTOP_ACCESS, None)
    assert desktop, "创建隔离桌面失败"
    job = process = None
    result = {}
    try:
        input_name = capture.ensure_desktop(desktop, name)
        job = capture.create_job("Local\\" + name)
        process, pid = capture.start_in_job(
            args.runtime.resolve(), ["--load-dir-res", "--path=."], output,
            environment, name, job,
        )
        getter = capture.USER32.GetClassLongPtrW
        getter.argtypes, getter.restype = [capture.PTR, C.c_int], capture.PTR
        callback_type = C.WINFUNCTYPE(capture.BOOL, capture.PTR, C.c_ssize_t)

        def collect(hwnd, unused):
            owner = capture.DWORD()
            capture.USER32.GetWindowThreadProcessId(hwnd, C.byref(owner))
            if owner.value != pid or win32gui.GetClassName(hwnd) != "Neutralinojs_webview":
                return True
            assert capture.in_job(owner.value, job)
            for label, index in (("small", -34), ("big", -14)):
                handle = getter(hwnd, index)
                result[label] = save_icon(handle, output / f"{label}.png") if handle else None
            result["pid"] = pid
            return False

        callback = callback_type(collect)
        deadline = time.monotonic() + 15
        while not result and time.monotonic() < deadline:
            capture.USER32.EnumDesktopWindows(desktop, callback, 0)
            time.sleep(0.005)
        assert result, "未发现本次原生窗口"
        assert capture.ensure_desktop(desktop, name) == input_name
        expected = {"small": None, "big": None} if args.expect_missing else {
            "small": [capture.USER32.GetSystemMetrics(49), capture.USER32.GetSystemMetrics(50)],
            "big": [capture.USER32.GetSystemMetrics(11), capture.USER32.GetSystemMetrics(12)],
        }
        assert {key: result[key] for key in expected} == expected, result
        result["passed"] = True
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        if job:
            capture.KERNEL32.TerminateJobObject(job, 0)
        if process:
            capture.KERNEL32.WaitForSingleObject(process, 3000)
            capture.KERNEL32.CloseHandle(process)
        if job:
            capture.KERNEL32.CloseHandle(job)
        capture.USER32.CloseDesktop(desktop)
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.rmtree(output / "profile", ignore_errors=True)


if __name__ == "__main__":
    main()
