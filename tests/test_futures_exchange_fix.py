#!/usr/bin/env python3
"""
测试期货合约交易所转换修复
验证Futu API返回的"HK.MHImain"格式能正确识别为HKFE
"""

import sys
sys.path.insert(0, 'D:/Dev/vnpy/vnpy_futu')

from vnpy_futu.futu_gateway import convert_symbol_futu2vt
from vnpy.trader.constant import Exchange

def test_futures_exchange_conversion():
    """测试期货交易所转换"""
    print("=" * 70)
    print("测试期货合约交易所转换修复")
    print("=" * 70)

    test_cases = [
        # (Futu代码, 期望symbol, 期望Exchange, 描述)
        ("HK.MHImain", "MHImain", Exchange.HKFE, "小恒指主力合约"),
        ("HK.MHI2412", "MHI2412", Exchange.HKFE, "小恒指2024年12月"),
        ("HK.HSImain", "HSImain", Exchange.HKFE, "大恒指主力合约"),
        ("HK.MCHmain", "MCHmain", Exchange.HKFE, "小国指主力合约"),
        ("HK.HHImain", "HHImain", Exchange.HKFE, "大国指主力合约"),
        ("HK.CUSmain", "CUSmain", Exchange.HKFE, "A50指数期货"),
        ("HK_FUTURE.MHImain", "MHImain", Exchange.HKFE, "标准期货格式"),
        ("HK.00700", "00700", Exchange.SEHK, "腾讯股票（应保持SEHK）"),
        ("HK.09988", "09988", Exchange.SEHK, "阿里股票（应保持SEHK）"),
        ("US.AAPL", "AAPL", Exchange.SMART, "美股（应保持SMART）"),
    ]

    all_passed = True

    for futu_code, expected_symbol, expected_exchange, description in test_cases:
        print(f"\n测试: {description}")
        print(f"  输入: {futu_code}")

        try:
            symbol, exchange = convert_symbol_futu2vt(futu_code)

            print(f"  输出: symbol={symbol}, exchange={exchange.value}")
            print(f"  期望: symbol={expected_symbol}, exchange={expected_exchange.value}")

            # 验证结果
            symbol_match = symbol == expected_symbol
            exchange_match = exchange == expected_exchange

            if symbol_match and exchange_match:
                print(f"  结果: 通过")
            else:
                print(f"  结果: 失败")
                if not symbol_match:
                    print(f"    - Symbol不匹配: {symbol} != {expected_symbol}")
                if not exchange_match:
                    print(f"    - Exchange不匹配: {exchange.value} != {expected_exchange.value}")
                all_passed = False

        except Exception as e:
            print(f"  结果: 异常 - {e}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("所有测试通过！")
        print("\n修复总结:")
        print("1. Futu API返回'HK.MHImain'格式时，正确识别为Exchange.HKFE")
        print("2. 根据合约代码特征(MHI/HSI/MCH/HHI/CUS)判断期货合约")
        print("3. 股票和其他合约保持原有映射不变")
    else:
        print("部分测试失败！")
    print("=" * 70)

    return all_passed

if __name__ == "__main__":
    success = test_futures_exchange_conversion()
    sys.exit(0 if success else 1)
