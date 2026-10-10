@echo off
setlocal
if "%~1"=="" goto :all_apps
if /i not "%~1"=="--dlcv-test" goto :usage
if "%~2"=="" goto :usage
if not "%~3"=="" goto :usage
chcp 65001 >nul

set "resource_hacker=C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe"
set "runtime=%~dp0bin\neutralino-win_x64.exe"
set "icon=%~dp0dist\test.ico"
set "version=%~dp0dist\test.rc"
set "version_resource=%~dp0dist\test.res"
set "output=%~dp0dist\DLCV Test-win_x64.exe"
set "target=%~f2"

for %%P in ("%target%") do (
    if /i not "%%~nxP"=="neutralino-win_x64.exe" (
        echo 目标文件名必须为 neutralino-win_x64.exe
        exit /b 2
    )
    if not exist "%%~dpP." (
        echo 目标目录不存在："%%~dpP"
        exit /b 1
    )
)
for %%P in ("%version_resource%" "%output%" "%target%") do (
    if exist "%%~fP\" (
        echo 文件路径指向目录："%%~fP"
        exit /b 1
    )
)
for %%P in ("%resource_hacker%" "%runtime%" "%icon%" "%version%") do (
    if not exist "%%~fP" (
        echo 找不到文件："%%~fP"
        exit /b 1
    )
    if exist "%%~fP\" (
        echo 文件路径指向目录："%%~fP"
        exit /b 1
    )
)

"%resource_hacker%" -open "%runtime%" -save "%output%" -action addoverwrite -res "%icon%" -mask ICONGROUP,MAINICON,0 -log console
if errorlevel 1 exit /b %errorlevel%
if not exist "%output%" exit /b 1
"%resource_hacker%" -open "%version%" -save "%version_resource%" -action compile -log console
if errorlevel 1 exit /b %errorlevel%
if not exist "%version_resource%" exit /b 1
"%resource_hacker%" -open "%output%" -save "%output%" -action addoverwrite -res "%version_resource%" -mask VERSIONINFO -log console
if errorlevel 1 exit /b %errorlevel%
copy /y "%output%" "%target%" >nul
if errorlevel 1 exit /b %errorlevel%
if not exist "%target%" exit /b 1
echo 已复制 DLCV Test 运行时到 "%target%"
exit /b 0

:usage
chcp 65001 >nul
echo 用法："%~nx0" --dlcv-test "目标目录\neutralino-win_x64.exe"
exit /b 2

:all_apps
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/studio.rc -save dist/studio.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Studio-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "dist/studio.res" -mask VERSIONINFO

cp "dist/DLCV AI Platform-win_x64.exe" "..\dlcv_ai_platform\neutralinojs\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Studio-win_x64.exe" "..\ai_studio\neu\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Training Platform-win_x64.exe" "..\dlcv_train\frontend\bin\neutralino-win_x64.exe"
cp "dist/DLCV Test-win_x64.exe" "..\dlcv_test\neu\bin\neutralino-win_x64.exe"

pause