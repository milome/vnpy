@echo off
chcp 65001 >nul
echo ========================================
echo VNPy Development Environment
echo ========================================

echo.
echo [1/4] Installing local modules in editable mode...
cd /d "D:\Dev\vnpy\vnpy_futu"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy\vnpy_datamanager"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy"
pip install -e . --no-deps
if errorlevel 1 goto error

echo.
echo [2/4] Verifying environment...
python -c "import vnpy_futu; print('vnpy_futu path:', vnpy_futu.__file__)"
python -c "import vnpy_datamanager; print('vnpy_datamanager path:', vnpy_datamanager.__file__)"
python -c "import vnpy; print('vnpy path:', vnpy.__file__)"

echo.
echo [3/4] Testing data connection...
python -c "from vnpy_datamanager import ManagerEngine; print('DataManager engine available')"

echo.
echo [4/4] Starting VNPy Trader...
cd /d "D:\Dev\vnpy\examples\veighna_trader"
python run.py

goto end

:error
echo.
echo ========================================
echo ERROR: Installation failed
echo ========================================
pause
exit /b 1

:end
