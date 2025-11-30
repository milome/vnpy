@echo off
chcp 65001 >nul
echo ========================================
echo 修复 pip 代理问题
echo ========================================
echo.

echo [1] 检查当前代理设置...
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%
echo http_proxy=%http_proxy%
echo https_proxy=%https_proxy%
echo.

echo [2] 临时禁用代理（仅当前会话）...
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=*
set no_proxy=*
echo 代理已禁用
echo.

echo [3] 检查 pip 配置文件...
if exist "%APPDATA%\pip\pip.ini" (
    echo 找到配置文件: %APPDATA%\pip\pip.ini
    type "%APPDATA%\pip\pip.ini"
) else (
    echo 未找到用户配置文件
)

if exist "%LOCALAPPDATA%\pip\pip.ini" (
    echo 找到配置文件: %LOCALAPPDATA%\pip\pip.ini
    type "%LOCALAPPDATA%\pip\pip.ini"
) else (
    echo 未找到本地配置文件
)
echo.

echo [4] 测试 pip 连接...
python -m pip --version
echo.

echo [5] 尝试安装 setuptools（测试连接）...
python -m pip install --upgrade setuptools --no-proxy
if errorlevel 1 (
    echo.
    echo 如果仍然失败，请尝试：
    echo   1. 检查网络连接
    echo   2. 使用国内镜像源：pip install setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo   3. 检查防火墙设置
    pause
    exit /b 1
) else (
    echo setuptools 安装成功！
)
echo.

echo ========================================
echo 修复完成！现在可以运行 update_and_run.bat
echo ========================================
pause

