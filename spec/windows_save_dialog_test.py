import ctypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "换图标、添加版本信息.bat"


@unittest.skipUnless(os.name == "nt", "仅适用于 Windows")
class WindowsSaveDialogTests(unittest.TestCase):
    def run_script(self, *arguments):
        command = f'call "{SCRIPT}" ' + " ".join(f'"{value}"' for value in arguments) + " < nul"
        return subprocess.run(
            f"cmd.exe /d /c {command}", cwd=tempfile.gettempdir(),
            capture_output=True, encoding="utf-8", errors="replace", timeout=120,
        )

    def test_save_directory_scope_and_lifetime(self):
        source = (ROOT / "lib/filedialogs/portable-file-dialogs.h").read_text(encoding="utf-8")
        start = source.index("        if (in_type == type::save)")
        end = source.index("            if (get_save_file_name(&ofn) == 0)", start)
        save = source[start:end]
        self.assertIn('find_last_of(L"\\\\/")', save)
        self.assertIn("if (!ofn.lpstrInitialDir && separator != std::wstring::npos)", save)
        self.assertIn("m_wdefault_path.substr(0, separator + 1)", save)
        self.assertIn("GetFileAttributesW(winitial_dir.c_str())", save)
        self.assertIn("parent_attr != INVALID_FILE_ATTRIBUTES && (parent_attr & FILE_ATTRIBUTE_DIRECTORY)", save)
        self.assertTrue(save.startswith(
            "        if (in_type == type::save)\n        {\n            std::wstring winitial_dir;"
        ))
        self.assertIn("if (!(options & opt::force_overwrite))", save)
        self.assertIn("ofn.Flags |= OFN_OVERWRITEPROMPT;", save)
        self.assertEqual(source.count("ofn.lpstrInitialDir = winitial_dir.c_str();"), 1)

    def test_save_forces_folder_before_show(self):
        source = (ROOT / "lib/filedialogs/portable-file-dialogs.h").read_text(encoding="utf-8")
        start = source.index("inline std::string internal::file_dialog::select_save_vista(")
        end = source.index("inline std::string internal::file_dialog::select_folder_vista(", start)
        save = source[start:end]
        self.assertIn("CLSID_FileSaveDialog", save)
        self.assertLess(save.index("ifd->SetFolder(folder)"), save.index("ifd->Show(GetForegroundWindow())"))
        self.assertNotIn("SetDefaultFolder", save)
        self.assertIn("ifd->SetFileName(filename.c_str())", save)
        self.assertIn("ifd->SetFileTypes((UINT)filter_specs.size(), filter_specs.data())", save)
        self.assertIn("if (!(options & opt::force_overwrite))", save)
        self.assertIn("dialog_options |= FOS_OVERWRITEPROMPT;", save)
        self.assertIn("if (FAILED(ifd->Show(GetForegroundWindow())))\n        return \"\";", save)
        self.assertIn("GetDisplayName(SIGDN_FILESYSPATH", save)
        self.assertIn("return select_save_vista(winitial_dir, m_wdefault_path.substr(separator + 1)", source)

    def test_resource_arguments_and_target_validation(self):
        with tempfile.TemporaryDirectory(prefix="neutralino-save-") as folder:
            root = Path(folder)
            directory = root / "neutralino-win_x64.exe"
            directory.mkdir()
            cases = [
                (("--unknown",), 2),
                (("--dlcv-test",), 2),
                (("--dlcv-test", root / "neutralino-win_x64.exe", "extra"), 2),
                (("--dlcv-test", root / "wrong.exe"), 2),
                (("--dlcv-test", root / "missing" / "neutralino-win_x64.exe"), 1),
                (("--dlcv-test", directory), 1),
            ]
            for arguments, expected in cases:
                with self.subTest(arguments=arguments):
                    result = self.run_script(*arguments)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            self.assertEqual(list(root.iterdir()), [directory])

    def test_dlcv_test_resources_only(self):
        other_outputs = [ROOT / "dist" / f"{name}-win_x64.exe" for name in (
            "DLCV AI Platform", "DLCV AI Training Platform", "DLCV AI Studio",
        )]
        before = [path.stat().st_mtime_ns if path.exists() else None for path in other_outputs]
        with tempfile.TemporaryDirectory(prefix="neutralino-save-") as folder:
            target_dir = Path(folder) / "保存资源 测试"
            target_dir.mkdir()
            target = target_dir / "neutralino-win_x64.exe"
            result = self.run_script("--dlcv-test", target)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(target.is_file())
            version = ctypes.WinDLL("version", use_last_error=True)
            version.GetFileVersionInfoSizeW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p]
            version.GetFileVersionInfoW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
            version.VerQueryValueW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p]
            size = version.GetFileVersionInfoSizeW(str(target), None)
            self.assertGreater(size, 0)
            buffer = ctypes.create_string_buffer(size)
            self.assertTrue(version.GetFileVersionInfoW(str(target), 0, size, buffer))
            value = ctypes.c_void_p()
            length = ctypes.c_uint32()
            resource = (ROOT / "dist/test.rc").read_text(encoding="utf-8")
            expected_version = re.search(r'VALUE "ProductVersion", "([^"]+)"', resource).group(1)
            for name, expected in (("InternalName", "DLCV Test"), ("ProductVersion", expected_version)):
                self.assertTrue(version.VerQueryValueW(
                    buffer, f"\\StringFileInfo\\000004B0\\{name}", ctypes.byref(value), ctypes.byref(length),
                ))
                self.assertEqual(ctypes.wstring_at(value.value), expected)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
            kernel.LoadLibraryExW.restype = ctypes.c_void_p
            kernel.FindResourceW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p]
            kernel.FindResourceW.restype = ctypes.c_void_p
            kernel.FreeLibrary.argtypes = [ctypes.c_void_p]
            handle = kernel.LoadLibraryExW(str(target), None, 0x22)
            self.assertTrue(handle)
            try:
                self.assertTrue(kernel.FindResourceW(handle, "MAINICON", ctypes.c_void_p(14)))
            finally:
                kernel.FreeLibrary(handle)
        after = [path.stat().st_mtime_ns if path.exists() else None for path in other_outputs]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
