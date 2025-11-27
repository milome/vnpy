#!/usr/bin/env python3
"""
依赖包自动安装脚本
解决多周期策略系统的环境配置问题
"""

import subprocess
import sys
import importlib
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ 警告: 建议使用Python 3.7或更高版本")
        return False
    else:
        print("✅ Python版本符合要求")
        return True

def install_package(package_name, pip_name=None):
    """安装单个包"""
    if pip_name is None:
        pip_name = package_name
    
    try:
        importlib.import_module(package_name)
        print(f"✅ {package_name} 已安装")
        return True
    except ImportError:
        print(f"📦 正在安装 {pip_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"✅ {pip_name} 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {pip_name} 安装失败: {e}")
            return False

def install_pyqt5():
    """专门处理PyQt5的安装"""
    print("\n🔧 安装PyQt5图形界面库...")
    
    # 尝试不同的PyQt5安装方法
    pyqt5_packages = [
        "PyQt5",
        "PyQt5==5.15.7",  # 稳定版本
        "PyQt5==5.15.4"   # 备选版本
    ]
    
    for package in pyqt5_packages:
        print(f"尝试安装: {package}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            
            # 验证安装
            import PyQt5.QtWidgets
            print(f"✅ {package} 安装并验证成功")
            return True
            
        except (subprocess.CalledProcessError, ImportError) as e:
            print(f"⚠️ {package} 安装失败，尝试下一个版本...")
            continue
    
    # 如果都失败了，尝试conda安装
    print("🔄 尝试使用conda安装PyQt5...")
    try:
        subprocess.check_call(["conda", "install", "-c", "conda-forge", "pyqt", "-y"])
        import PyQt5.QtWidgets
        print("✅ 通过conda安装PyQt5成功")
        return True
    except (subprocess.CalledProcessError, ImportError, FileNotFoundError):
        print("❌ conda安装也失败了")
    
    return False

def install_talib():
    """专门处理TA-Lib的安装"""
    print("\n📈 安装TA-Lib技术分析库...")
    
    try:
        import talib
        print("✅ TA-Lib 已安装")
        return True
    except ImportError:
        pass
    
    # 尝试不同的安装方法
    methods = [
        # 方法1: 直接pip安装
        lambda: subprocess.check_call([sys.executable, "-m", "pip", "install", "TA-Lib"]),
        
        # 方法2: 使用预编译包（Windows）
        lambda: subprocess.check_call([sys.executable, "-m", "pip", "install", "--find-links", "https://www.lfd.uci.edu/~gohlke/pythonlibs/", "TA-Lib"]),
        
        # 方法3: conda安装
        lambda: subprocess.check_call(["conda", "install", "-c", "conda-forge", "ta-lib", "-y"]),
    ]
    
    for i, method in enumerate(methods, 1):
        try:
            print(f"尝试方法 {i}...")
            method()
            
            # 验证安装
            import talib
            print("✅ TA-Lib 安装并验证成功")
            return True
            
        except (subprocess.CalledProcessError, ImportError, FileNotFoundError):
            print(f"⚠️ 方法 {i} 失败，尝试下一个...")
            continue
    
    print("❌ TA-Lib 安装失败")
    print("💡 手动安装建议:")
    print("   Windows: 下载预编译包 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib")
    print("   macOS: brew install ta-lib")
    print("   Linux: sudo apt-get install libta-lib-dev")
    
    return False

def create_requirements_txt():
    """创建requirements.txt文件"""
    requirements = [
        "PyQt5>=5.15.4",
        "pyqtgraph>=0.12.0", 
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "TA-Lib>=0.4.24",
        "scipy>=1.7.0",
        "matplotlib>=3.5.0"
    ]
    
    requirements_file = Path("requirements.txt")
    with open(requirements_file, "w", encoding="utf-8") as f:
        f.write("# 多周期策略系统依赖包\n")
        f.write("# 安装命令: pip install -r requirements.txt\n\n")
        for req in requirements:
            f.write(f"{req}\n")
    
    print(f"✅ 已创建 {requirements_file}")

def install_all_dependencies():
    """安装所有依赖包"""
    print("🚀 开始安装多周期策略系统依赖包...")
    print("=" * 60)
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    success_count = 0
    total_count = 0
    
    # 基础包列表
    basic_packages = [
        ("numpy", "numpy>=1.20.0"),
        ("pandas", "pandas>=1.3.0"), 
        ("scipy", "scipy>=1.7.0"),
        ("matplotlib", "matplotlib>=3.5.0")
    ]
    
    # 安装基础包
    print("\n📦 安装基础数据处理包...")
    for package_name, pip_name in basic_packages:
        total_count += 1
        if install_package(package_name, pip_name):
            success_count += 1
    
    # 安装PyQt5
    total_count += 1
    if install_pyqt5():
        success_count += 1
    
    # 安装pyqtgraph
    total_count += 1
    if install_package("pyqtgraph", "pyqtgraph>=0.12.0"):
        success_count += 1
    
    # 安装TA-Lib
    total_count += 1
    if install_talib():
        success_count += 1
    
    # 创建requirements.txt
    create_requirements_txt()
    
    # 总结
    print("\n" + "=" * 60)
    print(f"📊 安装完成统计: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 所有依赖包安装成功！")
        print("✅ 现在可以运行: python 完整集成示例.py")
        return True
    else:
        print("⚠️ 部分依赖包安装失败")
        print("💡 建议:")
        print("   1. 检查网络连接")
        print("   2. 更新pip: python -m pip install --upgrade pip")
        print("   3. 使用国内镜像: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/")
        return False

def test_imports():
    """测试所有包的导入"""
    print("\n🧪 测试包导入...")
    
    test_packages = [
        ("numpy", "import numpy as np"),
        ("pandas", "import pandas as pd"),
        ("PyQt5", "from PyQt5.QtWidgets import QApplication"),
        ("pyqtgraph", "import pyqtgraph as pg"),
        ("talib", "import talib"),
        ("scipy", "import scipy"),
        ("matplotlib", "import matplotlib.pyplot as plt")
    ]
    
    success_count = 0
    for name, import_code in test_packages:
        try:
            exec(import_code)
            print(f"✅ {name} 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name} 导入失败: {e}")
    
    print(f"\n📊 导入测试: {success_count}/{len(test_packages)} 成功")
    return success_count == len(test_packages)

def main():
    """主函数"""
    print("🔧 多周期策略系统 - 依赖包安装工具")
    print("=" * 60)
    
    try:
        # 安装依赖包
        if install_all_dependencies():
            # 测试导入
            if test_imports():
                print("\n🎉 环境配置完成！")
                print("🚀 运行命令: python 完整集成示例.py")
            else:
                print("\n⚠️ 部分包导入失败，请检查安装")
        else:
            print("\n❌ 依赖包安装未完全成功")
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断安装")
    except Exception as e:
        print(f"\n💥 安装过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

