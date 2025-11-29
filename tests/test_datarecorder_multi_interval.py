"""
DataRecorder多周期K线录制功能测试

测试内容：
1. 周期工具函数测试（时间划分、开盘价获取）
2. 多周期K线录制功能测试
3. 港期时间划分机制测试
4. 开盘价自动更新测试
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData, TickData, ContractData
from vnpy.trader.database import BaseDatabase

from vnpy.trader.period_utils import (
    get_period_start,
    get_hkfe_hour_period_start,
    is_hkfe_trading_time,
    get_hkfe_4hour_period,
    PeriodOpenPriceHelper
)
from vnpy_datarecorder.engine import RecorderEngine


class TestPeriodUtils(unittest.TestCase):
    """周期工具函数测试"""
    
    def test_get_period_start_minute_5(self):
        """测试5分钟周期时间划分"""
        dt = datetime(2024, 1, 1, 14, 33, 0)
        period_start = get_period_start(dt, Interval.MINUTE_5)
        self.assertEqual(period_start, datetime(2024, 1, 1, 14, 30, 0))
        
        dt = datetime(2024, 1, 1, 14, 37, 0)
        period_start = get_period_start(dt, Interval.MINUTE_5)
        self.assertEqual(period_start, datetime(2024, 1, 1, 14, 35, 0))
    
    def test_get_period_start_hour_standard(self):
        """测试标准交易所1小时周期时间划分"""
        dt = datetime(2024, 1, 1, 14, 30, 0)
        period_start = get_period_start(dt, Interval.HOUR, Exchange.SHFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 14, 0, 0))
    
    def test_get_hkfe_hour_period_start(self):
        """测试港期1小时周期时间划分"""
        # 夜盘时段
        dt = datetime(2024, 1, 1, 17, 30, 0)
        period_start = get_hkfe_hour_period_start(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 17, 15, 0))
        
        dt = datetime(2024, 1, 1, 18, 30, 0)
        period_start = get_hkfe_hour_period_start(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 18, 15, 0))
        
        # 日盘时段
        dt = datetime(2024, 1, 1, 9, 45, 0)
        period_start = get_hkfe_hour_period_start(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 9, 30, 0))
        
        dt = datetime(2024, 1, 1, 11, 45, 0)
        period_start = get_hkfe_hour_period_start(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 11, 30, 0))
    
    def test_get_hkfe_4hour_period_start(self):
        """测试港期4小时周期时间划分"""
        # 时段1: 17:15-21:14
        dt = datetime(2024, 1, 1, 19, 0, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 17, 15, 0))
        
        # 时段2: 21:15-01:14
        dt = datetime(2024, 1, 1, 23, 0, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 21, 15, 0))
        
        # 时段2后半（跨日）
        dt = datetime(2024, 1, 2, 0, 30, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 21, 15, 0))
        
        # 时段3: 01:15-03:00 + 09:15-11:29
        dt = datetime(2024, 1, 1, 2, 0, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 1, 15, 0))
        
        dt = datetime(2024, 1, 1, 10, 0, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        # 周一需要回溯到周六
        if dt.weekday() == 0:  # 周一
            expected = datetime(2023, 12, 30, 1, 15, 0)  # 上周六
        else:
            expected = datetime(2024, 1, 1, 1, 15, 0)
        self.assertEqual(period_start, expected)
        
        # 时段4: 11:30-12:00 + 13:00-16:29
        dt = datetime(2024, 1, 1, 14, 0, 0)
        period_start = get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)
        self.assertEqual(period_start, datetime(2024, 1, 1, 11, 30, 0))
    
    def test_is_hkfe_trading_time(self):
        """测试港期交易时段判断"""
        # 日盘早段
        dt = datetime(2024, 1, 1, 10, 0, 0)
        self.assertTrue(is_hkfe_trading_time(dt))
        
        # 日盘午段
        dt = datetime(2024, 1, 1, 14, 0, 0)
        self.assertTrue(is_hkfe_trading_time(dt))
        
        # 夜盘
        dt = datetime(2024, 1, 1, 20, 0, 0)
        self.assertTrue(is_hkfe_trading_time(dt))
        
        # 非交易时段
        dt = datetime(2024, 1, 1, 8, 0, 0)
        self.assertFalse(is_hkfe_trading_time(dt))
    
    def test_get_hkfe_4hour_period(self):
        """测试港期4小时周期函数（返回period_index）"""
        # 时段1
        dt = datetime(2024, 1, 1, 19, 0, 0)
        period_start, period_index = get_hkfe_4hour_period(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 17, 15, 0))
        self.assertEqual(period_index, 1)
        
        # 时段2
        dt = datetime(2024, 1, 1, 23, 0, 0)
        period_start, period_index = get_hkfe_4hour_period(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 21, 15, 0))
        self.assertEqual(period_index, 2)
        
        # 时段3
        dt = datetime(2024, 1, 1, 10, 0, 0)
        period_start, period_index = get_hkfe_4hour_period(dt)
        if dt.weekday() == 0:  # 周一
            expected = datetime(2023, 12, 30, 1, 15, 0)
        else:
            expected = datetime(2024, 1, 1, 1, 15, 0)
        self.assertEqual(period_start, expected)
        self.assertEqual(period_index, 3)
        
        # 时段4
        dt = datetime(2024, 1, 1, 14, 0, 0)
        period_start, period_index = get_hkfe_4hour_period(dt)
        self.assertEqual(period_start, datetime(2024, 1, 1, 11, 30, 0))
        self.assertEqual(period_index, 4)


class TestPeriodOpenPriceHelper(unittest.TestCase):
    """开盘价获取辅助类测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.database = Mock(spec=BaseDatabase)
        self.helper = PeriodOpenPriceHelper(self.database)
    
    def test_get_period_open_price_minute(self):
        """测试1分钟周期开盘价（直接使用tick价格）"""
        tick = Mock(spec=TickData)
        tick.last_price = 100.0
        
        open_price = self.helper.get_period_open_price(
            datetime(2024, 1, 1, 14, 30, 0),
            Interval.MINUTE,
            "rb2401.SHFE",
            tick=tick
        )
        
        self.assertEqual(open_price, 100.0)
    
    def test_get_period_open_price_from_cache(self):
        """测试从缓存获取开盘价"""
        # 创建1分钟K线并缓存
        minute_bar = Mock(spec=BarData)
        minute_bar.open_price = 100.0
        minute_bar.datetime = datetime(2024, 1, 1, 14, 30, 0)
        minute_bar.interval = Interval.MINUTE
        
        period_start = datetime(2024, 1, 1, 14, 30, 0)
        self.helper._minute_bars_cache[period_start] = minute_bar
        
        open_price = self.helper.get_period_open_price(
            period_start,
            Interval.MINUTE_5,
            "rb2401.SHFE"
        )
        
        self.assertEqual(open_price, 100.0)
    
    def test_get_period_open_price_from_database(self):
        """测试从数据库获取开盘价"""
        # 模拟数据库返回
        minute_bar = Mock(spec=BarData)
        minute_bar.open_price = 100.0
        minute_bar.datetime = datetime(2024, 1, 1, 14, 30, 0)
        
        self.database.load_bar_data.return_value = [minute_bar]
        
        open_price = self.helper.get_period_open_price(
            datetime(2024, 1, 1, 14, 30, 0),
            Interval.MINUTE_5,
            "rb2401.SHFE"
        )
        
        self.assertEqual(open_price, 100.0)
        # 验证缓存已更新
        self.assertIn(datetime(2024, 1, 1, 14, 30, 0), self.helper._minute_bars_cache)
    
    def test_cache_minute_bar(self):
        """测试缓存1分钟K线"""
        minute_bar = Mock(spec=BarData)
        minute_bar.interval = Interval.MINUTE
        minute_bar.datetime = datetime(2024, 1, 1, 14, 30, 0)
        minute_bar.exchange = Exchange.SHFE
        
        self.helper.cache_minute_bar(minute_bar)
        
        period_start = get_period_start(
            minute_bar.datetime,
            Interval.MINUTE,
            minute_bar.exchange
        )
        self.assertIn(period_start, self.helper._minute_bars_cache)


