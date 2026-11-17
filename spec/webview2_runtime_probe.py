"""在独立 Desktop 中读取固定 WebView2 版本并创建环境，不创建窗口控制器。"""

import argparse
import ctypes as C
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import uuid
import zipfile


def probe(runtime, loader, profile):
    ole = C.OleDLL("ole32")
    ole.CoInitializeEx(None, 2)
    ole.CoTaskMemFree.argtypes = [C.c_void_p]
    api = C.WinDLL(str(loader))
    get_version = api.GetAvailableCoreWebView2BrowserVersionString
    get_version.argtypes = [W.LPCWSTR, C.POINTER(C.c_void_p)]
    get_version.restype = C.c_long
    text = C.c_void_p()
    hr = get_version(str(runtime), C.byref(text))
    result = {"runtime_folder": str(runtime), "loader_path": str(loader),
              "environment_options": None, "available_hresult": f"0x{hr & 0xffffffff:08X}"}
    if text:
        result["available_version"] = C.wstring_at(text)
        ole.CoTaskMemFree(text)

    query_type = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.c_void_p, C.POINTER(C.c_void_p))
    ref_type = C.WINFUNCTYPE(C.c_ulong, C.c_void_p)
    invoke_type = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.c_long, C.c_void_p)
    supported = {uuid.UUID(value).bytes_le for value in (
        "00000000-0000-0000-c000-000000000046", "4e8a3389-c9d8-4bd2-b6b5-124fee6cc14d")}
    refs = [1]

    @query_type
    def query(this, iid, output):
        if C.string_at(iid, 16) in supported:
            output[0] = this
            refs[0] += 1
            return 0
        output[0] = None
        return -2147467262

    @ref_type
    def add_ref(this):
        refs[0] += 1
        return refs[0]

    @ref_type
    def release(this):
        refs[0] -= 1
        return refs[0]

    @invoke_type
    def completed(this, error, environment):
        result["environment_hresult"] = f"0x{error & 0xffffffff:08X}"
        if error >= 0 and environment:
            # 官方 ICoreWebView2Environment：IUnknown 后为控制器、响应、版本三个方法。
            table = C.cast(environment, C.POINTER(C.POINTER(C.c_void_p))).contents
            read_version = C.WINFUNCTYPE(C.c_long, C.c_void_p, C.POINTER(C.c_void_p))(table[5])
            value = C.c_void_p()
            status = read_version(environment, C.byref(value))
            result["browser_version_hresult"] = f"0x{status & 0xffffffff:08X}"
            if value:
                result["browser_version"] = C.wstring_at(value)
                ole.CoTaskMemFree(value)
        return 0

    table = (C.c_void_p * 4)(*[C.cast(fn, C.c_void_p) for fn in (query, add_ref, release, completed)])
    callback = (C.c_void_p * 1)(C.cast(table, C.c_void_p))
    create = api.CreateCoreWebView2EnvironmentWithOptions
    create.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, C.c_void_p]
    create.restype = C.c_long
    hr = create(str(runtime), str(profile), None, C.byref(callback))
    result["create_call_hresult"] = f"0x{hr & 0xffffffff:08X}"
    user = C.WinDLL("user32")
    user.PeekMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT, W.UINT]
    user.TranslateMessage.argtypes = [C.POINTER(W.MSG)]
    user.DispatchMessageW.argtypes = [C.POINTER(W.MSG)]
    deadline = time.monotonic() + 25
    message = W.MSG()
    while hr >= 0 and "environment_hresult" not in result and time.monotonic() < deadline:
        while user.PeekMessageW(C.byref(message), None, 0, 0, 1):
            user.TranslateMessage(C.byref(message))
            user.DispatchMessageW(C.byref(message))
        time.sleep(0.01)
    result["pass"] = all(result.get(key) == "0x00000000" for key in (
        "available_hresult", "create_call_hresult", "environment_hresult", "browser_version_hresult")) and bool(
        result.get("browser_version")) and result["browser_version"] == result.get("available_version")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--capture-helper", type=Path)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--loader", type=Path)
    args = parser.parse_args()
    if args.worker:
        result = probe(args.runtime, args.loader, args.output.parent / "profile")
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if result["pass"] else 1
    if args.output.exists():
        parser.error("结果文件已存在，请指定新的输出文件")
    root = Path(__file__).resolve().parents[1]
    work = root / "bin/.tmp" / ("runtime-probe-" + uuid.uuid4().hex)
    work.mkdir(parents=True)
    loader = work / "WebView2Loader.dll"
    archive = root / "bin/.tmp/webview2-1.0.2420.47.nupkg"
    with zipfile.ZipFile(archive) as package:
        loader.write_bytes(package.read("build/native/x64/WebView2Loader.dll"))
    spec = importlib.util.spec_from_file_location("capture_helper", args.capture_helper)
    cap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cap)
    name = "DLCV_runtime_probe_" + uuid.uuid4().hex
    desktop = cap.USER32.CreateDesktopW(name, None, None, 0, cap.DESKTOP_ACCESS, None)
    if not desktop:
        raise C.WinError(C.get_last_error())
    job = cap.create_job("Local\\" + name)
    handle = None
    try:
        cap.ensure_desktop(desktop, name)
        env = os.environ.copy()
        for key in ("TEMP", "TMP", "TMPDIR"):
            env[key] = str(work)
        handle, pid = cap.start_in_job(Path(sys.executable), [str(Path(__file__).resolve()),
            "--worker", "--runtime", str(args.runtime.resolve()), "--output", str(args.output.resolve()),
            "--loader", str(loader)], work, env, name, job)
        cap.KERNEL32.WaitForSingleObject(handle, 35000)
    finally:
        cap.KERNEL32.TerminateJobObject(job, 0)
        if handle:
            cap.KERNEL32.WaitForSingleObject(handle, 5000)
            cap.KERNEL32.CloseHandle(handle)
        cap.KERNEL32.CloseHandle(job)
        cap.USER32.CloseDesktop(desktop)
    result = json.loads(args.output.read_text(encoding="utf-8"))
    result.update(desktop=name, worker_pid=pid, job_stopped=True,
                  loader_archive=str(archive), loader_package="Microsoft.Web.WebView2 1.0.2420.47",
                  loader_entry="build/native/x64/WebView2Loader.dll")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
