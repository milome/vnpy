@echo off
chcp 65001 > nul
echo ============================================
echo    VNPy 自动更新和启动脚本 (本地开发版本)
echo ============================================
echo.

echo [1/3] 正在安装本地开发版 vnpy_futu (保留自定义功能)...
cd /d "d:\Dev\vnpy\vnpy_futu"
if %ERRORLEVEL% neq 0 (
    echo ❌ 目录切换失败！请检查路径是否正确
    echo 当前目录: %CD%
    echo 目标目录: d:\Dev\vnpy\vnpy_futu
    pause
    exit /b 1
)

pip install -e .
if %ERRORLEVEL% neq 0 (
    echo ❌ vnpy_futu 本地安装失败！
    pause
    exit /b 1
)
echo ✅ vnpy_futu 本地版本安装完成 (包含智能追价功能)

echo.
echo [2/3] 正在安装本地开发版 vnpy (保留自定义功能)...
cd /d "d:\Dev\vnpy"
if %ERRORLEVEL% neq 0 (
    echo ❌ 目录切换失败！请检查路径是否正确
    echo 当前目录: %CD%
    echo 目标目录: d:\Dev\vnpy
    pause
    exit /b 1
)

pip install -e .
if %ERRORLEVEL% neq 0 (
    echo ❌ vnpy 本地安装失败！
    pause
    exit /b 1
)
echo ✅ vnpy 本地版本安装完成 (包含Market/OPPONENT/智能追价UI)

echo.
echo [3/3] 切换到运行目录...
cd /d "d:\Dev\vnpy\examples\veighna_trader"
if %ERRORLEVEL% neq 0 (
    echo ❌ 目录切换失败！请检查路径是否正确
    echo 当前目录: %CD%
    echo 目标目录: d:\Dev\vnpy\examples\veighna_trader
    pause
    exit /b 1
)
echo ✅ 已切换到: %CD%

echo.
echo 启动 VNPy Trader...
echo ============================================
echo 🚀 正在启动交易系统 (完整自定义版本)...
echo   ✓ Market Price 实时价格计算
echo   ✓ OPPONENT Price 激进对手价
echo   ✓ 智能追价系统 (Gateway + UI)
echo   ✓ 简洁UI界面
echo ============================================
python run.py

echo.
echo ============================================
echo 📊 VNPy Trader 已退出
echo ============================================
pause