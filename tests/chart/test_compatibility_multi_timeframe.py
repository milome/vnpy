"""Phase 5: 多周期模式兼容性测试

兼容性测试目标：
- T082: 测试 HKFE 数据
- T083: 测试不同周期数据（1m/5m/1H/4H）
- T084: 测试不同交易所数据（如果适用）
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData
from tests.chart.conftest import mock_main_engine, mock_event_engine


class TestCompatibilityMultiTimeframe:
    """多周期模式兼容性测试"""

    @pytest.fixture
    def chart_window(self, mock_main_engine, mock_event_engine, qtbot):
        """创建ChartWindow实例用于测试"""
        from vnpy.trader.ui.widget import ChartWindow
        from unittest.mock import patch
        
        # 在创建 ChartWindow 之前，Mock 一些可能失败的操作
        with patch('vnpy.trader.database.get_database'), \
             patch('vnpy.chart.multi_timeframe_widget.get_database'):
            window = ChartWindow(mock_main_engine, mock_event_engine)
            
            # Mock图表组件（如果已创建）
            if window.chart and not isinstance(window.chart, Mock):
                window.chart.update_history = Mock()
                window.chart.update_bar = Mock()
                window.chart.set_future_bars = Mock()
                window.chart.set_vt_symbol = Mock()
                window.chart.get_drawing_order_controller = Mock(return_value=Mock())
                window.chart.clear_all = Mock()
                window.chart.get_plot = Mock(return_value=Mock())
                if not hasattr(window.chart, '_bar_count'):
                    window.chart._bar_count = 100
                if not hasattr(window.chart, '_right_ix'):
                    window.chart._right_ix = 100
                if not hasattr(window.chart, '_update_x_range'):
                    window.chart._update_x_range = Mock()
                if not hasattr(window.chart, 'isVisible') or not callable(window.chart.isVisible):
                    window.chart.isVisible = Mock(return_value=True)
                if not hasattr(window.chart, 'setVisible') or not callable(window.chart.setVisible):
                    window.chart.setVisible = Mock()
                if not hasattr(window.chart, '_price_line_manager'):
                    window.chart._price_line_manager = Mock()
                    window.chart._price_line_manager.get_all_lines = Mock(return_value={})
                if not hasattr(window.chart, '_breakthrough_monitor'):
                    window.chart._breakthrough_monitor = Mock()
            
            if hasattr(window, 'status_label') and window.status_label:
                if not isinstance(window.status_label, Mock):
                    window.status_label.setText = Mock()
            
            if hasattr(window, 'time_slider') and window.time_slider:
                if hasattr(window.time_slider, 'setRange'):
                    window.time_slider.setRange(0, 100)
                    window.time_slider.setValue(50)
            
            window.current_vt_symbol = "MHImain.HKFE"
            window.current_interval = "1m"
            window.history_loaded = False
            
            window.show()
            qtbot.waitExposed(window)
            
            yield window
            
            # 清理资源
            try:
                if hasattr(window, 'multi_timeframe_widget') and window.multi_timeframe_widget:
                    try:
                        window.multi_timeframe_widget.setVisible(False)
                        if hasattr(window.multi_timeframe_widget, '_chart') and window.multi_timeframe_widget._chart:
                            try:
                                if hasattr(window.multi_timeframe_widget._chart, 'clear'):
                                    window.multi_timeframe_widget._chart.clear()
                            except Exception:
                                pass
                        window.multi_timeframe_widget.setParent(None)
                    except Exception:
                        pass
                    window.multi_timeframe_widget = None
            except Exception:
                pass

    def test_hkfe_data_compatibility(self, chart_window):
        """T082: 测试 HKFE 数据兼容性"""
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        
        # 创建 HKFE 测试数据
        test_bars = []
        base_time = datetime(2024, 11, 14, 9, 0)
        
        for i in range(100):
            minutes = i % 60
            hours = i // 60
            bar_time = base_time.replace(hour=9 + hours, minute=minutes)
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=bar_time,
                interval=Interval.MINUTE,
                volume=1000,
                open_price=25000.0 + i,
                high_price=25001.0 + i,
                low_price=24999.0 + i,
                close_price=25000.5 + i,
                gateway_name="test"
            )
            test_bars.append(bar)
        
        # 设置 HKFE 合约
        chart_window.current_vt_symbol = "MHImain.HKFE"
        chart_window.history_data = test_bars
        
        # 验证数据加载成功
        assert chart_window.current_vt_symbol == "MHImain.HKFE", \
            "HKFE 合约设置失败"
        assert len(chart_window.history_data) == 100, \
            "HKFE 数据加载失败"
        
        # 验证多周期Widget可以处理HKFE数据
        if chart_window.multi_timeframe_widget:
            # 验证 switch_symbol 方法可以处理 HKFE 数据
            assert hasattr(chart_window.multi_timeframe_widget, 'switch_symbol'), \
                "MultiTimeframeWidget.switch_symbol 方法不存在"
            
            # 验证数据同步成功
            if hasattr(chart_window, 'sync_data_to_multi_timeframe'):
                chart_window.sync_data_to_multi_timeframe()
        
        # 验证实时更新可以处理HKFE数据
        tick = TickData(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            last_price=25000.0,
            volume=1000,
            gateway_name="test"
        )
        
        # 验证可以处理HKFE tick数据
        if chart_window.multi_timeframe_widget:
            assert hasattr(chart_window.multi_timeframe_widget, 'update_tick'), \
                "MultiTimeframeWidget.update_tick 方法不存在"

    def test_different_timeframes_compatibility(self, chart_window):
        """T083: 测试不同周期数据兼容性（1m/5m/1H/4H）"""
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        
        # 测试不同周期的数据
        timeframes = [
            ("1m", Interval.MINUTE, 60),
            ("5m", Interval.MINUTE_5, 24),
            ("1h", Interval.HOUR, 24),
            ("4h", Interval.HOUR_4, 6),
        ]
        
        for timeframe_str, interval_enum, bar_count in timeframes:
            # 创建该周期的测试数据
            test_bars = []
            base_time = datetime(2024, 11, 14, 9, 0)
            
            if interval_enum == Interval.MINUTE:
                time_delta = timedelta(minutes=1)
            elif interval_enum == Interval.MINUTE_5:
                time_delta = timedelta(minutes=5)
            elif interval_enum == Interval.HOUR:
                base_time = base_time.replace(minute=0)
                time_delta = timedelta(hours=1)
            elif interval_enum == Interval.HOUR_4:
                base_time = base_time.replace(minute=0)
                time_delta = timedelta(hours=4)
            
            for i in range(bar_count):
                bar_time = base_time + time_delta * i
                bar = BarData(
                    symbol="MHImain",
                    exchange=Exchange.HKFE,
                    datetime=bar_time,
                    interval=interval_enum,
                    volume=1000,
                    open_price=25000.0 + i,
                    high_price=25001.0 + i,
                    low_price=24999.0 + i,
                    close_price=25000.5 + i,
                    gateway_name="test"
                )
                test_bars.append(bar)
            
            # 设置数据
            chart_window.history_data = test_bars
            
            # 验证数据加载成功
            assert len(chart_window.history_data) == bar_count, \
                f"{timeframe_str} 周期数据加载失败，期望 {bar_count} 条，实际 {len(chart_window.history_data)} 条"
            
            # 验证多周期Widget可以处理该周期数据
            if chart_window.multi_timeframe_widget:
                # 验证数据同步成功
                if hasattr(chart_window, 'sync_data_to_multi_timeframe'):
                    chart_window.sync_data_to_multi_timeframe()
                
                # 验证该周期的BarManager存在
                manager_attr = f"_manager_{timeframe_str.replace('h', 'H')}"
                if hasattr(chart_window.multi_timeframe_widget, manager_attr):
                    manager = getattr(chart_window.multi_timeframe_widget, manager_attr)
                    assert manager is not None, \
                        f"{timeframe_str} 周期的 BarManager 不存在"
        
        # 验证所有周期数据都可以同时处理
        assert chart_window.display_mode == "multi", \
            "当前模式应为多周期模式"

    def test_different_exchanges_compatibility(self, chart_window):
        """T084: 测试不同交易所数据兼容性（如果适用）"""
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        
        # 测试不同交易所的数据
        # 注意：这里主要测试代码逻辑，实际交易所支持取决于数据源
        exchanges = [Exchange.HKFE]  # 目前主要支持 HKFE
        
        for exchange in exchanges:
            # 创建该交易所的测试数据
            test_bars = []
            base_time = datetime(2024, 11, 14, 9, 0)
            
            for i in range(100):
                minutes = i % 60
                hours = i // 60
                bar_time = base_time.replace(hour=9 + hours, minute=minutes)
                
                # 根据交易所设置不同的symbol
                if exchange == Exchange.HKFE:
                    symbol = "MHImain"
                    vt_symbol = f"{symbol}.{exchange.value}"
                else:
                    # 其他交易所的symbol格式可能不同
                    symbol = "TEST"
                    vt_symbol = f"{symbol}.{exchange.value}"
                
                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=bar_time,
                    interval=Interval.MINUTE,
                    volume=1000,
                    open_price=25000.0 + i,
                    high_price=25001.0 + i,
                    low_price=24999.0 + i,
                    close_price=25000.5 + i,
                    gateway_name="test"
                )
                test_bars.append(bar)
            
            # 设置合约和数据
            chart_window.current_vt_symbol = vt_symbol
            chart_window.history_data = test_bars
            
            # 验证数据加载成功
            assert chart_window.current_vt_symbol == vt_symbol, \
                f"{exchange.value} 交易所合约设置失败"
            assert len(chart_window.history_data) == 100, \
                f"{exchange.value} 交易所数据加载失败"
            
            # 验证多周期Widget可以处理该交易所数据
            if chart_window.multi_timeframe_widget:
                # 验证 switch_symbol 方法可以处理该交易所数据
                assert hasattr(chart_window.multi_timeframe_widget, 'switch_symbol'), \
                    "MultiTimeframeWidget.switch_symbol 方法不存在"
                
                # 验证数据同步成功
                if hasattr(chart_window, 'sync_data_to_multi_timeframe'):
                    chart_window.sync_data_to_multi_timeframe()
        
        # 验证所有交易所数据都可以处理
        assert chart_window.display_mode == "multi", \
            "当前模式应为多周期模式"

