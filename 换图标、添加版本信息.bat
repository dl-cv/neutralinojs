@echo off
if /i "%~1"=="test" goto test_only
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO

cp "dist/DLCV AI Platform-win_x64.exe" "..\dlcv_env\neutralinojs\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Training Platform-win_x64.exe" "..\dlcv_train\frontend\bin\neutralino-win_x64.exe"
cp "dist/DLCV Test-win_x64.exe" "..\dlcv_test\neu\bin\neutralino-win_x64.exe"

pause
exit /b

:test_only
setlocal
if "%~2"=="" (
    echo Usage: "%~nx0" test "project\neu\bin\neutralino-win_x64.exe"
    exit /b 2
)
if not exist "%~dp2" exit /b 2
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "RESOURCE_HACKER=C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe"
if not exist "%RESOURCE_HACKER%" goto test_failed
if not exist "bin\neutralino-win_x64.exe" goto test_failed
"%RESOURCE_HACKER%" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" -action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0 -log console
if errorlevel 1 goto test_failed
"%RESOURCE_HACKER%" -open "dist/test.rc" -save "dist/test.res" -action compile -log console
if errorlevel 1 goto test_failed
"%RESOURCE_HACKER%" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" -action addoverwrite -res "dist/test.res" -mask VERSIONINFO -log console
if errorlevel 1 goto test_failed
copy /y "dist\DLCV Test-win_x64.exe" "%~f2" > nul
if errorlevel 1 goto test_failed
popd
exit /b 0

:test_failed
popd
exit /b 1
