#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Market Price和OPPONENT Price实现
"""

from vnpy.trader.constant import Direction, Exchange, OrderType as VtOrderType
from vnpy.trader.object import OrderRequest

# 模拟OPPONENT_PRICE_MARKER
OPPONENT_PRICE_MARKER = -999999.0

def test_order_logic():
    """测试订单逻辑"""

    # 测试1：普通限价单
    req1 = OrderRequest(
        symbol="00700",
        exchange=Exchange.SEHK,
        direction=Direction.LONG,
        type=VtOrderType.LIMIT,
        volume=100,
        price=400.0,
        reference="TestLimit"
    )
    print(f"限价单测试: {req1.symbol} {req1.direction.value} {req1.type.value} 价格={req1.price}")

    # 测试2：市价单
    req2 = OrderRequest(
        symbol="00700",
        exchange=Exchange.SEHK,
        direction=Direction.LONG,
        type=VtOrderType.MARKET,
        volume=100,
        price=0,
        reference="TestMarket"
    )
    print(f"市价单测试: {req2.symbol} {req2.direction.value} {req2.type.value} 价格={req2.price}")

    # 测试3：OPPONENT价格单
    req3 = OrderRequest(
        symbol="00700",
        exchange=Exchange.SEHK,
        direction=Direction.LONG,
        type=VtOrderType.LIMIT,  # OPPONENT使用限价类型
        volume=100,
        price=OPPONENT_PRICE_MARKER,  # 特殊标记价格
        reference="TestOPPONENT"
    )
    print(f"OPPONENT价格单测试: {req3.symbol} {req3.direction.value} {req3.type.value} 价格={req3.price}")

    # 测试价格逻辑
    def simulate_price_logic(req, tick_ask=401.0, tick_bid=399.0, tick_last=400.0):
        """模拟价格处理逻辑"""
        order_price = req.price

        if req.price == OPPONENT_PRICE_MARKER:
            # OPPONENT价格订单：更激进的对手价策略
            if req.direction == Direction.LONG:
                # 买单使用卖一价（ask price），更激进一些
                base_price = tick_ask if tick_ask > 0 else tick_last
                order_price = base_price * 1.001  # 增加0.1%
            else:
                # 卖单使用买一价（bid price），更激进一些
                base_price = tick_bid if tick_bid > 0 else tick_last
                order_price = base_price * 0.999  # 减少0.1%
            print(f"  -> OPPONENT价格处理：{req.direction.value} 最终价格={order_price:.2f}")

        elif req.type == VtOrderType.MARKET:
            # 市价单处理：使用对手价
            if req.direction == Direction.LONG:
                order_price = tick_ask if tick_ask > 0 else req.price
            else:
                order_price = tick_bid if tick_bid > 0 else req.price
            print(f"  -> 市价单处理：{req.direction.value} 最终价格={order_price:.2f}")

        elif req.type == VtOrderType.LIMIT:
            # 限价单：使用用户指定价格
            order_price = req.price
            print(f"  -> 限价单处理：{req.direction.value} 最终价格={order_price:.2f}")

        return order_price

    # 模拟行情数据
    print(f"\n模拟行情：买一价={399.0}, 卖一价={401.0}, 最新价={400.0}")
    print("="*50)

    # 测试各种订单的价格处理
    for req in [req1, req2, req3]:
        final_price = simulate_price_logic(req)
        print()

if __name__ == "__main__":
    print("开始测试Market Price和OPPONENT Price实现")
    print("="*50)
    test_order_logic()
    print("="*50)
    print("测试完成！")