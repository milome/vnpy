@echo off
REM 手动生成ANTLR解析器的批处理脚本
REM 如果Java不在PATH中，请修改下面的JAVA_PATH变量

REM 设置Java路径（如果Java不在PATH中，取消注释并修改路径）
REM set JAVA_PATH=C:\Program Files\Java\jdk-11\bin\java.exe
REM set JAVA_PATH=C:\Program Files\Eclipse Adoptium\jdk-11.0.19.9-hotspot\bin\java.exe

REM 设置项目路径
set PROJECT_ROOT=%~dp0..\..
set GRAMMAR_DIR=%~dp0
set JAR_FILE=%PROJECT_ROOT%\jars\antlr-4.13.2-complete.jar

echo ============================================================
echo 麦语言 ANTLR 解析器生成工具 (手动模式)
echo ============================================================
echo.

REM 检查jar文件
if not exist "%JAR_FILE%" (
    echo [X] 找不到jar文件: %JAR_FILE%
    echo 请确认jar文件位置
    pause
    exit /b 1
)
echo [OK] 找到jar文件: %JAR_FILE%
echo.

REM 检查Java
if defined JAVA_PATH (
    echo 使用指定的Java路径: %JAVA_PATH%
    set JAVA_CMD=%JAVA_PATH%
) else (
    echo 检查Java是否在PATH中...
    java -version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Java在PATH中
        set JAVA_CMD=java
    ) else (
        echo [X] Java不在PATH中
        echo.
        echo 请选择以下方法之一:
        echo 1. 修改此脚本，设置JAVA_PATH变量（取消注释并修改路径）
        echo 2. 将Java添加到系统PATH环境变量
        echo 3. 重新打开命令行窗口（如果刚安装Java）
        echo.
        pause
        exit /b 1
    )
)
echo.

REM 生成解析器
echo 正在生成解析器...
echo 命令: %JAVA_CMD% -jar %JAR_FILE% -Dlanguage=Python3 -visitor MFLang.g4
echo.

cd /d "%GRAMMAR_DIR%"
%JAVA_CMD% -jar "%JAR_FILE%" -Dlanguage=Python3 -visitor MFLang.g4

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [OK] 解析器生成成功!
    echo ============================================================
    echo.
    echo 生成的文件:
    if exist MFLangLexer.py echo   - MFLangLexer.py
    if exist MFLangParser.py echo   - MFLangParser.py
    if exist MFLangListener.py echo   - MFLangListener.py
    if exist MFLangVisitor.py echo   - MFLangVisitor.py
    echo.
) else (
    echo.
    echo [X] 生成失败，请检查错误信息
    pause
    exit /b 1
)

pause

