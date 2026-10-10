import ctypes
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import uuid


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
        self.assertLess(source.index("std::replace(winitial_dir.begin()"), source.index("return select_save_vista(winitial_dir,"))
        self.assertLess(save.index("ifd->SetFolder(folder)"), save.index("ifd->Show(GetForegroundWindow())"))
        self.assertNotIn("SetDefaultFolder", save)
        self.assertIn("ifd->SetFileName(filename.c_str())", save)
        self.assertIn("ifd->SetFileTypes((UINT)filter_specs.size(), filter_specs.data())", save)
        self.assertIn("if (!(options & opt::force_overwrite))", save)
        self.assertIn("dialog_options |= FOS_OVERWRITEPROMPT;", save)
        self.assertIn("if (FAILED(ifd->Show(GetForegroundWindow())))\n        return \"\";", save)
        self.assertIn("GetDisplayName(SIGDN_FILESYSPATH", save)
        self.assertIn("return select_save_vista(winitial_dir, m_wdefault_path.substr(separator + 1)", source)
        self.assertIn("std::replace(winitial_dir.begin(), winitial_dir.end(), L'/', L'\\\\');", source)

    def test_existing_directory_shell_parsing(self):
        ole32 = ctypes.WinDLL("ole32")
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        ole32.CoInitializeEx.restype = ctypes.c_long
        ole32.CoUninitialize.argtypes = []
        ole32.CoUninitialize.restype = None
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole32.CoTaskMemFree.restype = None
        shell32 = ctypes.WinDLL("shell32")
        shell32.SHCreateItemFromParsingName.argtypes = [
            ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
        ]
        shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
        iid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID("43826d1e-e718-42ee-bc55-a1e261c37bfe").bytes_le)
        self.assertIn(ole32.CoInitializeEx(None, 2), (0, 1))
        try:
            with tempfile.TemporaryDirectory(prefix="neutralino-save-shell-") as folder:
                existing = Path(folder) / "流程 解析"
                existing.mkdir()
                native = str(existing) + os.sep
                inputs = (native, native.replace(os.sep, "/"), native.replace(os.sep, "/", 2))
                for path in inputs:
                    with self.subTest(path=path):
                        normalized = path.replace("/", os.sep)
                        self.assertEqual(normalized, native)
                        item = ctypes.c_void_p()
                        self.assertEqual(shell32.SHCreateItemFromParsingName(normalized, None, iid, ctypes.byref(item)), 0)
                        self.assertTrue(item.value)
                        table = ctypes.cast(item, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])
                        get_name = ctypes.WINFUNCTYPE(
                            ctypes.c_long, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
                        )(table[5])
                        name = ctypes.c_void_p()
                        try:
                            self.assertEqual(get_name(item, 0x80058000, ctypes.byref(name)), 0)
                            self.assertTrue(name.value)
                            self.assertTrue(Path(ctypes.wstring_at(name.value)).samefile(existing))
                        finally:
                            if name.value:
                                ole32.CoTaskMemFree(name)
                            release(item)
        finally:
            ole32.CoUninitialize()

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
