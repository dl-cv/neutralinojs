if /i "%~1"=="--platform-output" (
    if "%~2"=="" exit /b 2
    if not "%~3"=="" exit /b 2
    if not exist "%~f2\." exit /b 2
    goto platformIcon
)
if /i "%~1"=="--train-output" (
    if "%~2"=="" exit /b 2
    if not "%~3"=="" exit /b 2
    if not exist "%~f2\." exit /b 2
    goto trainIcon
)
if /i "%~1"=="--test-output" (
    if "%~2"=="" exit /b 2
    if not "%~3"=="" exit /b 2
    if not exist "%~f2\." exit /b 2
    goto testIcon
)
if not "%~1"=="" exit /b 2

:platformIcon
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0
if /i "%~1"=="--platform-output" if errorlevel 1 exit /b 1
if /i "%~1"=="--platform-output" goto platformVersion

:trainIcon
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0
if /i "%~1"=="--train-output" if errorlevel 1 exit /b 1
if /i "%~1"=="--train-output" goto trainVersion

:testIcon
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0
if /i "%~1"=="--test-output" if errorlevel 1 exit /b 1
if /i "%~1"=="--test-output" goto testVersion

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

:platformVersion
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console
if /i "%~1"=="--platform-output" if errorlevel 1 exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO
if /i "%~1"=="--platform-output" (
    if errorlevel 1 exit /b 1
    copy /y "dist\DLCV AI Platform-win_x64.exe" "%~f2\neutralino-win_x64.exe" > nul || exit /b 1
    exit /b 0
)

:trainVersion
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console
if /i "%~1"=="--train-output" if errorlevel 1 exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO
if /i "%~1"=="--train-output" (
    if errorlevel 1 exit /b 1
    copy /y "dist\DLCV AI Training Platform-win_x64.exe" "%~f2\neutralino-win_x64.exe" > nul || exit /b 1
    exit /b 0
)


:testVersion
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console
if /i "%~1"=="--test-output" if errorlevel 1 exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO
if /i "%~1"=="--test-output" (
    if errorlevel 1 exit /b 1
    copy /y "dist\DLCV Test-win_x64.exe" "%~f2\neutralino-win_x64.exe" > nul || exit /b 1
    exit /b 0
)

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/studio.rc -save dist/studio.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Studio-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "dist/studio.res" -mask VERSIONINFO

cp "dist/DLCV AI Platform-win_x64.exe" "..\dlcv_ai_platform\neutralinojs\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Studio-win_x64.exe" "..\ai_studio\neu\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Training Platform-win_x64.exe" "..\dlcv_train\frontend\bin\neutralino-win_x64.exe"
cp "dist/DLCV Test-win_x64.exe" "..\dlcv_test\neu\bin\neutralino-win_x64.exe"

pause