@echo off
chcp 65001 >nul
echo ========================================
echo VNPy Development Environment
echo ========================================

echo.
echo [1/8] Installing local modules in editable mode...
cd /d "D:\Dev\vnpy\vnpy_futu"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy\vnpy_datamanager"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy\vnpy_datarecorder"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy\vnpy_ctastrategy"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy\vnpy_ctabacktester"
pip install -e . --no-deps
if errorlevel 1 goto error

cd /d "D:\Dev\vnpy"
pip install -e . --no-deps
if errorlevel 1 goto error

echo.
echo [2/8] Installing mflang module...
cd /d "D:\Dev\vnpy\mflang"
pip install -e .
if errorlevel 1 goto error

echo.
echo [3/8] Installing indicators module...
cd /d "D:\Dev\vnpy\indicators"
pip install -e .
if errorlevel 1 goto error

echo.
echo [4/8] Verifying environment...
python -c "import vnpy_futu; print('vnpy_futu path:', vnpy_futu.__file__)"
python -c "import vnpy_datamanager; print('vnpy_datamanager path:', vnpy_datamanager.__file__)"
python -c "import vnpy_datarecorder; print('vnpy_datarecorder path:', vnpy_datarecorder.__file__)"
python -c "import vnpy_ctastrategy; print('vnpy_ctastrategy path:', vnpy_ctastrategy.__file__)"
python -c "import vnpy_ctabacktester; print('vnpy_ctabacktester path:', vnpy_ctabacktester.__file__)"
python -c "import vnpy; print('vnpy path:', vnpy.__file__)"

echo.
echo [5/8] Testing data connection...
python -c "from vnpy_datamanager import ManagerEngine; print('DataManager engine available')"
python -c "from vnpy_datarecorder import DataRecorderApp; print('DataRecorder app available')"

echo.
echo [6/8] Verifying CTA modules...
python -c "from vnpy_ctastrategy import CtaTemplate; print('CTA Strategy module available')"
python -c "from vnpy_ctabacktester import CtaBacktesterApp; print('CTA Backtester module available')"
python -c "from mflang import REF, BARSLAST; print('mflang module available')"
python -c "from indicators import IndicatorManager; print('indicators module available')"

echo.
echo [7/8] Verifying DataRecorder module...
python -c "from vnpy_datarecorder import DataRecorderApp, RecorderEngine; print('DataRecorder module available')"

echo.
echo [8/8] Starting VNPy Trader...
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
