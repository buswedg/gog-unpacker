@echo off
setlocal

set "VENV_DIR=env"
set "REQUIREMENTS_FILE=requirements.txt"

cd /d %~dp0

echo Starting build process

echo.
echo Checking Python exists...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo Error: Python not found in PATH.
    echo.
    goto :end
)

echo.
echo Creating/ activating virtual environment...

if exist "%VENV_DIR%" (
    echo Virtual environment "%VENV_DIR%" already exists. Skipping creation.
) else (
    echo Creating virtual environment in "%VENV_DIR%"...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo.
        echo Error: Failed to create the virtual environment.
        echo.
        goto :end
    )
)

call "%VENV_DIR%\Scripts\activate"

echo.
echo Installing dependencies via pip...

if exist "%REQUIREMENTS_FILE%" (
    echo Installing dependencies from "%REQUIREMENTS_FILE%"...
    pip install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo.
        echo Warning: Failed to install all dependencies.
        echo.
    )
    echo Dependencies installed successfully.
) else (
    echo "%REQUIREEMENTS_FILE%" not found. Skipping dependency installation.
)

:end
echo.
echo Build process finished

endlocal