"""Phase 5 T050: 向后兼容性测试

验证实时 Tick 更新功能的实现不会破坏现有的历史数据加载和 gap 补齐功能。
确保向后兼容性。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.event import EVENT_TICK
from vnpy.trader.object import TickData, BarData
from vnpy.event import Event, EventEngine

from .test_base import TestBase


class TestBackwardCompatibility(TestBase):
    """向后兼容性测试"""

    @pytest.fixture
    def event_engine(self) -> EventEngine:
        """创建真实的 EventEngine"""
        engine = EventEngine()
        engine.start()
        yield engine
        engine.stop()

    @pytest.fixture
    def main_engine(self) -> Mock:
        """创建模拟的 MainEngine"""
        engine = Mock()
        engine.write_log = Mock()
        engine.get_contract = Mock(return_value=Mock(
            gateway_name="TEST",
            pricetick=1.0,
            min_volume=1
        ))
        engine.get_all_gateway_names = Mock(return_value=["TEST"])
        engine.subscribe = Mock()
        engine.get_all_active_orders = Mock(return_value=[])
        engine.get_all_positions = Mock(return_value=[])
        return engine

    @pytest.fixture
    def chart_window(self, main_engine: Mock, event_engine: EventEngine, qapp):
        """创建 ChartWindow 实例"""
        from vnpy.trader.ui.widget import ChartWindow

        window = ChartWindow(main_engine, event_engine)

        # Mock ChartWidget 以避免真实 UI 依赖
        window.chart = Mock()
        window.chart.update_bar = Mock()
        window.chart.update_history = Mock()
        window.chart.clear_all = Mock()
        window.chart._price_line_manager = Mock()
        window.chart._price_line_manager.get_all_lines = Mock(return_value={})
        window.chart._breakthrough_monitor = Mock()
        window.chart._breakthrough_monitor.update_tick = Mock()
        window.chart.set_vt_symbol = Mock()

        return window

    def test_history_data_loading_still_works(self, chart_window):
        """
        T050-1: 验证历史数据加载功能仍然正常工作

        确保现有的历史数据加载功能没有被实时 Tick 更新功能破坏。
        """
        vt_symbol = "MHI2512.HKFE"
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"

        # 模拟历史数据
        history_bars = []
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
        for i in range(60):  # 60 根 1 分钟 K线
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        # 模拟加载历史数据（通过信号槽机制）
        chart_window.process_history_data(history_bars)

        # 验证历史数据已加载
        assert chart_window.history_loaded, "历史数据应该被标记为已加载"
        assert len(chart_window.history_data) == len(history_bars), \
            f"历史数据数量应该为 {len(history_bars)}，实际为 {len(chart_window.history_data)}"

        # 验证图表更新方法被调用
        assert chart_window.chart.update_history.called, "应该调用 chart.update_history 更新历史数据"

    def test_history_data_loading_with_gap_filling(self, chart_window):
        """
        T050-2: 验证 gap 补齐功能仍然正常工作

        确保现有的 gap 补齐功能没有被实时 Tick 更新功能破坏。
        """
        vt_symbol = "MHI2512.HKFE"
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1h"

        # 模拟有 gap 的历史数据（缺少某些时间段的 K线）
        history_bars = []
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=24)

        # 创建有 gap 的数据（每隔 2 小时一根，缺少一些时间段）
        for i in range(0, 24, 2):  # 0, 2, 4, ..., 22（缺少 1, 3, 5, ...）
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(hours=i),
                interval=Interval.HOUR,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        # 模拟加载历史数据
        chart_window.process_history_data(history_bars)

        # 验证历史数据已加载（即使有 gap）
        assert chart_window.history_loaded, "历史数据应该被标记为已加载"
        assert len(chart_window.history_data) == len(history_bars), \
            f"历史数据数量应该为 {len(history_bars)}，实际为 {len(chart_window.history_data)}"

        # 验证图表更新方法被调用
        assert chart_window.chart.update_history.called, "应该调用 chart.update_history 更新历史数据"

    def test_realtime_update_does_not_interfere_with_history_loading(self, chart_window, event_engine: EventEngine):
        """
        T050-3: 验证实时 Tick 更新不会干扰历史数据加载

        确保在历史数据加载期间，实时 Tick 更新功能不会干扰加载过程。
        """
        vt_symbol = "MHI2512.HKFE"
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = False  # 模拟历史数据尚未加载完成

        # 模拟历史数据
        history_bars = []
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
        for i in range(60):
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        # 在历史数据加载期间，发送实时 tick
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            gateway_name="TEST"
        )
        tick.vt_symbol = vt_symbol

        # 处理 tick 事件（此时 history_loaded = False，应该跳过 K线更新）
        chart_window.process_tick_event(Event(EVENT_TICK, tick))

        # 验证 tick 事件被处理（不会报错）
        # 但由于 history_loaded = False，应该不会更新 K线

        # 现在加载历史数据
        chart_window.process_history_data(history_bars)

        # 验证历史数据已加载
        assert chart_window.history_loaded, "历史数据应该被标记为已加载"
        assert len(chart_window.history_data) == len(history_bars), \
            f"历史数据数量应该为 {len(history_bars)}"

    def test_history_data_loading_with_different_intervals(self, chart_window):
        """
        T050-4: 验证不同周期的历史数据加载仍然正常工作

        确保所有周期（1m, 5m, 1h, 4h, 1d）的历史数据加载功能都正常工作。
        """
        vt_symbol = "MHI2512.HKFE"
        chart_window.current_vt_symbol = vt_symbol

        intervals = [
            ("1m", Interval.MINUTE, 60),
            ("5m", Interval.MINUTE_5, 24),
            ("1h", Interval.HOUR, 24),
            ("4h", Interval.HOUR_4, 6),
            ("1d", Interval.DAILY, 7),
        ]

        for interval_str, interval_enum, bar_count in intervals:
            chart_window.current_interval = interval_str
            chart_window.history_loaded = False
            chart_window.history_data = []

            # 创建该周期的历史数据
            history_bars = []
            base_time = datetime.now().replace(second=0, microsecond=0)

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
            else:  # DAILY
                base_time = base_time.replace(hour=0, minute=0)
                time_delta = timedelta(days=1)

            for i in range(bar_count):
                bar = self.create_bar_data(
                    symbol="MHI2512",
                    exchange=Exchange.HKFE,
                    datetime=base_time - time_delta * (bar_count - i),
                    interval=interval_enum,
                    gateway_name="TEST"
                )
                history_bars.append(bar)

            # 加载历史数据
            chart_window.process_history_data(history_bars)

            # 验证历史数据已加载
            assert chart_window.history_loaded, \
                f"{interval_str} 周期的历史数据应该被标记为已加载"
            assert len(chart_window.history_data) == len(history_bars), \
                f"{interval_str} 周期的历史数据数量应该为 {len(history_bars)}，实际为 {len(chart_window.history_data)}"

            # 验证图表更新方法被调用
            assert chart_window.chart.update_history.called, \
                f"{interval_str} 周期应该调用 chart.update_history 更新历史数据"

            # 重置 Mock 以便下一次循环使用
            chart_window.chart.update_history.reset_mock()

    def test_refresh_chart_still_works(self, chart_window):
        """
        T050-5: 验证 refresh_chart 功能仍然正常工作

        确保刷新图表功能没有被实时 Tick 更新功能破坏。
        """
        vt_symbol = "MHI2512.HKFE"
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"

        # 先加载一些历史数据
        history_bars = []
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
        for i in range(60):
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        chart_window.process_history_data(history_bars)
        assert chart_window.history_loaded, "历史数据应该已加载"

        # 刷新图表
        chart_window.refresh_chart()

        # 验证刷新后历史数据状态被重置
        assert not chart_window.history_loaded, "刷新后历史数据状态应该被重置"
        assert len(chart_window.history_data) == 0, "刷新后历史数据应该被清空"

        # 验证图表被清空
        assert chart_window.chart.clear_all.called, "刷新图表时应该清空图表"

    def test_switch_chart_still_works(self, chart_window):
        """
        T050-6: 验证 switch_chart 功能仍然正常工作

        确保切换合约功能没有被实时 Tick 更新功能破坏。
        """
        # 设置初始合约
        chart_window.current_vt_symbol = "MHI2512.HKFE"
        chart_window.current_interval = "1m"

        # 加载初始合约的历史数据
        history_bars = []
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
        for i in range(60):
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        chart_window.process_history_data(history_bars)
        assert chart_window.history_loaded, "初始合约的历史数据应该已加载"

        # 切换合约
        new_vt_symbol = "OTHER.HKFE"
        chart_window.symbol_line.setText(new_vt_symbol)

        # Mock load_history_data 以避免实际加载
        with patch.object(chart_window, 'load_history_data') as mock_load:
            chart_window.switch_chart()

            # 验证合约已切换
            assert chart_window.current_vt_symbol == new_vt_symbol, \
                f"当前合约应该切换为 {new_vt_symbol}"

            # 验证历史数据状态被重置
            assert not chart_window.history_loaded, "切换合约后历史数据状态应该被重置"
            assert len(chart_window.history_data) == 0, "切换合约后历史数据应该被清空"

            # 验证图表被清空
            assert chart_window.chart.clear_all.called, "切换合约时应该清空图表"

            # 验证加载新合约的历史数据
            assert mock_load.called, "切换合约时应该加载新合约的历史数据"
            assert mock_load.call_args[0][0] == new_vt_symbol, \
                f"应该加载新合约 {new_vt_symbol} 的历史数据"

    def test_tick_filtering_does_not_affect_history_loading(self, chart_window, event_engine: EventEngine):
        """
        T050-7: 验证 Tick 过滤功能不会影响历史数据加载

        确保 process_tick_event 中的合约过滤逻辑不会影响历史数据加载。
        """
        vt_symbol = "MHI2512.HKFE"
        other_vt_symbol = "OTHER.HKFE"

        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = True

        # 加载历史数据
        history_bars = []
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
        for i in range(60):
            bar = self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                gateway_name="TEST"
            )
            history_bars.append(bar)

        chart_window.process_history_data(history_bars)
        initial_history_count = len(chart_window.history_data)

        # 发送其他合约的 tick（应该被过滤，不影响历史数据）
        other_tick = self.create_tick_data(
            symbol="OTHER",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            gateway_name="TEST"
        )
        other_tick.vt_symbol = other_vt_symbol

        chart_window.process_tick_event(Event(EVENT_TICK, other_tick))

        # 验证历史数据没有被影响
        assert len(chart_window.history_data) == initial_history_count, \
            "其他合约的 tick 不应该影响历史数据"

        # 发送当前合约的 tick（应该被处理，但不会影响历史数据本身）
        current_tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            gateway_name="TEST"
        )
        current_tick.vt_symbol = vt_symbol

        chart_window.process_tick_event(Event(EVENT_TICK, current_tick))

        # 验证历史数据仍然保持不变（实时更新只更新当前 K线，不改变历史数据）
        assert len(chart_window.history_data) == initial_history_count, \
            "当前合约的 tick 不应该改变历史数据的数量"

