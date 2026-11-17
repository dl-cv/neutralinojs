"""从微软 NuGet 包更新 Windows WebView2 SDK。"""

from pathlib import Path
import urllib.request
import zipfile


VERSION = "1.0.2420.47"
ROOT = Path(__file__).resolve().parents[1]


def main():
    cache = ROOT / "bin/.tmp"
    cache.mkdir(parents=True, exist_ok=True)
    package = cache / f"webview2-{VERSION}.nupkg"
    url = ("https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/"
           f"{VERSION}/microsoft.web.webview2.{VERSION}.nupkg")
    urllib.request.urlretrieve(url, package)
    with zipfile.ZipFile(package) as archive:
        for name in ("WebView2.h", "WebView2EnvironmentOptions.h"):
            (ROOT / "lib/webview/windows" / name).write_bytes(
                archive.read(f"build/native/include/{name}"))
        (ROOT / "lib/webview/windows/WebView2LoaderStatic.lib").write_bytes(
            archive.read("build/native/x64/WebView2LoaderStatic.lib"))


if __name__ == "__main__":
    main()
