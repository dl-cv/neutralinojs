@echo off
python "%~dp0scripts\runtime_resources.py" %*
exit /b %errorlevel%
