"""
数据录制配置示例
展示如何通过代码配置数据录制
"""

from vnpy_datarecorder.engine import RecorderEngine
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine


class DataRecorderConfig:
    """数据录制配置类"""
    
    def __init__(self, main_engine: MainEngine):
        self.main_engine = main_engine
        self.recorder_engine: RecorderEngine = main_engine.get_engine("DataRecorder")
    
    def setup_stock_recording(self):
        """配置股票数据录制"""
        # 港股示例
        hk_stocks = [
            "00700.HK",  # 腾讯控股
            "00941.HK",  # 中国移动
            "01299.HK",  # 友邦保险
            "02318.HK",  # 中国平安
            "03690.HK",  # 美团
        ]
        
        for symbol in hk_stocks:
            # 添加Tick数据录制
            self.recorder_engine.add_tick_recording(symbol)
            # 添加K线数据录制
            self.recorder_engine.add_bar_recording(symbol)
            print(f"已添加 {symbol} 的数据录制")
    
    def setup_futures_recording(self):
        """配置期货数据录制"""
        # 期货合约示例（需要根据实际可用合约调整）
        futures = [
            "HSI2412.HKFE",  # 恒生指数期货
            "MHI2412.HKFE",  # 小型恒生指数期货
        ]
        
        for symbol in futures:
            # 添加Tick数据录制
            self.recorder_engine.add_tick_recording(symbol)
            # 添加K线数据录制
            self.recorder_engine.add_bar_recording(symbol)
            print(f"已添加 {symbol} 的数据录制")
    
    def setup_etf_recording(self):
        """配置ETF数据录制"""
        # ETF示例
        etfs = [
            "02800.HK",  # 盈富基金
            "02828.HK",  # 恒生中国企业
            "03188.HK",  # 华夏沪深三百
        ]
        
        for symbol in etfs:
            # 添加Tick数据录制
            self.recorder_engine.add_tick_recording(symbol)
            # 添加K线数据录制
            self.recorder_engine.add_bar_recording(symbol)
            print(f"已添加 {symbol} 的数据录制")
    
    def remove_recording(self, symbol: str):
        """移除指定合约的数据录制"""
        self.recorder_engine.remove_tick_recording(symbol)
        self.recorder_engine.remove_bar_recording(symbol)
        print(f"已移除 {symbol} 的数据录制")
    
    def get_recording_status(self):
        """获取当前录制状态"""
        tick_recordings = list(self.recorder_engine.tick_recordings.keys())
        bar_recordings = list(self.recorder_engine.bar_recordings.keys())
        
        print("当前Tick录制列表:")
        for symbol in tick_recordings:
            print(f"  - {symbol}")
        
        print("当前K线录制列表:")
        for symbol in bar_recordings:
            print(f"  - {symbol}")
        
        return tick_recordings, bar_recordings


def setup_recording_example(main_engine: MainEngine):
    """数据录制设置示例"""
    config = DataRecorderConfig(main_engine)
    
    # 设置股票录制
    config.setup_stock_recording()
    
    # 设置ETF录制
    config.setup_etf_recording()
    
    # 获取录制状态
    config.get_recording_status()
    
    return config
