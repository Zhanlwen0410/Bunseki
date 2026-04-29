@echo off
setlocal EnableDelayedExpansion
set "INTERP="

where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if "!INTERP!"=="" (
            "%%I" -c "import sudachipy" >nul 2>nul
            if "!errorlevel!"=="0" (
                set "INTERP=%%I"
            )
        )
    )
)

if "%INTERP%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -c "import sudachipy" >nul 2>nul
        if "!errorlevel!"=="0" (
            set "INTERP=py -3.12"
        )
    )
)

if "%INTERP%"=="" (
    echo Could not find a Python interpreter with SudachiPy installed.
    pause
    exit /b 1
)

cd /d "%~dp0"
%INTERP% main.py --gui --gui-mode tk
exit /b %errorlevel%
