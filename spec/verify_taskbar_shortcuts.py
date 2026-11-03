"""用独立用户目录中的真实快捷方式验证原生启动时的图标修正。"""

import argparse
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid

from PIL import Image
import pythoncom
from win32com.propsys import propsys, pscon
from win32com.shell import shell
import win32gui


PROPERTIES = {
    "appid": pscon.PKEY_AppUserModel_ID,
    "relaunch_command": pscon.PKEY_AppUserModel_RelaunchCommand,
    "relaunch_icon": pscon.PKEY_AppUserModel_RelaunchIconResource,
    "relaunch_name": pscon.PKEY_AppUserModel_RelaunchDisplayNameResource,
}


def known_folder(identifier, output):
    shell32 = C.WinDLL("shell32", use_last_error=True)
    ole32 = C.WinDLL("ole32", use_last_error=True)
    shell32.SHGetKnownFolderPath.argtypes = [C.c_void_p, C.c_uint, C.c_void_p, C.POINTER(C.c_void_p)]
    shell32.SHGetKnownFolderPath.restype = C.c_long
    ole32.CoTaskMemFree.argtypes = [C.c_void_p]
    identifier = (C.c_byte * 16).from_buffer_copy(uuid.UUID(identifier).bytes_le)
    value = C.c_void_p()
    status = shell32.SHGetKnownFolderPath(C.byref(identifier), 0x4000, None, C.byref(value))
    assert status == 0 and value.value, "读取 Known Folder 失败"
    try:
        path = Path(C.wstring_at(value)).resolve()
    finally:
        ole32.CoTaskMemFree(value)
    assert path.is_relative_to(output), "Known Folder 未进入本次独立目录，停止验证"
    return path


def create_shortcut(path, target, icon, output):
    path.parent.mkdir(parents=True, exist_ok=True)
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                     pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.SetPath(str(target))
    link.SetArguments('--load-dir-res --path=. --sample="保留 参数"')
    link.SetWorkingDirectory(str(output))
    link.SetDescription("快捷方式图标验证")
    link.SetHotkey(0x0241)
    link.SetShowCmd(7)
    link.SetIconLocation(*icon)
    store = link.QueryInterface(propsys.IID_IPropertyStore)
    values = {
        "appid": "dlcv.test.shortcut.icons",
        "relaunch_command": f'"{target}" --load-dir-res --path=.',
        "relaunch_icon": f"{target},0",
        "relaunch_name": "快捷方式图标验证",
    }
    for name, value in values.items():
        store.SetValue(PROPERTIES[name], propsys.PROPVARIANTType(value, pythoncom.VT_LPWSTR))
    store.Commit()
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(str(path), 1)


def shortcut_snapshot(path):
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                     pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.QueryInterface(pythoncom.IID_IPersistFile).Load(str(path), 0)
    store = link.QueryInterface(propsys.IID_IPropertyStore)
    fields = {
        "target": link.GetPath(4)[0], "arguments": link.GetArguments(),
        "directory": link.GetWorkingDirectory(), "description": link.GetDescription(),
        "hotkey": link.GetHotkey(), "show": link.GetShowCmd(),
        **{name: store.GetValue(key).GetValue() for name, key in PROPERTIES.items()},
    }
    return {"fields": fields, "icon": list(link.GetIconLocation()),
            "bytes": path.read_bytes(), "mtime_ns": path.stat().st_mtime_ns}


def start_from_link(capture, runtime, link, output, environment, desktop, job):
    startup = capture.STARTUPINFO()
    startup.cb = C.sizeof(startup)
    startup.lpDesktop = "WinSta0\\" + desktop
    startup.dwFlags = 0x800  # STARTF_TITLEISLINKNAME
    startup.lpTitle = str(link)
    process = capture.PROCESS_INFORMATION()
    command = C.create_unicode_buffer(subprocess.list2cmdline([str(runtime), "--load-dir-res", "--path=."]))
    block = C.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in
                                   sorted(environment.items(), key=lambda item: item[0].upper())) + "\0\0")
    created = capture.KERNEL32.CreateProcessW(str(runtime), command, None, None, False,
        capture.CREATE_SUSPENDED | capture.CREATE_UNICODE_ENVIRONMENT | capture.CREATE_NO_WINDOW,
        block, str(output), C.byref(startup), C.byref(process))
    if not created:
        raise C.WinError(C.get_last_error())
    resumed = False
    try:
        if not capture.KERNEL32.AssignProcessToJobObject(job, process.hProcess):
            raise C.WinError(C.get_last_error())
        if capture.KERNEL32.ResumeThread(process.hThread) == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        resumed = True
        return process.hProcess, process.dwProcessId
    finally:
        capture.KERNEL32.CloseHandle(process.hThread)
        if not resumed:
            capture.KERNEL32.TerminateProcess(process.hProcess, 1)
            capture.KERNEL32.CloseHandle(process.hProcess)


