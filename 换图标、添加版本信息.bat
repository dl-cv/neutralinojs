if /i "%~1"=="--test-output" goto testOutput
if not "%~1"=="" exit /b 2

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0

call :buildTest
if errorlevel 1 exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/studio.rc -save dist/studio.res -action compile -log console
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Studio-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "dist/studio.res" -mask VERSIONINFO

cp "dist/DLCV AI Platform-win_x64.exe" "..\dlcv_ai_platform\neutralinojs\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Studio-win_x64.exe" "..\ai_studio\neu\bin\neutralino-win_x64.exe"
cp "dist/DLCV AI Training Platform-win_x64.exe" "..\dlcv_train\frontend\bin\neutralino-win_x64.exe"
cp "dist/DLCV Test-win_x64.exe" "..\dlcv_test\neu\bin\neutralino-win_x64.exe"

pause
exit /b

:testOutput
setlocal
if "%~2"=="" exit /b 2
if not "%~3"=="" exit /b 2
for %%I in ("%~2") do set "testOutput=%%~fI"
if not exist "%testOutput%\." exit /b 2
pushd "%~dp0" || exit /b 1
call :buildTest
if errorlevel 1 (
    popd
    exit /b 1
)
copy /y "dist\DLCV Test-win_x64.exe" "%testOutput%\neutralino-win_x64.exe" > nul
set "result=%errorlevel%"
popd
endlocal & exit /b %result%

:buildTest
if not exist "bin\neutralino-win_x64.exe" exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0
if errorlevel 1 exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console
if errorlevel 1 exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO
exit /b %errorlevel%
