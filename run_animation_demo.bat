@echo off
chcp 65001 >nul
echo ========================================
echo 动态画线跑马灯效果演示
echo ========================================
echo.
echo 正在启动演示程序...
echo.

cd /d "%~dp0"

REM 检查虚拟环境
if exist "venv-dev\Scripts\activate.bat" (
    echo 使用虚拟环境: venv-dev
    call venv-dev\Scripts\activate.bat
) else (
    echo 警告: 未找到虚拟环境 venv-dev
    echo 使用系统Python环境
)

REM 运行演示程序
python examples\drawing\demo_drawing_animation.py

if errorlevel 1 (
    echo.
    echo 错误: 程序运行失败
    pause
    exit /b 1
)

echo.
echo 演示程序已关闭
pause

