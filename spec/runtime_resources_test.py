"""资源脚本完整性检查单独运行，不由编译或资源脚本调用。"""

from pathlib import Path
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
        commands = [line for line in COMMANDS if line.startswith((RESOURCE_HACKER, "cp "))]
        self.assertEqual(len(commands), 16)
        for command in commands:
            self.assertTrue(command.endswith("|| exit /b 1"))
        self.assertEqual(COMMANDS[-1], "exit /b 0")


if __name__ == "__main__":
    unittest.main()
