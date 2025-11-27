@echo off
cd /d d:\Dev\vnpy
"D:\Program Files\Java\jdk-25\bin\java.exe" -jar d:\Dev\vnpy\jars\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor mflang\grammar\MFLang.g4
echo ANTLR completed with exit code %ERRORLEVEL%
pause

