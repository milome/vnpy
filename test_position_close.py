#!/usr/bin/env python3
"""
测试持仓平仓逻辑
验证开仓后平仓，持仓应该正确清零
"""

from vnpy.trader.object import ContractData, TradeData
from vnpy.trader.constant import Direction, Offset, Exchange, Product
from vnpy.trader.converter import PositionHolding


def create_test_contract(symbol: str = "AAPL", exchange: Exchange = Exchange.SSE) -> ContractData:
    """创建测试合约"""
    return ContractData(
        symbol=symbol,
        exchange=exchange,
        name=symbol,
        product=Product.EQUITY,
        size=1,
        pricetick=0.01,
        min_volume=1,
        net_position=False,  # 多空仓模式
        gateway_name="TEST"
    )


def create_trade(
    symbol: str,
    exchange: Exchange,
    direction: Direction,
    offset: Offset,
    volume: float,
    price: float = 100.0,
    orderid: str = "1",
    tradeid: str = "1"
) -> TradeData:
    """创建测试成交"""
    return TradeData(
        symbol=symbol,
        exchange=exchange,
        direction=direction,
        offset=offset,
        volume=volume,
        price=price,
        orderid=orderid,
        tradeid=tradeid,
        datetime=None,
        gateway_name="TEST"
    )


