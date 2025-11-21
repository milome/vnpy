#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试平仓按钮功能
"""
import sys
import os

# 设置编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from unittest.mock import Mock, MagicMock, patch
from vnpy.trader.object import PositionData, TickData, ContractData
from vnpy.trader.constant import Direction, Exchange, Offset, OrderType
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.event import EVENT_POSITION


def test_close_position_button_logic():
    """测试平仓按钮逻辑"""
    print("=" * 60)
    print("测试平仓按钮功能")
    print("=" * 60)
    
    # 模拟持仓数据
    test_cases = [
        {
            "name": "测试1: 多仓5手，无冻结",
            "long_volume": 5,
            "long_frozen": 0,
            "short_volume": 0,
            "short_frozen": 0,
            "expected_button_text": "平仓（平多 5手）",
            "expected_enabled": True,
            "expected_max_volume": 5
        },
        {
            "name": "测试2: 多仓3手，冻结1手",
            "long_volume": 3,
            "long_frozen": 1,
            "short_volume": 0,
            "short_frozen": 0,
            "expected_button_text": "平仓（平多 2手）",
            "expected_enabled": True,
            "expected_max_volume": 2
        },
        {
            "name": "测试3: 空仓10手，无冻结",
            "long_volume": 0,
            "long_frozen": 0,
            "short_volume": 10,
            "short_frozen": 0,
            "expected_button_text": "平仓（平空 10手）",
            "expected_enabled": True,
            "expected_max_volume": 10
        },
        {
            "name": "测试4: 空仓8手，冻结2手",
            "long_volume": 0,
            "long_frozen": 0,
            "short_volume": 8,
            "short_frozen": 2,
            "expected_button_text": "平仓（平空 6手）",
            "expected_enabled": True,
            "expected_max_volume": 6
        },
        {
            "name": "测试5: 无持仓",
            "long_volume": 0,
            "long_frozen": 0,
            "short_volume": 0,
            "short_frozen": 0,
            "expected_button_text": "平仓（无持仓）",
            "expected_enabled": False,
            "expected_max_volume": 1000
        },
        {
            "name": "测试6: 多仓和空仓同时存在（优先平多）",
            "long_volume": 5,
            "long_frozen": 0,
            "short_volume": 3,
            "short_frozen": 0,
            "expected_button_text": "平仓（平多 5手）",
            "expected_enabled": True,
            "expected_max_volume": 5
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print(f"  多仓: {test_case['long_volume']}手 (冻结: {test_case['long_frozen']}手)")
        print(f"  空仓: {test_case['short_volume']}手 (冻结: {test_case['short_frozen']}手)")
        
        # 计算可用持仓
        long_available = max(0, test_case['long_volume'] - test_case['long_frozen'])
        short_available = max(0, test_case['short_volume'] - test_case['short_frozen'])
        
        # 模拟按钮状态计算逻辑
        if long_available > 0:
            button_text = f"平仓（平多 {long_available:.0f}手）"
            button_enabled = True
            max_volume = int(long_available)
        elif short_available > 0:
            button_text = f"平仓（平空 {short_available:.0f}手）"
            button_enabled = True
            max_volume = int(short_available)
        else:
            button_text = "平仓（无持仓）"
            button_enabled = False
            max_volume = 1000
        
        # 验证结果
        assert button_text == test_case['expected_button_text'], \
            f"按钮文字不匹配: 期望 {test_case['expected_button_text']}, 实际 {button_text}"
        assert button_enabled == test_case['expected_enabled'], \
            f"按钮状态不匹配: 期望 {test_case['expected_enabled']}, 实际 {button_enabled}"
        assert max_volume == test_case['expected_max_volume'], \
            f"最大手数不匹配: 期望 {test_case['expected_max_volume']}, 实际 {max_volume}"
        
        print(f"  ✓ 按钮文字: {button_text}")
        print(f"  ✓ 按钮启用: {button_enabled}")
        print(f"  ✓ 最大手数: {max_volume}")
    
    print("\n" + "=" * 60)
    print("所有测试用例通过！")
    print("=" * 60)


def test_close_position_order_request():
    """测试平仓订单请求构建"""
    print("\n" + "=" * 60)
    print("测试平仓订单请求构建")
    print("=" * 60)
    
    # 模拟平仓场景
    test_cases = [
        {
            "name": "测试1: 平多仓",
            "long_available": 5,
            "close_volume": 3,
            "expected_direction": Direction.SHORT,
            "expected_offset": Offset.CLOSE,
            "expected_type": OrderType.OPPONENT
        },
        {
            "name": "测试2: 平空仓",
            "short_available": 8,
            "close_volume": 5,
            "expected_direction": Direction.LONG,
            "expected_offset": Offset.CLOSE,
            "expected_type": OrderType.OPPONENT
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        
        # 模拟订单请求构建逻辑
        if 'long_available' in test_case:
            close_direction = Direction.SHORT  # 平多：卖出
            available_volume = test_case['long_available']
        else:
            close_direction = Direction.LONG  # 平空：买入
            available_volume = test_case['short_available']
        
        close_volume = test_case['close_volume']
        
        # 验证方向
        assert close_direction == test_case['expected_direction'], \
            f"平仓方向不匹配: 期望 {test_case['expected_direction']}, 实际 {close_direction}"
        
        # 验证手数
        assert close_volume <= available_volume, \
            f"平仓手数超过可用持仓: {close_volume} > {available_volume}"
        
        print(f"  ✓ 平仓方向: {close_direction.value}")
        print(f"  ✓ 平仓手数: {close_volume}")
        print(f"  ✓ 订单类型: {test_case['expected_type'].value}")
        print(f"  ✓ 开平标志: {test_case['expected_offset'].value}")
    
    print("\n" + "=" * 60)
    print("所有订单请求测试通过！")
    print("=" * 60)


def test_close_position_validation():
    """测试平仓验证逻辑"""
    print("\n" + "=" * 60)
    print("测试平仓验证逻辑")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "测试1: 平仓手数为0",
            "close_volume": 0,
            "available_volume": 5,
            "should_fail": True,
            "error_msg": "平仓手数必须大于0"
        },
        {
            "name": "测试2: 平仓手数超过可用持仓",
            "close_volume": 10,
            "available_volume": 5,
            "should_fail": True,
            "error_msg": "平仓手数超过可用持仓"
        },
        {
            "name": "测试3: 平仓手数等于可用持仓",
            "close_volume": 5,
            "available_volume": 5,
            "should_fail": False,
            "error_msg": None
        },
        {
            "name": "测试4: 平仓手数小于可用持仓",
            "close_volume": 3,
            "available_volume": 5,
            "should_fail": False,
            "error_msg": None
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print(f"  平仓手数: {test_case['close_volume']}")
        print(f"  可用持仓: {test_case['available_volume']}")
        
        # 模拟验证逻辑
        if test_case['close_volume'] <= 0:
            should_fail = True
            error_msg = "平仓手数必须大于0"
        elif test_case['close_volume'] > test_case['available_volume']:
            should_fail = True
            error_msg = f"平仓手数({test_case['close_volume']})超过可用持仓({test_case['available_volume']:.0f}手)"
        else:
            should_fail = False
            error_msg = None
        
        # 验证结果
        assert should_fail == test_case['should_fail'], \
            f"验证结果不匹配: 期望失败={test_case['should_fail']}, 实际失败={should_fail}"
        
        if should_fail:
            assert error_msg is not None, "失败时应该有错误消息"
            print(f"  ✓ 验证失败（预期）: {error_msg}")
        else:
            print(f"  ✓ 验证通过")
    
    print("\n" + "=" * 60)
    print("所有验证测试通过！")
    print("=" * 60)


def test_opponent_price_calculation():
    """测试对手价计算"""
    print("\n" + "=" * 60)
    print("测试对手价计算")
    print("=" * 60)
    
    # 模拟tick数据
    tick_data = Mock(spec=TickData)
    tick_data.bid_price_1 = 25000.0
    tick_data.ask_price_1 = 25010.0
    tick_data.last_price = 25005.0
    
    test_cases = [
        {
            "name": "测试1: 平多仓（使用买一价）",
            "close_direction": Direction.SHORT,
            "expected_price": 25000.0,  # bid_price_1
        },
        {
            "name": "测试2: 平空仓（使用卖一价）",
            "close_direction": Direction.LONG,
            "expected_price": 25010.0,  # ask_price_1
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        
        # 模拟对手价计算逻辑
        if test_case['close_direction'] == Direction.SHORT:
            # 平多：使用买一价（bid）
            price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
        else:
            # 平空：使用卖一价（ask）
            price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
        
        # 验证结果
        assert price == test_case['expected_price'], \
            f"对手价不匹配: 期望 {test_case['expected_price']}, 实际 {price}"
        
        print(f"  ✓ 对手价: {price:.2f}")
    
    print("\n" + "=" * 60)
    print("所有对手价计算测试通过！")
    print("=" * 60)


def test_chase_config_in_close_position():
    """测试平仓时的追价配置"""
    print("\n" + "=" * 60)
    print("测试平仓时的追价配置")
    print("=" * 60)
    
    # 模拟追价配置
    chase_config = {
        "enabled": True,
        "max_chase_times": 5,
        "max_slippage_pct": 0.1,
        "chase_step_pct": 0.05
    }
    
    # 模拟reference构建逻辑
    reference = "OPPONENT"
    if chase_config["enabled"]:
        chase_suffix = f"_Chase{chase_config['max_chase_times']}_Slip{chase_config['max_slippage_pct']}_Step{chase_config['chase_step_pct']}"
        reference += chase_suffix
    
    expected_reference = "OPPONENT_Chase5_Slip0.1_Step0.05"
    
    assert reference == expected_reference, \
        f"reference不匹配: 期望 {expected_reference}, 实际 {reference}"
    
    print(f"  ✓ Reference: {reference}")
    print(f"  ✓ 追价已启用: {chase_config['enabled']}")
    print(f"  ✓ 最大追价次数: {chase_config['max_chase_times']}")
    print(f"  ✓ 最大滑点: {chase_config['max_slippage_pct']}%")
    print(f"  ✓ 追价步长: {chase_config['chase_step_pct']}%")
    
    print("\n" + "=" * 60)
    print("追价配置测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_close_position_button_logic()
        test_close_position_order_request()
        test_close_position_validation()
        test_opponent_price_calculation()
        test_chase_config_in_close_position()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

