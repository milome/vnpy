#!/bin/bash

echo "========================================"
echo "动态画线跑马灯效果演示"
echo "========================================"
echo ""
echo "正在启动演示程序..."
echo ""

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ -f "venv-dev/bin/activate" ]; then
    echo "使用虚拟环境: venv-dev"
    source venv-dev/bin/activate
else
    echo "警告: 未找到虚拟环境 venv-dev"
    echo "使用系统Python环境"
fi

# 运行演示程序
python examples/drawing/demo_drawing_animation.py

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: 程序运行失败"
    exit 1
fi

echo ""
echo "演示程序已关闭"

