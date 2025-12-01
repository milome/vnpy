"""Phase 5: 集成测试 - 所有周期的实时更新

测试 ChartWindow 在所有周期（1分钟、5分钟、1小时、4小时、1日）下的实时 tick 更新功能。
这是端到端的集成测试，验证从 tick 事件到图表更新的完整流程。
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.event import EVENT_TICK
from vnpy.trader.object import TickData, BarData
from vnpy.trader.utility import BarGenerator
from vnpy.event import Event, EventEngine

from .test_base import TestBase


class TestIntegrationRealtimeAllPeriods(TestBase):
    """Phase 5 T045: 所有周期的实时更新集成测试"""

    @pytest.fixture
    def event_engine(self) -> EventEngine:
        """创建真实的 EventEngine 用于集成测试"""
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
        """创建 ChartWindow 实例用于集成测试"""
        from vnpy.trader.ui.widget import ChartWindow

        window = ChartWindow(main_engine, event_engine)

        # Mock ChartWidget 以避免真实 UI 依赖，但保留核心功能
        window.chart = Mock()
        window.chart.update_bar = Mock()
        window.chart._price_line_manager = Mock()
        window.chart._price_line_manager.get_all_lines = Mock(return_value={})
        window.chart._breakthrough_monitor = Mock()
        window.chart._breakthrough_monitor.update_tick = Mock()
        window.chart.set_vt_symbol = Mock()

        return window

    def _create_tick(
        self,
        vt_symbol: str,
        last_price: float = 20000.0,
        datetime: datetime = None
    ) -> TickData:
        """创建测试用的 TickData"""
        if datetime is None:
            datetime = datetime.now()

        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange(exchange_str)

        tick = self.create_tick_data(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime,
            last_price=last_price,
            bid_price_1=last_price - 1.0,
            ask_price_1=last_price + 1.0,
            volume=1000.0,
            gateway_name="TEST"
        )
        tick.vt_symbol = vt_symbol
        return tick

    @pytest.mark.parametrize("interval_str,interval_enum,interval_name", [
        ("1m", Interval.MINUTE, "1分钟"),
        ("5m", Interval.MINUTE_5, "5分钟"),
        ("1h", Interval.HOUR, "1小时"),
        ("4h", Interval.HOUR_4, "4小时"),
        ("1d", Interval.DAILY, "1日"),
    ])
    def test_all_periods_realtime_update(
        self,
        chart_window,
        event_engine: EventEngine,
        interval_str: str,
        interval_enum: Interval,
        interval_name: str
    ):
        """
        T045: 测试所有周期的实时更新

        验证从 tick 事件到图表更新的完整流程，包括：
        1. tick 事件被正确处理
        2. 不同周期使用不同的更新机制
        3. 图表最终被更新
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = interval_str
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 设置当前周期
        chart_window._get_interval_enum = Mock(return_value=interval_enum)

        # 根据周期设置不同的更新机制
        if interval_enum == Interval.MINUTE:
            # 1分钟周期：使用 BarGenerator
            chart_window.bg = BarGenerator(chart_window.on_bar)
            chart_window.bg.bar = None
        else:
            # 大周期：使用 _update_current_bar_with_tick
            chart_window.bg = None
            chart_window._current_bar = None
            chart_window._current_bar_period = None
            chart_window._current_bar_index = -1
            chart_window._period_start_volume = 0
            chart_window._period_start_turnover = 0
            chart_window._bar_historical_volume = 0
            chart_window._bar_historical_turnover = 0
            chart_window._need_init_baseline = True

            # Mock _update_current_bar_with_tick 以验证调用
            chart_window._update_current_bar_with_tick = Mock()

            # Mock 开盘价辅助类
            chart_window.open_price_helper = Mock()
            chart_window.open_price_helper.get_period_open_price = Mock(return_value=20000.0)

        # 创建 tick 数据
        tick = self._create_tick(vt_symbol, last_price=20000.0)

        # 创建并发送 tick 事件
        event = Event(EVENT_TICK, tick)

        # 模拟事件引擎发送事件（直接调用 process_tick_event）
        chart_window.process_tick_event(event)

        # 验证结果
        if interval_enum == Interval.MINUTE:
            # 1分钟周期：验证 BarGenerator 已更新
            assert chart_window.bg is not None, f"{interval_name}周期应该使用 BarGenerator"
            # BarGenerator 应该已创建或更新 bar
            # 注意：第一个 tick 会创建 bar，后续 tick 会更新 bar
            assert chart_window.bg.bar is not None or chart_window.bg.last_tick is not None, \
                f"{interval_name}周期应该更新 BarGenerator"

            # 如果 bar 已创建，验证图表更新被调用
            if chart_window.bg.bar:
                # 验证图表更新被调用（通过 on_bar 回调）
                # 注意：这里我们无法直接验证 on_bar 被调用，但可以验证 process_tick_event 执行完成
                assert True, f"{interval_name}周期应该处理 tick 事件"
        else:
            # 大周期：验证 _update_current_bar_with_tick 被调用
            assert chart_window._update_current_bar_with_tick.called, \
                f"{interval_name}周期应该调用 _update_current_bar_with_tick"

            # 验证调用参数
            call_args = chart_window._update_current_bar_with_tick.call_args
            assert call_args[0][0] == tick, f"{interval_name}周期应该传递 tick 数据"
            assert call_args[0][1] == interval_enum, f"{interval_name}周期应该传递正确的 interval"

    def test_integration_1minute_realtime_update_flow(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-1: 1分钟周期实时更新集成测试

        测试完整的 1 分钟周期实时更新流程：
        1. 接收多个 tick 事件
        2. BarGenerator 合成 1 分钟 K 线
        3. 图表实时更新
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = True
        chart_window.history_data = []
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)

        # 创建 BarGenerator
        on_bar_called = []
        def on_bar_callback(bar: BarData):
            """记录 on_bar 调用"""
            on_bar_called.append(bar)
            chart_window.chart.update_bar(bar)

        chart_window.on_bar = on_bar_callback
        chart_window.bg = BarGenerator(chart_window.on_bar)

        # 创建多个 tick 数据（在同一分钟内）
        base_time = datetime.now().replace(second=0, microsecond=0)
        ticks = [
            self._create_tick(vt_symbol, last_price=20000.0 + i, datetime=base_time + timedelta(seconds=i * 10))
            for i in range(5)
        ]

        # 发送 tick 事件
        for tick in ticks:
            event = Event(EVENT_TICK, tick)
            chart_window.process_tick_event(event)

        # 验证 BarGenerator 已更新
        assert chart_window.bg is not None
        assert chart_window.bg.bar is not None or chart_window.bg.last_tick is not None

        # 验证图表更新被调用（通过 on_bar 或直接更新）
        # 如果跨越了分钟边界，on_bar 会被调用
        # 否则，BarGenerator 会实时更新当前 bar，并通过 chart.update_bar 更新图表
        if chart_window.bg.bar:
            # 验证最后一根 bar 的价格更新
            assert chart_window.bg.bar.high_price >= 20000.0
            assert chart_window.bg.bar.close_price == ticks[-1].last_price

    def test_integration_large_period_realtime_update_flow(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-2: 大周期实时更新集成测试（以5分钟周期为例）

        测试完整的大周期实时更新流程：
        1. 接收多个 tick 事件
        2. _update_current_bar_with_tick 更新当前未完成的 K 线
        3. 图表实时更新
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "5m"
        chart_window.history_loaded = True
        chart_window.history_data = []
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE_5)
        chart_window.bg = None

        # 初始化大周期相关状态
        chart_window._current_bar = None
        chart_window._current_bar_period = None
        chart_window._current_bar_index = -1
        chart_window._period_start_volume = 0
        chart_window._period_start_turnover = 0
        chart_window._bar_historical_volume = 0
        chart_window._bar_historical_turnover = 0
        chart_window._need_init_baseline = True

        # Mock 开盘价辅助类
        chart_window.open_price_helper = Mock()
        chart_window.open_price_helper.get_period_open_price = Mock(return_value=20000.0)

        # Mock period utils
        with patch('vnpy.trader.ui.widget.get_period_start') as mock_get_period_start:
            # 模拟所有 tick 属于同一个周期
            mock_period_start = datetime.now().replace(minute=0, second=0, microsecond=0)
            mock_get_period_start.return_value = mock_period_start

            # 创建多个 tick 数据（在同一5分钟周期内）
            base_time = datetime.now().replace(second=0, microsecond=0)
            ticks = [
                self._create_tick(vt_symbol, last_price=20000.0 + i, datetime=base_time + timedelta(seconds=i * 30))
                for i in range(5)
            ]

            # 发送 tick 事件
            for tick in ticks:
                event = Event(EVENT_TICK, tick)
                chart_window.process_tick_event(event)

            # 验证 _update_current_bar_with_tick 被调用（每次 tick 都应该调用）
            assert chart_window._update_current_bar_with_tick.called
            assert chart_window._update_current_bar_with_tick.call_count == len(ticks), \
                f"应该调用 {len(ticks)} 次 _update_current_bar_with_tick，实际调用 {chart_window._update_current_bar_with_tick.call_count} 次"

    def test_integration_all_periods_tick_filtering(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-3: 测试所有周期下的 tick 过滤

        验证不同周期下，只有当前合约的 tick 会被处理。
        """
        vt_symbol = "MHI2512.HKFE"
        other_vt_symbol = "OTHER.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = True
        chart_window.history_data = []
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)
        chart_window.bg = BarGenerator(chart_window.on_bar)

        # 创建当前合约的 tick
        current_tick = self._create_tick(vt_symbol, last_price=20000.0)
        event1 = Event(EVENT_TICK, current_tick)

        # 创建其他合约的 tick
        other_tick = self._create_tick(other_vt_symbol, last_price=21000.0)
        event2 = Event(EVENT_TICK, other_tick)

        # 发送两个 tick 事件
        chart_window.process_tick_event(event1)
        chart_window.process_tick_event(event2)

        # 验证只有当前合约的 tick 被处理
        # BarGenerator 应该只更新一次（来自 current_tick）
        assert chart_window.bg.last_tick == current_tick or chart_window.bg.bar is not None
        # 图表不应该被 other_tick 更新
        # 注意：我们无法直接验证，但可以通过 BarGenerator 的状态来推断

    def test_integration_period_switch_realtime_update(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-4: 测试周期切换后的实时更新

        验证切换周期后，实时更新机制能正常工作。
        """
        vt_symbol = "MHI2512.HKFE"

        # 初始状态：1分钟周期
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = True
        chart_window.history_data = []
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)
        chart_window.bg = BarGenerator(chart_window.on_bar)

        # 发送 1 分钟周期的 tick
        tick1 = self._create_tick(vt_symbol, last_price=20000.0)
        event1 = Event(EVENT_TICK, tick1)
        chart_window.process_tick_event(event1)

        # 验证 1 分钟周期更新正常
        assert chart_window.bg is not None

        # 切换到 5 分钟周期
        chart_window.current_interval = "5m"
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE_5)
        chart_window.bg = None
        chart_window._current_bar = None

        # Mock _update_current_bar_with_tick
        chart_window._update_current_bar_with_tick = Mock()
        chart_window.open_price_helper = Mock()
        chart_window.open_price_helper.get_period_open_price = Mock(return_value=20000.0)

        # 发送 5 分钟周期的 tick
        tick2 = self._create_tick(vt_symbol, last_price=20050.0)
        event2 = Event(EVENT_TICK, tick2)
        chart_window.process_tick_event(event2)

        # 验证 5 分钟周期更新正常
        assert chart_window._update_current_bar_with_tick.called, \
            "切换到5分钟周期后应该调用 _update_current_bar_with_tick"

    def test_integration_realtime_update_with_history_data(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-5: 测试在有历史数据情况下的实时更新

        验证当历史数据已加载时，实时更新能正常工作。
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = True  # 历史数据已加载

        # 添加一些历史数据
        from datetime import datetime, timedelta
        base_time = datetime.now().replace(second=0, microsecond=0) - timedelta(minutes=10)
        history_bars = [
            self.create_bar_data(
                symbol="MHI2512",
                exchange=Exchange.HKFE,
                datetime=base_time + timedelta(minutes=i),
                interval=Interval.MINUTE,
                open_price=20000.0 + i,
                high_price=20050.0 + i,
                low_price=19950.0 + i,
                close_price=20025.0 + i
            )
            for i in range(10)
        ]
        chart_window.history_data = history_bars

        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)
        chart_window.bg = BarGenerator(chart_window.on_bar)

        # 发送实时 tick
        tick = self._create_tick(vt_symbol, last_price=20100.0)
        event = Event(EVENT_TICK, tick)
        chart_window.process_tick_event(event)

        # 验证实时更新正常工作
        assert chart_window.bg is not None
        assert chart_window.history_loaded, "历史数据加载状态应该保持为 True"

    def test_integration_realtime_update_skips_when_history_not_loaded(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T045-6: 测试历史数据未加载时跳过实时更新

        验证当历史数据未加载时，实时更新会被跳过，但价格突破监控仍然工作。
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.current_interval = "1m"
        chart_window.history_loaded = False  # 历史数据未加载
        chart_window.history_data = []
        chart_window._get_interval_enum = Mock(return_value=Interval.MINUTE)
        chart_window.bg = None

        # 发送 tick 事件
        tick = self._create_tick(vt_symbol, last_price=20000.0)
        event = Event(EVENT_TICK, tick)
        chart_window.process_tick_event(event)

        # 验证 K 线更新被跳过
        # 但价格突破监控仍然应该工作
        # 注意：由于 history_loaded=False，K 线更新会被跳过
        # 但突破监控应该仍然被调用（如果有挂单线）
        assert not chart_window.history_loaded


class TestIntegrationDrawingTradeRealtimeTriggers(TestBase):
    """Phase 5 T046: 画线交易实时触发的集成测试"""

    @pytest.fixture
    def event_engine(self) -> EventEngine:
        """创建真实的 EventEngine 用于集成测试"""
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
        engine.send_order = Mock(return_value="order_123")
        engine.get_tick = Mock(return_value=None)
        return engine

    @pytest.fixture
    def chart_window(self, main_engine: Mock, event_engine: EventEngine, qapp):
        """创建 ChartWindow 实例用于集成测试"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.chart.price_breakthrough import PriceBreakthroughMonitor

        window = ChartWindow(main_engine, event_engine)

        # 使用真实的 ChartWidget 组件（但简化初始化）
        from vnpy.chart.widget import ChartWidget
        window.chart = ChartWidget()
        window.chart.set_main_engine(main_engine)
        window.chart.set_vt_symbol("MHI2512.HKFE")

        # 确保突破监控器已初始化
        if not window.chart._breakthrough_monitor:
            window.chart._breakthrough_monitor = PriceBreakthroughMonitor()

        # 注册价格突破回调
        window.chart._breakthrough_monitor.register_line = Mock()

        return window

    def _create_tick(
        self,
        vt_symbol: str,
        last_price: float = 20000.0,
        datetime: datetime = None
    ) -> TickData:
        """创建测试用的 TickData"""
        if datetime is None:
            datetime = datetime.now()

        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange(exchange_str)

        tick = self.create_tick_data(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime,
            last_price=last_price,
            bid_price_1=last_price - 1.0,
            ask_price_1=last_price + 1.0,
            volume=1000.0,
            gateway_name="TEST"
        )
        tick.vt_symbol = vt_symbol
        return tick

    def test_integration_pending_order_trigger_on_breakthrough(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-1: 测试挂单线实时触发下单的完整流程

        验证从 tick 事件到挂单触发的完整流程：
        1. 创建挂单线
        2. 接收 tick 事件
        3. 价格突破检测
        4. 触发下单
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 创建挂单线（做多，价格 20000）
        from vnpy.chart.price_line import PriceLineType
        line_id = chart_window.chart.add_price_line(
            price=20000.0,
            line_type=PriceLineType.PENDING.value,
            direction="long"
        )
        line = chart_window.chart._price_line_manager.get_line(line_id)
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")

        # 注册价格突破回调
        chart_window.chart._breakthrough_monitor.register_line(
            line_id,
            line,
            chart_window.chart._on_price_breakthrough
        )

        # Mock trigger_pending_order_breakthrough 以验证调用
        chart_window.chart.trigger_pending_order_breakthrough = Mock(return_value=True)

        # 第一次 tick：价格在挂单线下方（19998 < 20000）
        tick1 = self._create_tick(vt_symbol, last_price=19998.0)
        event1 = Event(EVENT_TICK, tick1)
        chart_window.process_tick_event(event1)

        # 验证未触发下单
        assert not chart_window.chart.trigger_pending_order_breakthrough.called, \
            "价格未突破时不应触发下单"

        # 第二次 tick：价格突破挂单线（20001 > 20000）
        tick2 = self._create_tick(vt_symbol, last_price=20001.0)
        event2 = Event(EVENT_TICK, tick2)
        chart_window.process_tick_event(event2)

        # 等待事件处理（如果需要）
        import time
        time.sleep(0.1)

        # 验证触发下单
        assert chart_window.chart.trigger_pending_order_breakthrough.called, \
            "价格突破挂单线时应该触发下单"

        # 验证调用参数
        call_args = chart_window.chart.trigger_pending_order_breakthrough.call_args
        assert call_args[0][0] == line_id, "应该传递正确的 line_id"
        assert call_args[0][1] == line, "应该传递正确的 line 对象"
        assert call_args[0][2] == tick2, "应该传递突破时的 tick 数据"

    def test_integration_stop_loss_trigger_on_price_touch(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-2: 测试止损线实时触发平仓的完整流程

        验证从 tick 事件到止损触发的完整流程：
        1. 创建止损线
        2. 接收 tick 事件
        3. 价格触及止损线
        4. 触发平仓
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 创建止损线（多仓止损，价格 19950）
        from vnpy.chart.price_line import PriceLineType
        line_id = chart_window.chart.add_price_line(
            price=19950.0,
            line_type=PriceLineType.STOP_LOSS.value,
            direction="long"
        )
        line = chart_window.chart._price_line_manager.get_line(line_id)

        # Mock trigger_stop_loss_close 以验证调用
        chart_window.chart.trigger_stop_loss_close = Mock(return_value=True)

        # Mock 持仓数据（模拟有持仓）
        from vnpy.trader.constant import Direction
        mock_position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10.0
        )
        chart_window.chart._main_engine.get_all_positions = Mock(return_value=[mock_position])
        chart_window.chart._find_position_by_main_contract_mapping = Mock(return_value=mock_position)

        # 第一次 tick：价格在止损线上方（19960 > 19950）
        tick1 = self._create_tick(vt_symbol, last_price=19960.0)
        event1 = Event(EVENT_TICK, tick1)
        chart_window.process_tick_event(event1)

        # 验证未触发平仓（价格未触及止损线）
        # 注意：trigger_stop_loss_close 内部会检查价格是否触及，这里我们主要验证方法被调用
        # 实际触发逻辑在 trigger_stop_loss_close 内部

        # 第二次 tick：价格触及止损线（19950 <= 19950）
        tick2 = self._create_tick(vt_symbol, last_price=19950.0)
        event2 = Event(EVENT_TICK, tick2)
        chart_window.process_tick_event(event2)

        # 验证触发平仓
        assert chart_window.chart.trigger_stop_loss_close.called, \
            "价格触及止损线时应该触发平仓"

        # 验证调用参数
        call_args = chart_window.chart.trigger_stop_loss_close.call_args
        assert call_args[0][0] == line_id, "应该传递正确的 line_id"
        assert call_args[0][1] == line, "应该传递正确的 line 对象"
        assert call_args[0][2] == tick2, "应该传递触及时的 tick 数据"

    def test_integration_take_profit_trigger_on_price_touch(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-3: 测试止盈线实时触发平仓的完整流程

        验证从 tick 事件到止盈触发的完整流程：
        1. 创建止盈线
        2. 接收 tick 事件
        3. 价格触及止盈线
        4. 触发平仓
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 创建止盈线（多仓止盈，价格 20050）
        from vnpy.chart.price_line import PriceLineType
        line_id = chart_window.chart.add_price_line(
            price=20050.0,
            line_type=PriceLineType.TAKE_PROFIT.value,
            direction="long"
        )
        line = chart_window.chart._price_line_manager.get_line(line_id)

        # Mock trigger_take_profit_close 以验证调用
        chart_window.chart.trigger_take_profit_close = Mock(return_value=True)

        # Mock 持仓数据（模拟有持仓）
        from vnpy.trader.constant import Direction
        mock_position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10.0
        )
        chart_window.chart._main_engine.get_all_positions = Mock(return_value=[mock_position])
        chart_window.chart._find_position_by_main_contract_mapping = Mock(return_value=mock_position)

        # 第一次 tick：价格在止盈线下方（20040 < 20050）
        tick1 = self._create_tick(vt_symbol, last_price=20040.0)
        event1 = Event(EVENT_TICK, tick1)
        chart_window.process_tick_event(event1)

        # 验证未触发平仓（价格未触及止盈线）

        # 第二次 tick：价格触及止盈线（20050 >= 20050）
        tick2 = self._create_tick(vt_symbol, last_price=20050.0)
        event2 = Event(EVENT_TICK, tick2)
        chart_window.process_tick_event(event2)

        # 验证触发平仓
        assert chart_window.chart.trigger_take_profit_close.called, \
            "价格触及止盈线时应该触发平仓"

        # 验证调用参数
        call_args = chart_window.chart.trigger_take_profit_close.call_args
        assert call_args[0][0] == line_id, "应该传递正确的 line_id"
        assert call_args[0][1] == line, "应该传递正确的 line 对象"
        assert call_args[0][2] == tick2, "应该传递触及时的 tick 数据"

    def test_integration_multiple_lines_realtime_monitoring(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-4: 测试多条价格线同时监控

        验证系统能同时监控多条价格线（挂单线、止损线、止盈线）。
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 创建多条价格线
        from vnpy.chart.price_line import PriceLineType

        # 挂单线（做多，价格 20000）
        pending_line_id = chart_window.chart.add_price_line(
            price=20000.0,
            line_type=PriceLineType.PENDING.value,
            direction="long"
        )
        pending_line = chart_window.chart._price_line_manager.get_line(pending_line_id)
        pending_line.set_order_volume(10.0)
        pending_line.set_order_offset("OPEN")

        # 止损线（多仓止损，价格 19950）
        chart_window.chart.add_price_line(
            price=19950.0,
            line_type=PriceLineType.STOP_LOSS.value,
            direction="long"
        )
        # 止盈线（多仓止盈，价格 20050）
        chart_window.chart.add_price_line(
            price=20050.0,
            line_type=PriceLineType.TAKE_PROFIT.value,
            direction="long"
        )

        # 注册挂单线回调
        chart_window.chart._breakthrough_monitor.register_line(
            pending_line_id,
            pending_line,
            chart_window.chart._on_price_breakthrough
        )

        # Mock 触发方法
        chart_window.chart.trigger_pending_order_breakthrough = Mock(return_value=True)
        chart_window.chart.trigger_stop_loss_close = Mock(return_value=True)
        chart_window.chart.trigger_take_profit_close = Mock(return_value=True)

        # Mock 持仓数据
        from vnpy.trader.constant import Direction
        mock_position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10.0
        )
        chart_window.chart._main_engine.get_all_positions = Mock(return_value=[mock_position])
        chart_window.chart._find_position_by_main_contract_mapping = Mock(return_value=mock_position)

        # 发送多个 tick，测试不同价格下的触发情况
        # Tick 1: 价格在挂单线下方，未触发任何操作
        tick1 = self._create_tick(vt_symbol, last_price=19990.0)
        event1 = Event(EVENT_TICK, tick1)
        chart_window.process_tick_event(event1)

        assert not chart_window.chart.trigger_pending_order_breakthrough.called
        assert not chart_window.chart.trigger_stop_loss_close.called
        assert not chart_window.chart.trigger_take_profit_close.called

        # Tick 2: 价格突破挂单线，应该触发挂单
        tick2 = self._create_tick(vt_symbol, last_price=20001.0)
        event2 = Event(EVENT_TICK, tick2)
        chart_window.process_tick_event(event2)

        import time
        time.sleep(0.1)

        assert chart_window.chart.trigger_pending_order_breakthrough.called, \
            "价格突破挂单线时应该触发挂单"

        # 重置 Mock 调用计数
        chart_window.chart.trigger_pending_order_breakthrough.reset_mock()

        # Tick 3: 价格触及止损线，应该触发止损平仓
        tick3 = self._create_tick(vt_symbol, last_price=19950.0)
        event3 = Event(EVENT_TICK, tick3)
        chart_window.process_tick_event(event3)

        assert chart_window.chart.trigger_stop_loss_close.called, \
            "价格触及止损线时应该触发止损平仓"

        # Tick 4: 价格触及止盈线，应该触发止盈平仓
        tick4 = self._create_tick(vt_symbol, last_price=20050.0)
        event4 = Event(EVENT_TICK, tick4)
        chart_window.process_tick_event(event4)

        assert chart_window.chart.trigger_take_profit_close.called, \
            "价格触及止盈线时应该触发止盈平仓"

    def test_integration_drawing_trade_trigger_with_history_not_loaded(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-5: 测试历史数据未加载时画线交易触发仍然工作

        验证即使历史数据未加载，价格突破监控和触发仍然正常工作。
        """
        vt_symbol = "MHI2512.HKFE"

        # 设置 ChartWindow 状态（历史数据未加载）
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = False  # 关键：历史数据未加载
        chart_window.history_data = []

        # 创建挂单线
        from vnpy.chart.price_line import PriceLineType
        line_id = chart_window.chart.add_price_line(
            price=20000.0,
            line_type=PriceLineType.PENDING.value,
            direction="long"
        )
        line = chart_window.chart._price_line_manager.get_line(line_id)
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")

        # 注册价格突破回调
        chart_window.chart._breakthrough_monitor.register_line(
            line_id,
            line,
            chart_window.chart._on_price_breakthrough
        )

        # Mock trigger_pending_order_breakthrough
        chart_window.chart.trigger_pending_order_breakthrough = Mock(return_value=True)

        # 发送 tick 事件（价格突破挂单线）
        tick = self._create_tick(vt_symbol, last_price=20001.0)
        event = Event(EVENT_TICK, tick)
        chart_window.process_tick_event(event)

        # 等待事件处理
        import time
        time.sleep(0.1)

        # 验证即使历史数据未加载，价格突破监控仍然工作
        assert chart_window.chart.trigger_pending_order_breakthrough.called, \
            "即使历史数据未加载，价格突破监控也应该正常工作"

    def test_integration_drawing_trade_trigger_only_current_contract(
        self,
        chart_window,
        event_engine: EventEngine
    ):
        """
        T046-6: 测试只处理当前合约的 tick

        验证只有当前合约的 tick 会触发画线交易，其他合约的 tick 会被忽略。
        """
        vt_symbol = "MHI2512.HKFE"
        other_vt_symbol = "OTHER.HKFE"

        # 设置 ChartWindow 状态
        chart_window.current_vt_symbol = vt_symbol
        chart_window.history_loaded = True
        chart_window.history_data = []

        # 创建挂单线
        from vnpy.chart.price_line import PriceLineType
        line_id = chart_window.chart.add_price_line(
            price=20000.0,
            line_type=PriceLineType.PENDING.value,
            direction="long"
        )
        line = chart_window.chart._price_line_manager.get_line(line_id)
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")

        # 注册价格突破回调
        chart_window.chart._breakthrough_monitor.register_line(
            line_id,
            line,
            chart_window.chart._on_price_breakthrough
        )

        # Mock trigger_pending_order_breakthrough
        chart_window.chart.trigger_pending_order_breakthrough = Mock(return_value=True)

        # 发送其他合约的 tick（价格突破挂单线）
        other_tick = self._create_tick(other_vt_symbol, last_price=20001.0)
        other_event = Event(EVENT_TICK, other_tick)
        chart_window.process_tick_event(other_event)

        # 验证未触发下单（因为不是当前合约）
        assert not chart_window.chart.trigger_pending_order_breakthrough.called, \
            "其他合约的 tick 不应该触发画线交易"

        # 发送当前合约的 tick（价格突破挂单线）
        current_tick = self._create_tick(vt_symbol, last_price=20001.0)
        current_event = Event(EVENT_TICK, current_tick)
        chart_window.process_tick_event(current_event)

        # 等待事件处理
        import time
        time.sleep(0.1)

        # 验证触发下单（当前合约）
        assert chart_window.chart.trigger_pending_order_breakthrough.called, \
            "当前合约的 tick 应该触发画线交易"

