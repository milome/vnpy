"""
VeighNa数据录制快速启动脚本
一键启动数据录制功能
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖包...")
    
    required_packages = [
        'vnpy',
        'vnpy_datarecorder',
        'vnpy_futu',
        'vnpy_datamanager'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n需要安装以下包: {', '.join(missing_packages)}")
        install = input("是否现在安装? (y/n): ").lower().strip()
        if install == 'y':
            for package in missing_packages:
                print(f"正在安装 {package}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', package])
        else:
            print("请手动安装缺失的包后重试")
            return False
    
    return True


def setup_environment():
    """设置环境"""
    print("\n设置环境...")
    
    # 检查vnpy_datarecorder目录
    datarecorder_path = Path("vnpy_datarecorder")
    if not datarecorder_path.exists():
        print("✗ vnpy_datarecorder目录不存在")
        print("请确保已正确下载vnpy_datarecorder模块")
        return False
    
    print("✓ vnpy_datarecorder目录存在")
    
    # 检查示例目录
    examples_path = Path("examples/data_recorder")
    if examples_path.exists():
        print("✓ 数据录制示例目录已创建")
    else:
        print("✗ 数据录制示例目录不存在")
        return False
    
    return True


def show_usage_guide():
    """显示使用指南"""
    print("\n" + "="*60)
    print("VeighNa数据录制使用指南")
    print("="*60)
    
    print("\n1. 启动数据录制程序:")
    print("   python examples/data_recorder/run_data_recorder.py")
    
    print("\n2. 连接交易接口:")
    print("   - 启动富途牛牛客户端")
    print("   - 开启OpenD服务 (端口11111)")
    print("   - 在VeighNa界面中连接富途接口")
    
    print("\n3. 配置数据录制:")
    print("   - 点击菜单: 功能 -> 行情记录")
    print("   - 输入合约代码 (如: 00700.HK)")
    print("   - 添加Tick和K线录制")
    
    print("\n4. 测试数据录制:")
    print("   python examples/data_recorder/test_data_recording.py")
    
    print("\n5. 常用合约代码:")
    print("   港股: 00700.HK (腾讯), 00941.HK (中移动)")
    print("   美股: AAPL.US (苹果), MSFT.US (微软)")
    
    print("\n6. 数据存储位置:")
    print("   ~/.vnpy/database.db")
    
    print("\n详细说明请查看: examples/data_recorder/README.md")
    print("="*60)


def main():
    """主函数"""
    print("VeighNa数据录制环境检查和启动")
    print("-" * 40)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 设置环境
    if not setup_environment():
        return
    
    # 显示使用指南
    show_usage_guide()
    
    # 询问是否启动
    print("\n准备就绪!")
    start_choice = input("是否现在启动数据录制程序? (y/n): ").lower().strip()
    
    if start_choice == 'y':
        print("\n启动数据录制程序...")
        try:
            # 切换到示例目录并启动程序
            os.chdir("examples/data_recorder")
            subprocess.run([sys.executable, "run_data_recorder.py"])
        except KeyboardInterrupt:
            print("\n程序已停止")
        except Exception as e:
            print(f"\n启动失败: {e}")
    else:
        print("\n可以稍后手动启动:")
        print("cd examples/data_recorder")
        print("python run_data_recorder.py")


if __name__ == "__main__":
    main()
