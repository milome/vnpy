@echo off
chcp 65001 >nul
echo ========================================
echo VNPy Development Environment (Worktree)
echo ========================================

REM Disable proxy to avoid connection issues
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=*
set no_proxy=*

REM Optional: Use Chinese mirror source
REM set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
REM set PIP_EXTRA_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [0/9] Installing required build tools...
python -m pip install --upgrade pip wheel
python -m pip install "hatchling>=1.27.0" "build>=1.0.0" "editables>=0.3"
if errorlevel 1 goto error

echo.
echo [1/9] Installing local modules in editable mode...
echo NOTE: Installing from WORKTREE: D:\Dev\vnpy-007-multi-timeframe-integration
echo.

REM Install vnpy_futu from main repo (not modified in worktree)
cd /d "D:\Dev\vnpy\vnpy_futu"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

REM Install vnpy_datamanager from main repo
cd /d "D:\Dev\vnpy\vnpy_datamanager"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

REM Install vnpy_datarecorder from main repo
cd /d "D:\Dev\vnpy\vnpy_datarecorder"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

REM Install vnpy_ctastrategy from worktree
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration\vnpy_ctastrategy"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

REM Install vnpy_ctabacktester from worktree
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration\vnpy_ctabacktester"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

REM Install main vnpy from WORKTREE (contains multi-timeframe changes)
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration"
pip install -e . --no-deps --no-build-isolation
if errorlevel 1 goto error

echo.
echo [2/9] Installing mflang module from worktree...
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration\mflang"
pip install -e . --no-build-isolation
if errorlevel 1 goto error

echo.
echo [3/9] Installing indicators module from worktree...
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration\indicators"
pip install -e . --no-build-isolation
if errorlevel 1 goto error

echo.
echo [4/9] Verifying environment...
python -c "import vnpy_futu; print('vnpy_futu path:', vnpy_futu.__file__)"
python -c "import vnpy_datamanager; print('vnpy_datamanager path:', vnpy_datamanager.__file__)"
python -c "import vnpy_datarecorder; print('vnpy_datarecorder path:', vnpy_datarecorder.__file__)"
python -c "import vnpy_ctastrategy; print('vnpy_ctastrategy path:', vnpy_ctastrategy.__file__)"
python -c "import vnpy_ctabacktester; print('vnpy_ctabacktester path:', vnpy_ctabacktester.__file__)"
python -c "import vnpy; print('vnpy path:', vnpy.__file__)"
python -c "from vnpy.chart import ChartWidget; print('ChartWidget import: OK')"
python -c "from vnpy.chart import MultiTimeframeWidget; print('MultiTimeframeWidget import: OK - Multi-timeframe feature available!')"

echo.
echo [5/9] Testing data connection...
python -c "from vnpy_datamanager import ManagerEngine; print('DataManager engine available')"
python -c "from vnpy_datarecorder import DataRecorderApp; print('DataRecorder app available')"

echo.
echo [6/9] Verifying CTA modules...
python -c "from vnpy_ctastrategy import CtaTemplate; print('CTA Strategy module available')"
python -c "from vnpy_ctabacktester import CtaBacktesterApp; print('CTA Backtester module available')"
python -c "from mflang import REF, BARSLAST; print('mflang module available')"
python -c "from indicators import IndicatorManager; print('indicators module available')"

echo.
echo [7/9] Verifying DataRecorder module...
python -c "from vnpy_datarecorder import DataRecorderApp, RecorderEngine; print('DataRecorder module available')"

echo.
echo [8/9] Verifying Multi-Timeframe Feature...
python -c "from vnpy.trader.ui.widget import ChartWindow; print('ChartWindow with multi-timeframe support: OK')"
python -c "from vnpy.chart.multi_timeframe_widget import MultiTimeframeWidget; print('MultiTimeframeWidget: OK')"
python -c "from vnpy.chart.cross_index_candle_item import CrossIndexCandleItem; print('CrossIndexCandleItem: OK')"

echo.
echo [9/9] Starting VNPy Trader from worktree...
echo NOTE: Running with multi-timeframe integration enabled
cd /d "D:\Dev\vnpy-007-multi-timeframe-integration\examples\veighna_trader"
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

