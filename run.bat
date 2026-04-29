@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "INTERP="

where node >nul 2>nul
if errorlevel 1 (
    echo Node.js is required for the Electron desktop. Install from https://nodejs.org/
    echo Legacy Tk GUI: run_legacy.bat ^(Python + SudachiPy still required^)
    pause
    exit /b 1
)

where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if "!INTERP!"=="" (
            "%%I" -c "import sudachipy,fastapi,uvicorn" >nul 2>nul
            if "!errorlevel!"=="0" (
                set "INTERP=%%I"
            )
        )
    )
)

if "%INTERP%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -c "import sudachipy,fastapi,uvicorn" >nul 2>nul
        if "!errorlevel!"=="0" (
            set "INTERP=py -3.12"
        )
    )
)

if "%INTERP%"=="" (
    echo Could not find a Python interpreter with required deps installed ^(SudachiPy/FastAPI/Uvicorn^).
    echo.
    echo Try one of these:
    echo   python -m pip install -r requirements.txt
    echo   py -m pip install -r requirements.txt
    echo Then re-run run.bat.
    pause
    exit /b 1
)

set "WMIX_PYTHON=%INTERP%"
set "WMIX_ELECTRON_MIRROR_FALLBACK=https://npmmirror.com/mirrors/electron/"

pushd desktop
if not exist node_modules (
    echo Installing desktop dependencies ^(first run^)...
    call :npm_install_with_retry
    if not "!NPM_INSTALL_OK!"=="1" (
        echo npm install failed.
        popd
        pause
        exit /b 1
    )
)

rem node_modules may exist but electron binary can still be broken (partial install/interrupted download).
node -e "require('electron')" >nul 2>nul
if errorlevel 1 (
    echo Electron runtime looks broken. Reinstalling desktop dependencies...
    if exist node_modules\electron rmdir /s /q node_modules\electron
    call :npm_install_with_retry
    if not "!NPM_INSTALL_OK!"=="1" (
        echo npm reinstall failed.
        echo.
        echo This is usually a network/download issue while fetching Electron.
        echo If it keeps failing, try:
        echo   set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
        echo   run.bat
        popd
        pause
        exit /b 1
    )
    node -e "require('electron')" >nul 2>nul
    if errorlevel 1 (
        echo Electron is still not usable after reinstall.
        echo Try deleting desktop\node_modules and run.bat again.
        popd
        pause
        exit /b 1
    )
)

echo Starting Bunseki ^(Electron + Vite + Python API^)...
call npm run dev
set "APP_EXIT=!errorlevel!"
popd

if not "!APP_EXIT!"=="0" (
    echo.
    echo Desktop exited with error code !APP_EXIT!.
    echo Ensure Python deps: pip install -r requirements.txt
    echo Optional: set WMIX_PYTHON=path\to\python.exe if the wrong interpreter is used.
    pause
)
exit /b !APP_EXIT!

:npm_install_with_retry
set "NPM_INSTALL_OK=0"
set /a NPM_TRY=0
set "WMIX_ORIG_ELECTRON_MIRROR=%ELECTRON_MIRROR%"
set "WMIX_MIRROR_SWITCHED=0"
:npm_install_retry_loop
set /a NPM_TRY+=1
echo npm install attempt !NPM_TRY!/3...
if !NPM_TRY! EQU 2 (
    if "%WMIX_ORIG_ELECTRON_MIRROR%"=="" (
        echo Switching Electron download mirror for retry...
        set "ELECTRON_MIRROR=%WMIX_ELECTRON_MIRROR_FALLBACK%"
        set "WMIX_MIRROR_SWITCHED=1"
    )
)
set "npm_config_fetch_retries=5"
set "npm_config_fetch_retry_factor=2"
set "npm_config_fetch_retry_mintimeout=20000"
set "npm_config_fetch_retry_maxtimeout=120000"
call npm install
if not errorlevel 1 (
    set "NPM_INSTALL_OK=1"
    if "!WMIX_MIRROR_SWITCHED!"=="1" (
        echo Electron mirror fallback worked: %ELECTRON_MIRROR%
    )
    goto :eof
)
if !NPM_TRY! lss 3 (
    echo npm install failed ^(attempt !NPM_TRY!^). Retrying...
    if exist node_modules\electron (
        rmdir /s /q node_modules\electron
    )
    ping 127.0.0.1 -n 4 >nul
    goto npm_install_retry_loop
)
if "!WMIX_MIRROR_SWITCHED!"=="1" (
    echo Tried mirror: %ELECTRON_MIRROR%
)
goto :eof
