@echo off
REM VedaApex Media - Setup Script (Windows PowerShell)

echo.
echo 🚀 VedaApex Media - Setup Script
echo ==================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do (
    echo ✅ %%i
)

REM Create virtual environment
echo.
echo 📦 Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Create .env
if not exist .env (
    echo 📝 Creating .env from .env.example...
    copy .env.example .env
)

REM Create logs directory
if not exist logs mkdir logs

echo.
echo ✅ Setup completed!
echo.
echo 📖 Next steps:
echo    1. Update .env with your configuration
echo    2. Run: python app.py
echo    3. Visit: http://localhost:8000/api/v1/docs
echo.
pause