class TestRecorderEngineMultiInterval(unittest.TestCase):
    """DataRecorder多周期录制功能测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.main_engine = Mock()
        self.event_engine = Mock()
        
        # 创建RecorderEngine实例
        with patch('vnpy_datarecorder.engine.get_database'):
            self.engine = RecorderEngine(self.main_engine, self.event_engine)
            self.engine.active = False  # 不启动线程
    
    def test_add_bar_recording_single_interval(self):
        """测试添加单周期K线录制"""
        contract = Mock(spec=ContractData)
        contract.symbol = "rb2401"
        contract.exchange = Exchange.SHFE
        contract.gateway_name = "CTP"
        contract.vt_symbol = "rb2401.SHFE"
        
        self.main_engine.get_contract.return_value = contract
        
        self.engine.add_bar_recording("rb2401.SHFE", [Interval.MINUTE])
        
        self.assertIn("rb2401.SHFE", self.engine.bar_recordings)
        self.assertEqual(
            self.engine.bar_recordings["rb2401.SHFE"]["intervals"],
            [Interval.MINUTE.value]
        )
    
    def test_add_bar_recording_multi_interval(self):
        """测试添加多周期K线录制"""
        contract = Mock(spec=ContractData)
        contract.symbol = "rb2401"
        contract.exchange = Exchange.SHFE
        contract.gateway_name = "CTP"
        contract.vt_symbol = "rb2401.SHFE"
        
        self.main_engine.get_contract.return_value = contract
        
        intervals = [Interval.MINUTE, Interval.MINUTE_5, Interval.HOUR]
        self.engine.add_bar_recording("rb2401.SHFE", intervals)
        
        self.assertIn("rb2401.SHFE", self.engine.bar_recordings)
        recorded_intervals = self.engine.bar_recordings["rb2401.SHFE"]["intervals"]
        self.assertEqual(len(recorded_intervals), 3)
        self.assertIn(Interval.MINUTE.value, recorded_intervals)
        self.assertIn(Interval.MINUTE_5.value, recorded_intervals)
        self.assertIn(Interval.HOUR.value, recorded_intervals)
    
    def test_add_bar_recording_update_intervals(self):
        """测试更新已存在的录制任务的周期"""
        contract = Mock(spec=ContractData)
        contract.symbol = "rb2401"
        contract.exchange = Exchange.SHFE
        contract.gateway_name = "CTP"
        contract.vt_symbol = "rb2401.SHFE"
        
        self.main_engine.get_contract.return_value = contract
        
        # 先添加1分钟
        self.engine.add_bar_recording("rb2401.SHFE", [Interval.MINUTE])
        
        # 再添加5分钟
        self.engine.add_bar_recording("rb2401.SHFE", [Interval.MINUTE_5])
        
        recorded_intervals = self.engine.bar_recordings["rb2401.SHFE"]["intervals"]
        self.assertEqual(len(recorded_intervals), 2)
        self.assertIn(Interval.MINUTE.value, recorded_intervals)
        self.assertIn(Interval.MINUTE_5.value, recorded_intervals)
    
    def test_get_recording_intervals(self):
        """测试获取录制周期列表"""
        contract = Mock(spec=ContractData)
        contract.symbol = "rb2401"
        contract.exchange = Exchange.SHFE
        contract.gateway_name = "CTP"
        contract.vt_symbol = "rb2401.SHFE"
        
        self.main_engine.get_contract.return_value = contract
        
        intervals = [Interval.MINUTE, Interval.MINUTE_5]
        self.engine.add_bar_recording("rb2401.SHFE", intervals)
        
        recorded_intervals = self.engine._get_recording_intervals("rb2401.SHFE")
        self.assertEqual(len(recorded_intervals), 2)
        self.assertIn(Interval.MINUTE, recorded_intervals)
        self.assertIn(Interval.MINUTE_5, recorded_intervals)


if __name__ == '__main__':
    unittest.main()

