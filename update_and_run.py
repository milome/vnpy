#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VNPy 自动更新和启动脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_header(title):
    """打印格式化标题"""
    print("=" * 60)
    print(f"   {title}")
    print("=" * 60)

def print_step(step, total, message):
    """打印步骤信息"""
    print(f"\n[{step}/{total}] {message}")

def run_command(command, description):
    """执行命令并处理结果"""
    print(f"执行: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True,
                              capture_output=True, text=True, encoding='utf-8')
        print(f"✅ {description}成功")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败!")
        print(f"错误: {e}")
        if e.stderr:
            print(f"错误详情: {e.stderr}")
        return False

def main():
    """主函数"""
    print_header("VNPy 自动更新和启动脚本")

    # 步骤1: 更新vnpy
    print_step(1, 4, "正在更新 vnpy...")
    if not run_command("pip install --upgrade vnpy", "vnpy更新"):
        input("按任意键退出...")
        return

    # 步骤2: 更新vnpy_futu
    print_step(2, 4, "正在更新 vnpy_futu...")
    if not run_command("pip install --upgrade vnpy_futu", "vnpy_futu更新"):
        input("按任意键退出...")
        return

    # 步骤3: 切换目录
    print_step(3, 4, "切换到运行目录...")
    target_dir = Path("d:/Dev/vnpy/examples/veighna_trader")

    if not target_dir.exists():
        print(f"❌ 目录不存在: {target_dir}")
        print(f"当前目录: {os.getcwd()}")
        input("按任意键退出...")
        return

    try:
        os.chdir(target_dir)
        print(f"✅ 已切换到: {os.getcwd()}")
    except Exception as e:
        print(f"❌ 目录切换失败: {e}")
        input("按任意键退出...")
        return

    # 检查run.py是否存在
    run_file = Path("run.py")
    if not run_file.exists():
        print(f"❌ 运行文件不存在: {run_file.absolute()}")
        input("按任意键退出...")
        return

    # 步骤4: 启动程序
    print_step(4, 4, "启动 VNPy Trader...")
    print_header("🚀 正在启动交易系统...")

    try:
        # 直接运行，不捕获输出，让用户看到实时输出
        result = subprocess.run([sys.executable, "run.py"], check=False)

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("📊 VNPy Trader 正常退出")
        else:
            print(f"⚠️ VNPy Trader 异常退出 (退出码: {result.returncode})")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")

    input("按任意键退出...")

if __name__ == "__main__":
    main()