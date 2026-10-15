@echo off
if /i "%~1"=="test" goto test_icon

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

:test_icon
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1
if /i "%~1"=="test" goto test_version

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO || exit /b 1

:test_version
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO || exit /b 1
if /i "%~1"=="test" goto test_copy

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/studio.rc -save dist/studio.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Studio-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "dist/studio.res" -mask VERSIONINFO || exit /b 1

cp "dist/DLCV AI Platform-win_x64.exe" "..\dlcv_ai_platform\neutralinojs\bin\neutralino-win_x64.exe" || exit /b 1
cp "dist/DLCV AI Studio-win_x64.exe" "..\ai_studio\neu\bin\neutralino-win_x64.exe" || exit /b 1
cp "dist/DLCV AI Training Platform-win_x64.exe" "..\dlcv_train\frontend\bin\neutralino-win_x64.exe" || exit /b 1
:test_copy
if not "%~2"=="" (
    cp "dist/DLCV Test-win_x64.exe" "%~2" || exit /b 1
    exit /b 0
)
cp "dist/DLCV Test-win_x64.exe" "..\dlcv_test\neu\bin\neutralino-win_x64.exe" || exit /b 1

exit /b 0