def test_open_long_then_close():
    """测试：开多仓后平仓，持仓应该清零"""
    print("=" * 60)
    print("测试用例1: 开多仓1手，然后平仓1手")
    print("=" * 60)
    
    contract = create_test_contract("AAPL", Exchange.SSE)
    holding = PositionHolding(contract)
    
    # 1. 开多仓1手
    trade1 = create_trade("AAPL", Exchange.SSE, Direction.LONG, Offset.OPEN, 1.0, 100.0, "1", "1")
    holding.update_trade(trade1)
    
    print(f"开多仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.long_pos == 1.0, f"多仓应该为1，实际为{holding.long_pos}"
    assert holding.long_td == 1.0, f"多今仓应该为1，实际为{holding.long_td}"
    assert holding.short_pos == 0.0, f"空仓应该为0，实际为{holding.short_pos}"
    
    # 2. 平多仓1手（空单平仓）
    trade2 = create_trade("AAPL", Exchange.SSE, Direction.SHORT, Offset.CLOSE, 1.0, 101.0, "2", "2")
    holding.update_trade(trade2)
    
    print(f"\n平多仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.long_pos == 0.0, f"多仓应该为0，实际为{holding.long_pos}"
    assert holding.long_td == 0.0, f"多今仓应该为0，实际为{holding.long_td}"
    assert holding.long_yd == 0.0, f"多昨仓应该为0，实际为{holding.long_yd}"
    assert holding.short_pos == 0.0, f"空仓应该为0，实际为{holding.short_pos}"
    
    print("[PASS] 测试通过: 开多仓后平仓，持仓正确清零")


def test_open_short_then_close():
    """测试：开空仓后平仓，持仓应该清零"""
    print("\n" + "=" * 60)
    print("测试用例2: 开空仓1手，然后平仓1手")
    print("=" * 60)
    
    contract = create_test_contract("AAPL", Exchange.SSE)
    holding = PositionHolding(contract)
    
    # 1. 开空仓1手
    trade1 = create_trade("AAPL", Exchange.SSE, Direction.SHORT, Offset.OPEN, 1.0, 100.0, "1", "1")
    holding.update_trade(trade1)
    
    print(f"开空仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.short_pos == 1.0, f"空仓应该为1，实际为{holding.short_pos}"
    assert holding.short_td == 1.0, f"空今仓应该为1，实际为{holding.short_td}"
    assert holding.long_pos == 0.0, f"多仓应该为0，实际为{holding.long_pos}"
    
    # 2. 平空仓1手（多单平仓）
    trade2 = create_trade("AAPL", Exchange.SSE, Direction.LONG, Offset.CLOSE, 1.0, 99.0, "2", "2")
    holding.update_trade(trade2)
    
    print(f"\n平空仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.short_pos == 0.0, f"空仓应该为0，实际为{holding.short_pos}"
    assert holding.short_td == 0.0, f"空今仓应该为0，实际为{holding.short_td}"
    assert holding.short_yd == 0.0, f"空昨仓应该为0，实际为{holding.short_yd}"
    assert holding.long_pos == 0.0, f"多仓应该为0，实际为{holding.long_pos}"
    
    print("[PASS] 测试通过: 开空仓后平仓，持仓正确清零")


def test_open_long_then_close_with_reverse():
    """测试：开多仓后，用空单开仓来平仓（反向开仓自动平仓）"""
    print("\n" + "=" * 60)
    print("测试用例3: 开多仓1手，然后用空单开仓1手（应该自动平仓）")
    print("=" * 60)
    
    contract = create_test_contract("AAPL", Exchange.SSE)
    holding = PositionHolding(contract)
    
    # 1. 开多仓1手
    trade1 = create_trade("AAPL", Exchange.SSE, Direction.LONG, Offset.OPEN, 1.0, 100.0, "1", "1")
    holding.update_trade(trade1)
    
    print(f"开多仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.long_pos == 1.0, f"多仓应该为1，实际为{holding.long_pos}"
    
    # 2. 用空单开仓1手（应该自动平掉多仓）
    trade2 = create_trade("AAPL", Exchange.SSE, Direction.SHORT, Offset.OPEN, 1.0, 101.0, "2", "2")
    holding.update_trade(trade2)
    
    print(f"\n用空单开仓1手后（应该自动平掉多仓）:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    print(f"  空仓: {holding.short_pos} (今={holding.short_td}, 昨={holding.short_yd})")
    
    assert holding.long_pos == 0.0, f"多仓应该为0，实际为{holding.long_pos}"
    assert holding.short_pos == 0.0, f"空仓应该为0，实际为{holding.short_pos}"
    
    print("[PASS] 测试通过: 反向开仓自动平仓，持仓正确清零")


def test_partial_close():
    """测试：部分平仓"""
    print("\n" + "=" * 60)
    print("测试用例4: 开多仓2手，然后平仓1手")
    print("=" * 60)
    
    contract = create_test_contract("AAPL", Exchange.SSE)
    holding = PositionHolding(contract)
    
    # 1. 开多仓2手
    trade1 = create_trade("AAPL", Exchange.SSE, Direction.LONG, Offset.OPEN, 2.0, 100.0, "1", "1")
    holding.update_trade(trade1)
    
    print(f"开多仓2手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    
    assert holding.long_pos == 2.0, f"多仓应该为2，实际为{holding.long_pos}"
    
    # 2. 平多仓1手
    trade2 = create_trade("AAPL", Exchange.SSE, Direction.SHORT, Offset.CLOSE, 1.0, 101.0, "2", "2")
    holding.update_trade(trade2)
    
    print(f"\n平多仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    
    assert holding.long_pos == 1.0, f"多仓应该为1，实际为{holding.long_pos}"
    assert holding.short_pos == 0.0, f"空仓应该为0，实际为{holding.short_pos}"
    
    print("[PASS] 测试通过: 部分平仓，持仓正确减少")


def test_close_today():
    """测试：平今仓"""
    print("\n" + "=" * 60)
    print("测试用例5: 开多仓1手，然后平今仓1手")
    print("=" * 60)
    
    contract = create_test_contract("AAPL", Exchange.SSE)
    holding = PositionHolding(contract)
    
    # 1. 开多仓1手
    trade1 = create_trade("AAPL", Exchange.SSE, Direction.LONG, Offset.OPEN, 1.0, 100.0, "1", "1")
    holding.update_trade(trade1)
    
    print(f"开多仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    
    assert holding.long_pos == 1.0, f"多仓应该为1，实际为{holding.long_pos}"
    assert holding.long_td == 1.0, f"多今仓应该为1，实际为{holding.long_td}"
    
    # 2. 平今仓1手
    trade2 = create_trade("AAPL", Exchange.SSE, Direction.SHORT, Offset.CLOSETODAY, 1.0, 101.0, "2", "2")
    holding.update_trade(trade2)
    
    print(f"\n平今仓1手后:")
    print(f"  多仓: {holding.long_pos} (今={holding.long_td}, 昨={holding.long_yd})")
    
    assert holding.long_pos == 0.0, f"多仓应该为0，实际为{holding.long_pos}"
    assert holding.long_td == 0.0, f"多今仓应该为0，实际为{holding.long_td}"
    
    print("[PASS] 测试通过: 平今仓，持仓正确清零")


def run_all_tests():
    """运行所有测试"""
    try:
        test_open_long_then_close()
        test_open_short_then_close()
        test_open_long_then_close_with_reverse()
        test_partial_close()
        test_close_today()
        
        print("\n" + "=" * 60)
        print("所有测试用例通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_all_tests()

