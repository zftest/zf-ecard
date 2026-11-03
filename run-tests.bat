@echo off
REM Run the full test suite from the project root.
REM Works from any working directory (or by double-click) because it cd's
REM to this script's own folder first.
REM
REM Why this file exists:
REM   pytest only honors `testpaths` from pytest.ini when it is invoked FROM
REM   the rootdir. If you run it inside .venv\Scripts, pytest still finds
REM   rootdir and configfile, but ignores testpaths and collects the current
REM   directory instead -> "no tests ran" with exit code 5.
REM   Exit code 5 means "no tests collected", NOT success.

setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [FAIL] virtualenv python not found: %PY%
    exit /b 1
)

"%PY%" -m pytest %*
set "RC=%ERRORLEVEL%"

if "%RC%"=="5" (
    echo.
    echo [FAIL] No tests were collected ^(exit code 5^).
    echo        Make sure pytest.ini exists and the tests\ folder is present.
    exit /b 1
)

exit /b %RC%
