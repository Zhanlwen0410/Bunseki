@echo off
cd /d "%~dp0"
python -c "import sudachipy" 2>nul || (
    echo ERROR: SudachiPy is not installed. Please run: pip install -r requirements.txt
    pause
    exit /b 1
)
python "bunseki.py" %*