from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "lib/webview/popup_window.h").read_text(encoding="utf-8")


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



if __name__ == "__main__":
    unittest.main()
