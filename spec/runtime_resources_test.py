"""资源生成检查单独运行，不由编译或资源脚本调用。"""

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import runtime_resources as resources


ROOT = Path(__file__).resolve().parents[1]


class RuntimeResourcesTests(unittest.TestCase):
    def test_batch_only_runs_production_generator(self):
        lines = (ROOT / "换图标、添加版本信息.bat").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, ["@echo off", 'python "%~dp0scripts\\runtime_resources.py" %*', "exit /b %errorlevel%"])
        source = (ROOT / "scripts/runtime_resources.py").read_text(encoding="utf-8")
        for forbidden in ("unittest", "pytest", "spec/", "static_test", "--test-output"):
            self.assertNotIn(forbidden, source)

    def test_each_application_generates_its_resources_and_copies_requested_output(self):
        temporary_root = Path(os.environ["TEMP"]).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="runtime-resource-check-", dir=temporary_root) as name:
            folder = Path(name).resolve(strict=True)
            self.assertEqual(folder.parent, temporary_root)
            (folder / "dist").mkdir()
            output = folder / "output"
            output.mkdir()
            with patch.object(resources, "ROOT", folder), patch.object(resources.subprocess, "run") as run:
                for app, (executable, icon, version, _) in resources.APPS.items():
                    with self.subTest(app=app):
                        run.reset_mock()
                        (folder / "dist" / executable).write_bytes(b"runtime-fixture")
                        resources.main(["--app", app, "--output", str(output)])
                        self.assertEqual(run.call_count, 3)
                        commands = [call.args[0] for call in run.call_args_list]
                        self.assertIn(str(folder / icon), commands[0])
                        self.assertIn(str(folder / "dist" / (version + ".rc")), commands[1])
                        self.assertIn(str(folder / "dist" / (version + ".res")), commands[2])
                        self.assertEqual(commands[0][-2:], ["-mask", "ICONGROUP,MAINICON,0"])
                        self.assertEqual(commands[2][-2:], ["-mask", "VERSIONINFO"])
                        self.assertTrue(all(call.kwargs["check"] for call in run.call_args_list))
                        self.assertEqual((output / "neutralino-win_x64.exe").read_bytes(), b"runtime-fixture")

    def test_default_outputs_keep_the_existing_product_paths(self):
        with patch.object(resources.Path, "resolve", lambda path, strict=False: path), patch.object(resources.Path, "is_dir", return_value=True), patch.object(resources, "export_runtime") as export:
            resources.main([])
        self.assertEqual(export.call_count, 4)
        for call in export.call_args_list:
            app, output = call.args
            self.assertEqual(output, resources.ROOT.parent / resources.APPS[app][3])

    def test_invalid_arguments_do_not_generate_resources(self):
        cases = (["--unknown"], ["--app", "missing"], ["--output", os.environ["TEMP"]], ["--app", "test", "--output", str(Path(os.environ["TEMP"]) / "missing-runtime-bin")])
        for args in cases:
            with self.subTest(args=args), patch.object(resources, "export_runtime") as export, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    resources.main(args)
                self.assertEqual(error.exception.code, 2)
                export.assert_not_called()

    def test_resource_failure_stops_before_copy(self):
        with patch.object(resources.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "ResourceHacker")) as run, patch.object(resources.shutil, "copy2") as copy:
            with self.assertRaises(subprocess.CalledProcessError):
                resources.export_runtime("studio", Path(os.environ["TEMP"]))
            self.assertEqual(run.call_count, 1)
            copy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
