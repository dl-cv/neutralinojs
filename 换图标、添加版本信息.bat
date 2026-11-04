@echo off
setlocal
if not defined DLCV_PLATFORM_WORKTREE set "DLCV_PLATFORM_WORKTREE=..\dlcv_ai_platform"
if not defined DLCV_STUDIO_WORKTREE set "DLCV_STUDIO_WORKTREE=..\ai_studio"
if not defined DLCV_TRAIN_WORKTREE set "DLCV_TRAIN_WORKTREE=..\dlcv_train"
if not defined DLCV_TEST_WORKTREE set "DLCV_TEST_WORKTREE=..\dlcv_test"
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "bin/neutralino-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "ico.ico" -mask ICONGROUP,MAINICON,0 || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/env.rc -save dist/env.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Platform-win_x64.exe" -save "dist/DLCV AI Platform-win_x64.exe" ^
-action addoverwrite -res "dist/env.res" -mask VERSIONINFO || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/train.rc -save dist/train.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Training Platform-win_x64.exe" -save "dist/DLCV AI Training Platform-win_x64.exe" ^
-action addoverwrite -res "dist/train.res" -mask VERSIONINFO || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/test.rc -save dist/test.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV Test-win_x64.exe" -save "dist/DLCV Test-win_x64.exe" ^
-action addoverwrite -res "dist/test.res" -mask VERSIONINFO || exit /b 1

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open dist/studio.rc -save dist/studio.res -action compile -log console || exit /b 1
"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open "dist/DLCV AI Studio-win_x64.exe" -save "dist/DLCV AI Studio-win_x64.exe" ^
-action addoverwrite -res "dist/studio.res" -mask VERSIONINFO || exit /b 1

cp "dist/DLCV AI Platform-win_x64.exe" "%DLCV_PLATFORM_WORKTREE%\neutralinojs\bin\neutralino-win_x64.exe" || exit /b 1
cp "dist/DLCV AI Studio-win_x64.exe" "%DLCV_STUDIO_WORKTREE%\neu\bin\neutralino-win_x64.exe" || exit /b 1
cp "dist/DLCV AI Training Platform-win_x64.exe" "%DLCV_TRAIN_WORKTREE%\frontend\bin\neutralino-win_x64.exe" || exit /b 1
cp "dist/DLCV Test-win_x64.exe" "%DLCV_TEST_WORKTREE%\neu\bin\neutralino-win_x64.exe" || exit /b 1

exit /b 0
