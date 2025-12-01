"""ChartWindow 数据自动补齐功能测试

测试所有支持周期的数据自动补齐功能：
- 1分钟 (1m)
- 5分钟 (5m)
- 1小时 (1h)
- 4小时 (4h)
- 1天 (1d)

测试场景：
1. 从数据库补齐缺失数据
2. 从FUTU API补齐缺失数据
3. 检测并补齐与当前时间的gap
4. 历史数据完全缺失时的补齐
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from tzlocal import get_localzone_name

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.utility import ZoneInfo
from tests.chart.conftest import mock_main_engine, mock_event_engine


class TestChartWindowDataFilling:
    """ChartWindow数据自动补齐功能测试"""
    
    @pytest.fixture
    def chart_window(self, mock_main_engine, mock_event_engine, qtbot):
        """创建ChartWindow实例用于测试"""
        from vnpy.trader.ui.widget import ChartWindow
        
        window = ChartWindow(mock_main_engine, mock_event_engine)
        window.current_vt_symbol = "MHImain.HKFE"
        window.current_interval = "1m"
        window.current_data_source = "数据库"
        window.history_loaded = False
        window.history_data = []
        
        # Mock图表组件
        window.chart = Mock()
        window.chart.update_history = Mock()
        window.chart.update_bar = Mock()
        window.chart.set_future_bars = Mock()
        window.chart.set_vt_symbol = Mock()
        
        # Mock状态标签
        window.status_label = Mock()
        window.status_label.setText = Mock()
        window.status_label.setToolTip = Mock()
        window.status_label.setStyleSheet = Mock()
        
        # Mock时间滚动条
        window.time_slider = Mock()
        window.time_slider.setValue = Mock()
        
        return window
    
    @pytest.fixture
    def sample_bars_1m(self):
        """创建示例1分钟K线数据"""
        local_tz = ZoneInfo(get_localzone_name())
        base_time = datetime.now(local_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        
        bars = []
        for i in range(10):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                open_price=20000.0 + i,
                high_price=20005.0 + i,
                low_price=19995.0 + i,
                close_price=20002.0 + i,
                volume=100.0 + i * 10,
                turnover=2000000.0 + i * 200000,
                gateway_name="test"
            )
            bars.append(bar)
        return bars
    
    @pytest.fixture
    def sample_bars_5m(self):
        """创建示例5分钟K线数据"""
        local_tz = ZoneInfo(get_localzone_name())
        base_time = datetime.now(local_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        
        bars = []
        for i in range(5):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i * 5),
                interval=Interval.MINUTE_5,
                open_price=20000.0 + i * 5,
                high_price=20010.0 + i * 5,
                low_price=19990.0 + i * 5,
                close_price=20005.0 + i * 5,
                volume=500.0 + i * 50,
                turnover=10000000.0 + i * 1000000,
                gateway_name="test"
            )
            bars.append(bar)
        return bars
    
    def test_fill_missing_bars_1m_from_database(self, chart_window, sample_bars_1m):
        """测试1分钟数据从数据库补齐缺失数据"""
        from vnpy.trader.database import get_database
        
        # 准备测试数据：只有前5根和后5根，中间缺失
        partial_bars = sample_bars_1m[:5] + sample_bars_1m[8:]
        
        # Mock数据库
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=sample_bars_1m[5:8])
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_synthesize_missing_bars', return_value=[]):
                result = chart_window._fill_missing_bars(
                    partial_bars,
                    "MHImain",
                    Exchange.HKFE,
                    Interval.MINUTE,
                    sample_bars_1m[0].datetime,
                    sample_bars_1m[-1].datetime,
                    mock_database
                )
        
        # 验证：应该包含所有数据
        assert len(result) == len(sample_bars_1m)
        assert all(bar.datetime in [b.datetime for b in result] for bar in sample_bars_1m)
    
    def test_fill_missing_bars_5m_from_1m_synthesis(self, chart_window, sample_bars_5m):
        """测试5分钟数据从1分钟数据合成补齐"""
        from vnpy.trader.database import get_database
        
        # 准备测试数据：只有前2根和后2根，中间缺失
        partial_bars = sample_bars_5m[:2] + sample_bars_5m[3:]
        
        # Mock数据库和合成方法
        mock_database = Mock()
        synthesized_bars = sample_bars_5m[2:3]
        
        with patch.object(chart_window, '_synthesize_missing_bars', return_value=synthesized_bars):
            result = chart_window._fill_missing_bars(
                partial_bars,
                "MHImain",
                Exchange.HKFE,
                Interval.MINUTE_5,
                sample_bars_5m[0].datetime,
                sample_bars_5m[-1].datetime,
                mock_database
            )
        
        # 验证：应该包含所有数据
        assert len(result) == len(sample_bars_5m)
        assert all(bar.datetime in [b.datetime for b in result] for bar in sample_bars_5m)
    
    def test_fill_missing_bars_1h_from_1m_synthesis(self, chart_window):
        """测试1小时数据从1分钟数据合成补齐"""
        local_tz = ZoneInfo(get_localzone_name())
        base_time = datetime.now(local_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        
        # 创建1小时K线数据
        hour_bars = []
        for i in range(3):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(hours=i),
                interval=Interval.HOUR,
                open_price=20000.0 + i * 10,
                high_price=20020.0 + i * 10,
                low_price=19980.0 + i * 10,
                close_price=20010.0 + i * 10,
                volume=1000.0 + i * 100,
                turnover=20000000.0 + i * 2000000,
                gateway_name="test"
            )
            hour_bars.append(bar)
        
        # 只有第一根和第三根，中间缺失
        partial_bars = [hour_bars[0], hour_bars[2]]
        
        # Mock合成方法
        synthesized_bars = [hour_bars[1]]
        
        mock_database = Mock()
        with patch.object(chart_window, '_synthesize_missing_bars', return_value=synthesized_bars):
            result = chart_window._fill_missing_bars(
                partial_bars,
                "MHImain",
                Exchange.HKFE,
                Interval.HOUR,
                hour_bars[0].datetime,
                hour_bars[-1].datetime,
                mock_database
            )
        
        # 验证：应该包含所有数据
        assert len(result) == len(hour_bars)
    
    def test_fill_missing_bars_4h_from_1m_synthesis(self, chart_window):
        """测试4小时数据从1分钟数据合成补齐"""
        local_tz = ZoneInfo(get_localzone_name())
        base_time = datetime.now(local_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        
        # 创建4小时K线数据
        bars_4h = []
        for i in range(2):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(hours=i * 4),
                interval=Interval.HOUR_4,
                open_price=20000.0 + i * 20,
                high_price=20040.0 + i * 20,
                low_price=19960.0 + i * 20,
                close_price=20020.0 + i * 20,
                volume=2000.0 + i * 200,
                turnover=40000000.0 + i * 4000000,
                gateway_name="test"
            )
            bars_4h.append(bar)
        
        # 只有第一根，第二根缺失
        partial_bars = [bars_4h[0]]
        
        # Mock合成方法
        synthesized_bars = [bars_4h[1]]
        
        mock_database = Mock()
        with patch.object(chart_window, '_synthesize_missing_bars', return_value=synthesized_bars):
            result = chart_window._fill_missing_bars(
                partial_bars,
                "MHImain",
                Exchange.HKFE,
                Interval.HOUR_4,
                bars_4h[0].datetime,
                bars_4h[-1].datetime,
                mock_database
            )
        
        # 验证：应该包含所有数据
        assert len(result) == len(bars_4h)
    
    def test_detect_and_fill_gap_1m_from_database(self, chart_window, sample_bars_1m):
        """测试1分钟数据检测并补齐与当前时间的gap（从数据库）"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        
        # 历史数据只到1小时前
        old_bars = sample_bars_1m[:5]
        for bar in old_bars:
            bar.datetime = now - timedelta(hours=2) + timedelta(minutes=len(old_bars) - old_bars.index(bar) - 1)
        
        # Mock数据库返回gap期间的数据
        gap_bars = []
        gap_start = old_bars[-1].datetime + timedelta(minutes=1)
        gap_end = now - timedelta(minutes=1)
        current_time = gap_start
        while current_time < gap_end:
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            gap_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=gap_bars)
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=[]):
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.MINUTE
                )
        
        # 验证：应该包含历史数据和gap数据
        assert len(result) > len(old_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_1m_from_futu(self, chart_window, sample_bars_1m):
        """测试1分钟数据检测并补齐与当前时间的gap（从FUTU API）"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        
        # 历史数据只到1小时前
        old_bars = sample_bars_1m[:5]
        for bar in old_bars:
            bar.datetime = now - timedelta(hours=2) + timedelta(minutes=len(old_bars) - old_bars.index(bar) - 1)
        
        # Mock数据库返回空（没有数据）
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=[])
        
        # Mock FUTU API返回gap期间的数据
        gap_bars = []
        gap_start = old_bars[-1].datetime + timedelta(minutes=1)
        gap_end = now - timedelta(minutes=1)
        current_time = gap_start
        while current_time < gap_end and len(gap_bars) < 10:  # 限制数量避免测试时间过长
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            gap_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=gap_bars):
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.MINUTE
                )
        
        # 验证：应该包含历史数据和gap数据
        assert len(result) > len(old_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_5m_from_1m_synthesis(self, chart_window, sample_bars_5m):
        """测试5分钟数据检测并补齐与当前时间的gap（从1分钟数据合成）"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        
        # 历史数据只到1小时前
        old_bars = sample_bars_5m[:2]
        for bar in old_bars:
            bar.datetime = now - timedelta(hours=2) + timedelta(minutes=(len(old_bars) - old_bars.index(bar) - 1) * 5)
        
        # Mock数据库返回1分钟数据
        minute_bars = []
        gap_start = old_bars[-1].datetime + timedelta(minutes=5)
        gap_end = now - timedelta(minutes=5)
        current_time = gap_start
        while current_time < gap_end and len(minute_bars) < 20:  # 限制数量
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            minute_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=minute_bars)
        
        # Mock合成方法
        synthesized_bars = []
        for i in range(0, len(minute_bars), 5):
            if i + 5 <= len(minute_bars):
                bar = BarData(
                    symbol="MHImain",
                    exchange=Exchange.HKFE,
                    datetime=minute_bars[i].datetime.replace(minute=(minute_bars[i].minute // 5) * 5, second=0),
                    interval=Interval.MINUTE_5,
                    open_price=20000.0,
                    high_price=20010.0,
                    low_price=19990.0,
                    close_price=20005.0,
                    volume=500.0,
                    turnover=10000000.0,
                    gateway_name="test"
                )
                synthesized_bars.append(bar)
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=[]):
                # Mock _synthesize_bars_from_minute 方法
                def mock_synthesize(minute_bars, target_interval, symbol, exchange):
                    return synthesized_bars
                chart_window._synthesize_bars_from_minute = mock_synthesize
                
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.MINUTE_5
                )
        
        # 验证：应该包含历史数据和合成的gap数据
        assert len(result) > len(old_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_1h_from_1m_synthesis(self, chart_window):
        """测试1小时数据检测并补齐与当前时间的gap（从1分钟数据合成）"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        base_time = now - timedelta(hours=3)
        
        # 历史数据只到2小时前
        old_bars = [
            BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time,
                interval=Interval.HOUR,
                open_price=20000.0,
                high_price=20020.0,
                low_price=19980.0,
                close_price=20010.0,
                volume=1000.0,
                turnover=20000000.0,
                gateway_name="test"
            )
        ]
        
        # Mock数据库返回1分钟数据
        minute_bars = []
        gap_start = old_bars[-1].datetime + timedelta(hours=1)
        gap_end = now - timedelta(hours=1)
        current_time = gap_start
        while current_time < gap_end and len(minute_bars) < 30:  # 限制数量
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            minute_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=minute_bars)
        
        # Mock合成方法
        synthesized_bars = [
            BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=gap_start.replace(minute=0, second=0),
                interval=Interval.HOUR,
                open_price=20000.0,
                high_price=20020.0,
                low_price=19980.0,
                close_price=20010.0,
                volume=1000.0,
                turnover=20000000.0,
                gateway_name="test"
            )
        ]
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=[]):
                # Mock DataManager引擎不存在，使用通用合成方法
                chart_window.main_engine.get_engine = Mock(return_value=None)
                
                # Mock _synthesize_bars_from_minute 方法
                def mock_synthesize(minute_bars, target_interval, symbol, exchange):
                    return synthesized_bars
                chart_window._synthesize_bars_from_minute = mock_synthesize
                
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.HOUR
                )
        
        # 验证：应该包含历史数据和合成的gap数据
        assert len(result) > len(old_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_4h_from_1m_synthesis(self, chart_window):
        """测试4小时数据检测并补齐与当前时间的gap（从1分钟数据合成）"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        base_time = now - timedelta(hours=8)
        
        # 历史数据只到4小时前
        old_bars = [
            BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=base_time.replace(minute=0, second=0),
                interval=Interval.HOUR_4,
                open_price=20000.0,
                high_price=20040.0,
                low_price=19960.0,
                close_price=20020.0,
                volume=2000.0,
                turnover=40000000.0,
                gateway_name="test"
            )
        ]
        
        # Mock数据库返回1分钟数据
        minute_bars = []
        gap_start = old_bars[-1].datetime + timedelta(hours=4)
        gap_end = now - timedelta(hours=4)
        current_time = gap_start
        while current_time < gap_end and len(minute_bars) < 60:  # 限制数量
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            minute_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=minute_bars)
        
        # Mock合成方法
        synthesized_bars = [
            BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=gap_start.replace(minute=0, second=0),
                interval=Interval.HOUR_4,
                open_price=20000.0,
                high_price=20040.0,
                low_price=19960.0,
                close_price=20020.0,
                volume=2000.0,
                turnover=40000000.0,
                gateway_name="test"
            )
        ]
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=[]):
                # Mock _synthesize_bars_from_minute 方法
                def mock_synthesize(minute_bars, target_interval, symbol, exchange):
                    return synthesized_bars
                chart_window._synthesize_bars_from_minute = mock_synthesize
                
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.HOUR_4
                )
        
        # 验证：应该包含历史数据和合成的gap数据
        assert len(result) > len(old_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_no_gap(self, chart_window, sample_bars_1m):
        """测试没有gap时不进行补齐"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        
        # 历史数据到当前时间（没有gap）
        recent_bars = sample_bars_1m[:3]
        for i, bar in enumerate(recent_bars):
            bar.datetime = now - timedelta(minutes=len(recent_bars) - i)
        
        result = chart_window._detect_and_fill_gap(
            recent_bars,
            "MHImain.HKFE",
            Interval.MINUTE
        )
        
        # 验证：应该返回原始数据，不进行补齐
        assert len(result) == len(recent_bars)
        assert chart_window._has_data_gap is False
    
    def test_detect_and_fill_gap_fail_to_fetch(self, chart_window, sample_bars_1m):
        """测试无法获取gap数据时标记为有缺口"""
        local_tz = ZoneInfo(get_localzone_name())
        now = datetime.now(local_tz)
        
        # 历史数据只到1小时前
        old_bars = sample_bars_1m[:5]
        for bar in old_bars:
            bar.datetime = now - timedelta(hours=2) + timedelta(minutes=len(old_bars) - old_bars.index(bar) - 1)
        
        # Mock数据库和FUTU API都返回空
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=[])
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=[]):
                result = chart_window._detect_and_fill_gap(
                    old_bars,
                    "MHImain.HKFE",
                    Interval.MINUTE
                )
        
        # 验证：应该标记为有缺口
        assert len(result) == len(old_bars)  # 没有补齐
        assert chart_window._has_data_gap is True
        assert chart_window._gap_info != ""
    
    def test_load_history_data_1m_from_futu_when_empty(self, chart_window, mock_main_engine):
        """测试1分钟数据在数据库为空时从FUTU API获取"""
        from vnpy.trader.database import get_database
        
        local_tz = ZoneInfo(get_localzone_name())
        start = datetime.now(local_tz) - timedelta(days=7)
        end = datetime.now(local_tz)
        
        # Mock数据库返回空
        mock_database = Mock()
        mock_database.load_bar_data = Mock(return_value=[])
        
        # Mock FUTU API返回数据
        futu_bars = []
        current_time = start
        while current_time < end and len(futu_bars) < 10:  # 限制数量
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=current_time,
                interval=Interval.MINUTE,
                open_price=20000.0,
                high_price=20005.0,
                low_price=19995.0,
                close_price=20002.0,
                volume=100.0,
                turnover=2000000.0,
                gateway_name="test"
            )
            futu_bars.append(bar)
            current_time += timedelta(minutes=1)
        
        chart_window.current_interval = "1m"
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)
        
        with patch('vnpy.trader.database.get_database', return_value=mock_database):
            with patch.object(chart_window, '_fetch_bars_from_futu', return_value=futu_bars):
                with patch.object(chart_window, 'signal_history') as mock_signal:
                    # 模拟load_history_data的内部逻辑
                    chart_window.load_history_data("MHImain.HKFE")
                    
                    # 等待线程完成（在实际测试中可能需要更复杂的同步机制）
                    import time
                    time.sleep(0.1)
        
        # 验证：应该调用FUTU API
        chart_window._fetch_bars_from_futu.assert_called_once()
    
    def test_all_intervals_supported(self, chart_window):
        """测试所有支持的周期都在INTERVAL_MAP中"""
        expected_intervals = {
            "1分钟": "1m",
            "5分钟": "5m",
            "1小时": "1h",
            "4小时": "4h",
            "1天": "1d"
        }
        
        assert chart_window.INTERVAL_MAP == expected_intervals
        
        # 验证所有周期都能正确转换为Interval枚举
        from vnpy.trader.constant import Interval
        
        interval_mapping = {
            "1m": Interval.MINUTE,
            "5m": Interval.MINUTE_5,
            "1h": Interval.HOUR,
            "4h": Interval.HOUR_4,
            "1d": Interval.DAILY
        }
        
        for name, code in chart_window.INTERVAL_MAP.items():
            chart_window.current_interval = code
            interval_enum = chart_window._get_interval_enum()
            assert interval_enum == interval_mapping[code], f"{name} ({code}) 应该映射到 {interval_mapping[code]}"

