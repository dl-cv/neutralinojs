"""检查窗口线程的退出不会进入十秒等待；不代替实际任务栏操作验收。"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HEADER = (ROOT / "lib/webview/webview.h").read_text(encoding="utf-8")
WINDOW = (ROOT / "api/window/window.cpp").read_text(encoding="utf-8")
BATCH = (ROOT / "换图标、添加版本信息.bat").read_text(encoding="utf-8")


class WindowCloseStaticTests(unittest.TestCase):
    def test_ui_thread_destroys_window_before_dispatch_or_wait(self):
        body = HEADER.split("class win32_edge_engine", 1)[1].split("void terminate(int exitCode = 0)", 1)[1].split("void dispatch(", 1)[0]
        self.assertRegex(body, r"processExitCode = exitCode;[\s\S]*?if \(GetCurrentThreadId\(\) == m_main_thread\) \{\s*DestroyWindow\(m_window\);\s*return;\s*\}")
        ui = body.split("if (GetCurrentThreadId() == m_main_thread)", 1)[1].split("return;", 1)[0]
        self.assertNotIn("WaitForSingleObject", ui)
        self.assertNotIn("dispatch(", ui)
        self.assertLess(body.index("return;"), body.index("CreateEvent("))

    def test_other_threads_keep_dispatch_and_completion_wait(self):
        body = HEADER.split("class win32_edge_engine", 1)[1].split("void terminate(int exitCode = 0)", 1)[1].split("void dispatch(", 1)[0]
        self.assertRegex(body, r"dispatch\(\[=\]\(\) \{\s*DestroyWindow\(m_window\);\s*SetEvent\(evtWindowClosed\);")
        self.assertLess(body.index("dispatch("), body.index("WaitForSingleObject("))
        self.assertLess(body.index("WaitForSingleObject("), body.index("CloseHandle("))

    def test_system_close_still_uses_existing_exit_path(self):
        self.assertRegex(HEADER, r"case WM_CLOSE:\s*if \(windowStateChange\)\s*windowStateChange\(WEBVIEW_WINDOW_CLOSE\);")
        self.assertRegex(WINDOW, r"case WEBVIEW_WINDOW_CLOSE:[\s\S]*?app::exit\(\);")

    def test_train_output_only_targets_requested_worktree(self):
        self.assertIn('goto trainIcon', BATCH)
        self.assertIn('goto trainVersion', BATCH)
        self.assertIn('copy /y "dist\\DLCV AI Training Platform-win_x64.exe" "%~f2\\neutralino-win_x64.exe" > nul || exit /b 1', BATCH)
        block = BATCH.split(':trainVersion', 1)[1].split(':testVersion', 1)[0]
        self.assertIn('exit /b 0', block)
        self.assertNotIn('..\\dlcv_train', block)


if __name__ == "__main__":
    unittest.main()