def wait_window(capture, desktop, job, process, pid, title, deadline):
    found = []
    callback_type = C.WINFUNCTYPE(capture.BOOL, capture.PTR, C.c_ssize_t)

    def collect(hwnd, unused):
        owner = capture.DWORD()
        capture.USER32.GetWindowThreadProcessId(hwnd, C.byref(owner))
        if (owner.value == pid and win32gui.GetClassName(hwnd) == "Neutralinojs_webview"
                and win32gui.GetWindowText(hwnd) == title):
            found.append(hwnd)
            return False
        return True

    callback = callback_type(collect)
    while not found and time.monotonic() < deadline:
        if capture.KERNEL32.WaitForSingleObject(process, 0) == capture.WAIT_OBJECT_0:
            raise RuntimeError("运行时在窗口初始化完成前退出")
        capture.USER32.EnumDesktopWindows(desktop, callback, 0)
        time.sleep(0.05)
    assert found and capture.in_job(pid, job), "未发现本次 Job 中初始化完成的窗口"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "capture-module", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    home = output / "home"
    home.mkdir()
    environment = os.environ.copy()
    for key in ("USERPROFILE", "HOME"):
        environment[key] = str(home)
    for key in ("APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "TMPDIR"):
        environment[key] = str(output)
    original_environment = os.environ.copy()
    os.environ.update(environment)
    result = {"passed": False, "cases": []}
    desktop = job = capture = None
    handles = []
    pythoncom.CoInitialize()
    try:
        pinned = known_folder("9e3995ab-1f9c-4f13-b827-48b24b6c7174", output)
        implicit = known_folder("bcb5256f-79f6-4cee-b725-dc34e402fd46", output)
        custom = home / "custom.ico"
        Image.new("RGBA", (32, 32), (31, 133, 201, 255)).save(custom, sizes=[(32, 32)])
        missing = str(output / "deleted.ico")
        startup_link = output / "startup.lnk"
        cases = (
            ("固定副本失效文件", pinned / "TaskBar" / "missing.lnk", runtime, (missing, 0), True),
            ("自动分组失效资源", implicit / "test-group" / "resource.lnk", runtime, (str(runtime), 2147483647), True),
            ("有效自定义图标", pinned / "TaskBar" / "custom.lnk", runtime, (str(custom), 0), False),
            ("远程图标保留", implicit / "remote-group" / "remote.lnk", runtime,
             (r"\\127.0.0.1\dlcv-icon-regression\missing.ico", 0), False),
            ("空图标位置", pinned / "TaskBar" / "default.lnk", runtime, ("", 0), False),
            ("其他完整目标", pinned / "TaskBar" / "other.lnk", output / "other" / runtime.name, (missing, 0), False),
            ("实际启动链接", startup_link, runtime, (missing, 0), True),
            ("指定目录外链接", pinned / "StartMenu" / "ignored.lnk", runtime, (missing, 0), False),
        )
        before = {}
        for label, path, target, icon, repair in cases:
            create_shortcut(path, target, icon, output)
            before[label] = shortcut_snapshot(path)
        title = "任务栏快捷方式图标验证"
        config = {
            "applicationId": "dlcv.shortcut.check", "defaultMode": "window", "port": 0,
            "url": "/index.html", "documentRoot": "/", "enableServer": True,
            "logging": {"enabled": True, "writeToLogFile": True},
            "modes": {"window": {"title": title, "width": 640, "height": 480, "useSavedState": False}},
        }
        (output / "neutralino.config.json").write_text(json.dumps(config), encoding="utf-8")
        (output / "index.html").write_text("<!doctype html><html><body></body></html>", encoding="utf-8")
        spec = importlib.util.spec_from_file_location("capture", args.capture_module.resolve(strict=True))
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        name = "DLCV_shortcut_" + secrets.token_hex(8)
        desktop = capture.USER32.CreateDesktopW(name, None, None, 0, capture.DESKTOP_ACCESS, None)
        assert desktop, "创建独立桌面失败"
        input_name = capture.ensure_desktop(desktop, name)
        job = capture.create_job("Local\\" + name)
        explorer, _ = capture.start_in_job(Path(os.environ["SystemRoot"]) / "explorer.exe",
            [], output, environment, name, job)
        handles.append(explorer)
        deadline = time.monotonic() + 40
        after = {}
        for iteration in range(2):
            process, pid = start_from_link(capture, runtime, startup_link, output, environment, name, job)
            handles.append(process)
            wait_window(capture, desktop, job, process, pid, title, deadline)
            assert capture.ensure_desktop(desktop, name) == input_name, "输入桌面发生变化"
            for label, path, target, icon, repair in cases:
                current = shortcut_snapshot(path)
                if iteration == 0:
                    properties_preserved = current["fields"] == before[label]["fields"]
                    expected_icon = [str(runtime), 0] if repair else before[label]["icon"]
                    untouched = current["bytes"] == before[label]["bytes"] and current["mtime_ns"] == before[label]["mtime_ns"]
                    passed = properties_preserved and current["icon"] == expected_icon and (repair or untouched)
                    result["cases"].append({"name": label, "passed": passed,
                        "properties_preserved": properties_preserved, "icon": current["icon"],
                        "expected_icon": expected_icon, "unchanged": untouched,
                        "before_properties": before[label]["fields"], "after_properties": current["fields"]})
                    after[label] = current
                else:
                    record = next(item for item in result["cases"] if item["name"] == label)
                    record["second_run_icon"] = current["icon"]
                    record["second_run_properties"] = current["fields"]
                    record["first_run_mtime_ns"] = after[label]["mtime_ns"]
                    record["second_run_mtime_ns"] = current["mtime_ns"]
                    record["second_run_unchanged"] = (current == after[label])
                    record["passed"] = record["passed"] and record["second_run_unchanged"]
            capture.KERNEL32.TerminateProcess(process, 0)
            capture.KERNEL32.WaitForSingleObject(process, 1000)
        result["passed"] = all(case["passed"] for case in result["cases"])
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if job:
            capture.KERNEL32.TerminateJobObject(job, 0)
        for handle in handles:
            capture.KERNEL32.WaitForSingleObject(handle, 1000)
            capture.KERNEL32.CloseHandle(handle)
        if job:
            capture.KERNEL32.CloseHandle(job)
        if desktop:
            capture.USER32.CloseDesktop(desktop)
        pythoncom.CoUninitialize()
        os.environ.clear()
        os.environ.update(original_environment)
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
