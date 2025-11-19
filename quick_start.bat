@echo off
title VNPy 更新和启动 (本地开发版本)

echo 🔄 安装本地开发版 vnpy_futu (保留自定义功能)...
cd /d "d:\Dev\vnpy\vnpy_futu"
pip install -e .

echo 🔄 安装本地开发版 vnpy (保留自定义功能)...
cd /d "d:\Dev\vnpy"
pip install -e .

echo 🚀 启动 VNPy...
cd /d "d:\Dev\vnpy\examples\veighna_trader"
python run.py

pause