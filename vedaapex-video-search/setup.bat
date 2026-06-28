@echo off
REM VedaApex Video Search Backend - Setup Script (Windows)
REM This script sets up the development environment

echo.
echo ======================================
echo VedaApex Video Search Backend - Setup
echo ======================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)
echo [OK] Python found

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    exit /b 1
)
echo [OK] Virtual environment created

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    exit /b 1
)
echo [OK] Dependencies installed

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo.
    echo [WARNING] Please edit .env and add your Pexels API key
    echo Edit .env in your text editor
) else (
    echo [OK] .env file already exists
)

REM Create logs directory
echo Creating logs directory...
if not exist logs mkdir logs
echo [OK] Logs directory created

REM Verify installation
echo Verifying installation...
python -c "import fastapi; import pydantic; print('[OK] All dependencies installed successfully')" 
if errorlevel 1 (
    echo Error: Dependency verification failed
    exit /b 1
)

echo.
echo ======================================
echo [SUCCESS] Setup Complete!
echo ======================================
echo.
echo Next steps:
echo 1. Edit .env and add your Pexels API key
echo 2. Run the server: python app.py
echo 3. Visit API docs: http://localhost:8000/docs
echo.
pause
