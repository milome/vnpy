"""
VeighNa数据录制示例
用于录制实时K线和Tick数据，为策略开发和回测提供数据支持
"""

import sys
sys.path.insert(0, 'D:/Dev/vnpy/vnpy_futu')

from vnpy_futu.futu_gateway import FutuGateway
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.setting import SETTINGS

# 导入数据录制相关模块
from vnpy_datarecorder import DataRecorderApp
from vnpy_datamanager import DataManagerApp


def main():
    """启动数据录制程序"""
    
    # 配置数据服务
    if not SETTINGS.get("datafeed.name"):
        # 使用富途数据服务
        SETTINGS["datafeed.name"] = "futu"
        SETTINGS["datafeed.host"] = "127.0.0.1"
        SETTINGS["datafeed.port"] = 11111
    
    # 创建Qt应用
    qapp = create_qapp()
    
    # 创建事件引擎
    event_engine = EventEngine()
    
    # 创建主引擎
    main_engine = MainEngine(event_engine)
    
    # 添加交易接口
    main_engine.add_gateway(FutuGateway)
    
    # 添加应用模块
    main_engine.add_app(DataRecorderApp)  # 数据录制
    main_engine.add_app(DataManagerApp)   # 数据管理
    
    # 创建主窗口
    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()
    
    # 启动应用
    qapp.exec()


if __name__ == "__main__":
    main()
