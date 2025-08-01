@echo off
echo Installing Histology Slide Renaming Tool Dependencies
echo ===================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

echo Installing Python packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Error installing Python packages
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Python packages installed successfully!
echo.
echo IMPORTANT: You still need to install OpenSlide:
echo   Windows: Download from https://openslide.org/download/
echo   macOS: brew install openslide
echo   Linux: sudo apt-get install openslide-tools
echo.
echo After installing OpenSlide, run:
echo   python main.py
echo to start the application.
echo ===============================================
pause