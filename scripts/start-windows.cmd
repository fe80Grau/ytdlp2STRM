@echo off
setlocal DisableDelayedExpansion
rem Always use the checkout containing this script, not the caller's directory.
pushd "%~dp0.." || exit /b 2
if "%~1"=="" (
    echo Usage: start-windows.cmd "C:\absolute\path\to\python.exe" 1>&2
    popd
    exit /b 2
)
rem Append so a subsequent start does not erase the previous failure.
echo [%date% %time%] Starting ytdlp2STRM with "%~1" >> log.txt
"%~1" -u main.py >> log.txt 2>&1
set "exitCode=%errorlevel%"
echo [%date% %time%] Python exited with code %exitCode% >> log.txt
popd
exit /b %exitCode%
