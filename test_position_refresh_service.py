#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
针对方案D的TDD：测试刷新定序器基础流程
"""

import sys
import os
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest import TestCase
from unittest.mock import Mock

from vnpy.event import Event, EVENT_TIMER
from vnpy.trader.constant import Direction, Exchange, Product, Offset
from vnpy.trader.engine import OmsEngine
from vnpy.trader.event import EVENT_POSITION, EVENT_POSITION_VIEW, EVENT_TICK
from vnpy.trader.object import PositionData, TickData, ContractData, TradeData
from vnpy.trader.setting import SETTINGS


class DummyEventEngine:
    """
    精简版事件引擎，用于捕获注册的handler并同步触发
    """

    def __init__(self):
        self.handlers: dict[str, list] = {}
        self.put = Mock()

    def register(self, type: str, handler) -> None:
        self.handlers.setdefault(type, []).append(handler)


class TestPositionRefreshService(TestCase):
    def setUp(self) -> None:
        self.prev_view_enabled = SETTINGS.get("position.view.enabled")
        self.prev_emit_legacy = SETTINGS.get("position.view.emit_legacy")
        SETTINGS["position.view.enabled"] = True
        SETTINGS["position.view.emit_legacy"] = False

        self.main_engine = Mock()
        self.event_engine = DummyEventEngine()
        self.oms = OmsEngine(self.main_engine, self.event_engine)

        # 注册合约信息，确保乘数获取成功
        contract = ContractData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            name="Mini Hang Seng",
            product=Product.FUTURES,
            size=50,
            pricetick=1,
            gateway_name="FUTU",
        )
        self.oms.contracts[contract.vt_symbol] = contract

    def tearDown(self) -> None:
        if self.prev_view_enabled is None:
            SETTINGS.pop("position.view.enabled", None)
        else:
            SETTINGS["position.view.enabled"] = self.prev_view_enabled

        if self.prev_emit_legacy is None:
            SETTINGS.pop("position.view.emit_legacy", None)
        else:
            SETTINGS["position.view.emit_legacy"] = self.prev_emit_legacy

    def _raise_timer(self):
        handlers = self.event_engine.handlers.get(EVENT_TIMER, [])
        for handler in handlers:
            handler(Event(EVENT_TIMER))

    def test_position_refresh_pipeline(self):
        """
        TDD-1：Tick只入队，定序器执行后才推送持仓事件
        """
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1,
            price=20000,
            pnl=0,
            gateway_name="FUTU",
        )
        self.oms.process_position_event(Event(EVENT_POSITION, position))
        self.event_engine.put.assert_called_once()
        initial_event = self.event_engine.put.call_args[0][0]
        self.assertEqual(initial_event.type, EVENT_POSITION_VIEW)
        self.event_engine.put.reset_mock()

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20090,
            ask_price_1=20095,
            bid_price_1=20085,
        )

        self.oms.process_tick_event(Event(EVENT_TICK, tick))
        self.event_engine.put.assert_not_called()

        self._raise_timer()

        self.event_engine.put.assert_called_once()
        pushed_event = self.event_engine.put.call_args[0][0]
        self.assertEqual(pushed_event.type, EVENT_POSITION_VIEW)
        refreshed_position = pushed_event.data
        expected_pnl = (tick.ask_price_1 - position.price) * position.volume * 50
        self.assertAlmostEqual(refreshed_position.pnl, expected_pnl, places=2)

    def test_trade_merge_updates_volume_price(self):
        """
        TDD-2：成交后可推导最新仓位并触发刷新
        """
        trade = TradeData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            orderid="1",
            tradeid="1",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=20010,
            volume=2,
            gateway_name="FUTU",
        )
        trade_event = Event("eTrade.", trade)
        self.oms.process_trade_event(trade_event)
        self.event_engine.put.assert_called_once()
        first_event = self.event_engine.put.call_args[0][0]
        self.assertEqual(first_event.type, EVENT_POSITION_VIEW)
        self.event_engine.put.reset_mock()

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20050,
            ask_price_1=20055,
            bid_price_1=20045,
        )
        self.oms.process_tick_event(Event(EVENT_TICK, tick))
        self._raise_timer()

        pushed_event = self.event_engine.put.call_args[0][0]
        refreshed_position = pushed_event.data
        self.assertEqual(refreshed_position.volume, 2)
        expected_pnl = (tick.ask_price_1 - 20010) * 2 * 50
        self.assertAlmostEqual(refreshed_position.pnl, expected_pnl, places=2)

    def test_tick_throttling_merges_requests(self):
        """
        TDD-3：同symbol多次tick只触发一次刷新
        """
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1,
            price=20000,
            pnl=0,
            gateway_name="FUTU",
        )
        self.oms.process_position_event(Event(EVENT_POSITION, position))
        self.event_engine.put.reset_mock()

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20080,
            ask_price_1=20085,
            bid_price_1=20075,
        )

        self.oms.process_tick_event(Event(EVENT_TICK, tick))
        self.oms.process_tick_event(Event(EVENT_TICK, tick))
        self._raise_timer()

        self.assertEqual(self.event_engine.put.call_count, 1)

    def test_zero_volume_position_no_event(self):
        """
        TDD-4：零持仓不推送事件
        """
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=0,
            price=20000,
            pnl=0,
            gateway_name="FUTU",
        )
        self.oms.process_position_event(Event(EVENT_POSITION, position))
        self.event_engine.put.assert_called_once()
        zero_event = self.event_engine.put.call_args[0][0]
        self.assertEqual(zero_event.data.volume, 0)
        self.event_engine.put.reset_mock()

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20100,
            ask_price_1=20105,
            bid_price_1=20095,
        )
        self.oms.process_tick_event(Event(EVENT_TICK, tick))
        self._raise_timer()

        self.event_engine.put.assert_not_called()

    def test_view_disabled_no_refresh(self):
        SETTINGS["position.view.enabled"] = False
        local_event_engine = DummyEventEngine()
        local_main_engine = Mock()
        disabled_oms = OmsEngine(local_main_engine, local_event_engine)

        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1,
            price=20000,
            pnl=0,
            gateway_name="FUTU",
        )
        disabled_oms.process_position_event(Event(EVENT_POSITION, position))

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20100,
            ask_price_1=20105,
            bid_price_1=20095,
        )
        disabled_oms.process_tick_event(Event(EVENT_TICK, tick))
        handlers = local_event_engine.handlers.get(EVENT_TIMER, [])
        for handler in handlers:
            handler(Event(EVENT_TIMER))

        local_event_engine.put.assert_not_called()

    def test_emit_legacy_true_pushes_both(self):
        SETTINGS["position.view.enabled"] = True
        SETTINGS["position.view.emit_legacy"] = True
        local_event_engine = DummyEventEngine()
        local_main_engine = Mock()
        dual_oms = OmsEngine(local_main_engine, local_event_engine)

        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1,
            price=20000,
            pnl=0,
            gateway_name="FUTU",
        )
        dual_oms.process_position_event(Event(EVENT_POSITION, position))

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=datetime.utcnow(),
            gateway_name="FUTU",
            last_price=20100,
            ask_price_1=20105,
            bid_price_1=20095,
        )
        dual_oms.process_tick_event(Event(EVENT_TICK, tick))
        handlers = local_event_engine.handlers.get(EVENT_TIMER, [])
        for handler in handlers:
            handler(Event(EVENT_TIMER))

        self.assertGreaterEqual(local_event_engine.put.call_count, 2)
        event_types = [call.args[0].type for call in local_event_engine.put.call_args_list]
        self.assertIn(EVENT_POSITION_VIEW, event_types)
        self.assertIn(EVENT_POSITION, event_types)

