import os
from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "lib/webview/popup_window.h").read_text(encoding="utf-8")
BATCH = ROOT / "换图标、添加版本信息.bat"
SCRIPT = BATCH.read_text(encoding="utf-8")


class PopupHostStaticTests(unittest.TestCase):
    def test_independent_window_keeps_owner_icons(self):
        self.assertRegex(HEADER, r"CreateWindowExW\(WS_EX_APPWINDOW,[\s\S]*?WS_OVERLAPPEDWINDOW,[\s\S]*?nullptr, nullptr, GetModuleHandleW\(nullptr\), holder\)")
        self.assertIn("WS_OVERLAPPEDWINDOW, FALSE, WS_EX_APPWINDOW, dpi", HEADER)
        for size in ("ICON_SMALL", "ICON_BIG"):
            self.assertIn(f"SendMessageW(owner, WM_GETICON, {size}, 0)", HEADER)

    def test_minimizing_does_not_resize_webview(self):
        resize = HEADER.split("case WM_SIZE:", 1)[1].split("case WM_SETFOCUS:", 1)[0]
        self.assertRegex(resize, r"if \(wparam != SIZE_MINIMIZED && popup->controller_\) \{\s+RECT bounds;\s+GetClientRect\(window, &bounds\);\s+popup->controller_->put_Bounds\(bounds\);")

    def test_focus_message_is_exact_and_checks_window_before_restore(self):
        handler = HEADER.split("view_->add_WebMessageReceived(", 1)[1].split("view_->add_DocumentTitleChanged(", 1)[0]
        self.assertIn("SUCCEEDED(args->TryGetWebMessageAsString(&message))", handler)
        self.assertIn('received && message && std::wstring(message) == L"neutralino-popup:focus";', handler)
        expected = (
            "CoTaskMemFree(message);",
            "if (!focus) return S_OK;",
            "auto popup = weak.lock();",
            "if (!popup || !IsWindow(popup->window_)) return S_OK;",
            "if (IsIconic(popup->window_)) ShowWindow(popup->window_, SW_RESTORE);",
            "SetForegroundWindow(popup->window_);",
            "if (popup->controller_)",
            "popup->controller_->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);",
        )
        positions = [handler.index(step) for step in expected]
        self.assertEqual(positions, sorted(positions))

    def test_existing_webview_lifecycle_is_retained(self):
        for operation in (
            "request->put_NewWindow(view_.Get())",
            "view_->add_DocumentTitleChanged(",
            "SetWindowTextW(popup->window_, title)",
            "view_->add_WindowCloseRequested(",
            'popup->view_->ExecuteScript(L"window.close()", nullptr)',
            "popup->controller_->Close()",
        ):
            self.assertIn(operation, HEADER)

    def test_test_only_resource_route_preserves_original_commands(self):
        self.assertEqual(SCRIPT.count("ResourceHacker.exe"), 12)
        self.assertEqual(len(re.findall(r"^cp ", SCRIPT, re.MULTILINE)), 4)
        self.assertNotIn("call :buildTest", SCRIPT)
        self.assertTrue(SCRIPT.rstrip().endswith("pause"))
        icon = SCRIPT.split("\n:testIcon\n", 1)[1].split("\n:testVersion\n", 1)[0]
        version = SCRIPT.split("\n:testVersion\n", 1)[1]
        self.assertIn('goto testIcon', SCRIPT)
        self.assertIn('goto testVersion', icon)
        self.assertIn('if not exist "%~f2\\." exit /b 2', SCRIPT)
        self.assertIn('-res "dist/test.ico" -mask ICONGROUP,MAINICON,0', icon)
        self.assertIn('-open dist/test.rc -save dist/test.res -action compile', version)
        self.assertIn('-open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^', version)
        self.assertIn('-res "dist/test.res" -mask VERSIONINFO', version)
        self.assertIn('copy /y "dist\\DLCV Test-win_x64.exe" "%~f2\\neutralino-win_x64.exe" > nul || exit /b 1', version)
        self.assertLess(version.index('exit /b 0'), version.index('dist/studio.rc'))

    @unittest.skipUnless(os.name == "nt", "参数校验需要 Windows CMD")
    def test_invalid_arguments_exit_before_resource_generation(self):
        output = Path(os.environ["TEMP"]).resolve()
        missing = output / "neutralino-popup-missing-bin"
        self.assertFalse(missing.exists())
        cases = (
            ("--unknown",),
            ("--test-output",),
            ("--TEST-OUTPUT",),
            ("--test-output", str(missing)),
            ("--test-output", str(output), "extra"),
        )
        for args in cases:
            with self.subTest(args=args):
                command = f'call "{BATCH}" {subprocess.list2cmdline(args)} < nul'
                result = subprocess.run(
                    f'{subprocess.list2cmdline([os.environ["COMSPEC"]])} /d /c {command}',
                    cwd=output, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn(b"ResourceHacker.exe", result.stdout)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
