"""资源脚本完整性检查单独运行，不由编译或资源脚本调用。"""

from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BATCH = (ROOT / "换图标、添加版本信息.bat").read_text(encoding="utf-8")
COMMANDS = BATCH.replace("^\n", "").splitlines()
RESOURCE_HACKER = r'"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe"'


class RuntimeResourcesTests(unittest.TestCase):
    def test_batch_keeps_all_resource_and_copy_steps(self):
        applications = (
            ("DLCV AI Platform", "ico.ico", "env", r"dlcv_ai_platform\neutralinojs\bin"),
            ("DLCV AI Training Platform", "dist/train.ico", "train", r"dlcv_train\frontend\bin"),
            ("DLCV Test", "dist/test.ico", "test", r"dlcv_test\neu\bin"),
            ("DLCV AI Studio", "ico.ico", "studio", r"ai_studio\neu\bin"),
        )
        for app, icon, version, output in applications:
            with self.subTest(app=app):
                executable = f"dist/{app}-win_x64.exe"
                steps = (
                    f'{RESOURCE_HACKER} -open "bin/neutralino-win_x64.exe" -save "{executable}" -action addoverwrite -res "{icon}" -mask ICONGROUP,MAINICON,0 || exit /b 1',
                    f"{RESOURCE_HACKER} -open dist/{version}.rc -save dist/{version}.res -action compile -log console || exit /b 1",
                    f'{RESOURCE_HACKER} -open "{executable}" -save "{executable}" -action addoverwrite -res "dist/{version}.res" -mask VERSIONINFO || exit /b 1',
                    f'cp "{executable}" "..\\{output}\\neutralino-win_x64.exe" || exit /b 1',
                )
                for command in steps:
                    self.assertEqual(COMMANDS.count(command), 1)
                positions = [COMMANDS.index(command) for command in steps]
                self.assertEqual(positions, sorted(positions))

    def test_production_scripts_do_not_run_tests(self):
        for name in ("编译.bat", "换图标、添加版本信息.bat"):
            source = (ROOT / name).read_text(encoding="utf-8").lower()
            for forbidden in ("unittest", "pytest", "spec/", "spec\\", "_test.py", "--test-output", "--platform-output", "runtime_resources.py"):
                with self.subTest(script=name, forbidden=forbidden):
                    self.assertNotIn(forbidden, source)
        self.assertNotIn("python", BATCH.lower())

    def test_failed_resource_or_copy_command_stops_batch(self):
        commands = [line.strip() for line in COMMANDS if line.strip().startswith((RESOURCE_HACKER, "cp "))]
        self.assertEqual(len(commands), 17)
        for command in commands:
            self.assertTrue(command.endswith("|| exit /b 1"))
        self.assertEqual(COMMANDS[-1], "exit /b 0")

    def run_test_batch(self, fail_resource=0, fail_copy=0):
        # 外部工具由小命令替换，只验证批处理分支、参数和退出码。
        with tempfile.TemporaryDirectory(prefix="runtime-resources-") as directory:
            root = Path(directory)
            (root / "dist").mkdir()
            (root / "dist" / "DLCV Test-win_x64.exe").write_bytes(b"test runtime")
            target = root / "target runtime.exe"
            log = root / "calls.txt"
            for kind in ("resource", "copy"):
                (root / f"{kind}.cmd").write_text(
                    f"@echo off\nset /a {kind}_calls+=1 >nul\n"
                    f'>>"%CALL_LOG%" echo {kind} %*\n'
                    f'if "%{kind}_calls%"=="%FAIL_{kind.upper()}%" exit /b 1\n'
                    + ('set "source=%~1"\ncopy /y "%source:/=\\%" "%~2" >nul\nexit /b %errorlevel%\n' if kind == "copy" else "exit /b 0\n"),
                    encoding="ascii",
                )
            source = BATCH.replace(RESOURCE_HACKER, "call resource.cmd")
            source = re.sub(r"(?m)^(\s*)cp ", r"\1call copy.cmd ", source)
            script = root / "resources.bat"
            script.write_text(source, encoding="utf-8")
            environment = os.environ.copy()
            environment.update(
                CALL_LOG=str(log), FAIL_RESOURCE=str(fail_resource), FAIL_COPY=str(fail_copy),
                resource_calls="0", copy_calls="0", TEMP=str(root), TMP=str(root), TMPDIR=str(root),
            )
            result = subprocess.run(
                'cmd.exe /d /c call resources.bat test "target runtime.exe" < nul',
                cwd=root, env=environment, capture_output=True, timeout=10,
            )
            self.assertTrue(log.exists(), result.stdout + result.stderr)
            return result, log.read_text().splitlines(), target.read_bytes() if target.exists() else None

    @unittest.skipUnless(os.name == "nt", "需要 Windows 批处理")
    def test_test_mode_only_processes_test_runtime_and_target(self):
        result, calls, copied = self.run_test_batch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(calls), 4)
        self.assertIn('-res "dist/test.ico"', calls[0])
        self.assertIn("-open dist/test.rc", calls[1])
        self.assertIn('-res "dist/test.res"', calls[2])
        self.assertTrue(calls[3].startswith('copy "dist/DLCV Test-win_x64.exe" '))
        self.assertTrue(calls[3].endswith('target runtime.exe"'))
        self.assertEqual(copied, b"test runtime")

    @unittest.skipUnless(os.name == "nt", "需要 Windows 批处理")
    def test_test_mode_stops_on_each_resource_or_copy_failure(self):
        for failure in range(1, 5):
            with self.subTest(step=failure):
                result, calls, copied = self.run_test_batch(
                    fail_resource=failure if failure < 4 else 0,
                    fail_copy=1 if failure == 4 else 0,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(calls), failure)
                self.assertIsNone(copied)


if __name__ == "__main__":
    unittest.main()
