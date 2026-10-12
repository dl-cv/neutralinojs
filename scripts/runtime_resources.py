"""生成各应用的正式图标、版本资源和运行时文件，不执行测试。"""

import argparse
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_HACKER = Path(r"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe")
APPS = {
    "platform": ("DLCV AI Platform-win_x64.exe", "ico.ico", "env", "dlcv_ai_platform/neutralinojs/bin"),
    "studio": ("DLCV AI Studio-win_x64.exe", "ico.ico", "studio", "ai_studio/neu/bin"),
    "train": ("DLCV AI Training Platform-win_x64.exe", "dist/train.ico", "train", "dlcv_train/frontend/bin"),
    "test": ("DLCV Test-win_x64.exe", "dist/test.ico", "test", "dlcv_test/neu/bin"),
}


def export_runtime(app, output):
    name, icon, version, _ = APPS[app]
    executable = ROOT / "dist" / name
    resource = ROOT / "dist" / (version + ".res")
    commands = (
        ["-open", str(ROOT / "bin/neutralino-win_x64.exe"), "-save", str(executable),
         "-action", "addoverwrite", "-res", str(ROOT / icon), "-mask", "ICONGROUP,MAINICON,0"],
        ["-open", str(ROOT / "dist" / (version + ".rc")), "-save", str(resource),
         "-action", "compile", "-log", "console"],
        ["-open", str(executable), "-save", str(executable),
         "-action", "addoverwrite", "-res", str(resource), "-mask", "VERSIONINFO"],
    )
    for command in commands:
        subprocess.run([str(RESOURCE_HACKER), *command], cwd=ROOT, check=True)
    shutil.copy2(executable, output / "neutralino-win_x64.exe")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", choices=APPS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output is not None and args.app is None:
        parser.error("指定输出目录时必须同时指定应用")
    applications = [args.app] if args.app else APPS
    outputs = []
    for app in applications:
        path = args.output if args.output is not None else ROOT.parent / APPS[app][3]
        try:
            path = path.resolve(strict=True)
        except OSError:
            parser.error("输出目录不存在：" + str(path))
        if not path.is_dir():
            parser.error("输出位置不是目录：" + str(path))
        outputs.append((app, path))
    for app, output in outputs:
        export_runtime(app, output)


if __name__ == "__main__":
    main()
