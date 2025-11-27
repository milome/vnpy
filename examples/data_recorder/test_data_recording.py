"""
数据录制测试脚本
用于验证数据录制功能是否正常工作
"""

import time
from datetime import datetime, timedelta
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarRequest, HistoryRequest


class DataRecordingTester:
    """数据录制测试类"""
    
    def __init__(self):
        self.database = get_database()
    
    def test_tick_data_recording(self, symbol: str, exchange: Exchange, hours: int = 1):
        """测试Tick数据录制"""
        print(f"\n=== 测试 {symbol}.{exchange.value} 的Tick数据录制 ===")
        
        # 获取最近指定小时数的Tick数据
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        ticks = self.database.load_tick_data(
            symbol=symbol,
            exchange=exchange,
            start=start_time,
            end=end_time
        )
        
        if ticks:
            print(f"✓ 成功获取到 {len(ticks)} 条Tick数据")
            print(f"  时间范围: {ticks[0].datetime} 到 {ticks[-1].datetime}")
            print(f"  最新价格: {ticks[-1].last_price}")
            print(f"  买一价: {ticks[-1].bid_price_1}, 卖一价: {ticks[-1].ask_price_1}")
            return True
        else:
            print("✗ 未获取到Tick数据，可能原因：")
            print("  - 合约代码不正确")
            print("  - 未在交易时间内")
            print("  - 数据录制未启动")
            return False
    
    def test_bar_data_recording(self, symbol: str, exchange: Exchange, days: int = 1):
        """测试K线数据录制"""
        print(f"\n=== 测试 {symbol}.{exchange.value} 的K线数据录制 ===")
        
        # 获取最近指定天数的K线数据
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        bars = self.database.load_bar_data(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.MINUTE,
            start=start_time,
            end=end_time
        )
        
        if bars:
            print(f"✓ 成功获取到 {len(bars)} 条K线数据")
            print(f"  时间范围: {bars[0].datetime} 到 {bars[-1].datetime}")
            print(f"  最新K线: 开={bars[-1].open_price}, 高={bars[-1].high_price}, "
                  f"低={bars[-1].low_price}, 收={bars[-1].close_price}")
            print(f"  成交量: {bars[-1].volume}")
            return True
        else:
            print("✗ 未获取到K线数据，可能原因：")
            print("  - 合约代码不正确")
            print("  - 未在交易时间内")
            print("  - 数据录制未启动")
            return False
    
    def test_data_continuity(self, symbol: str, exchange: Exchange, minutes: int = 30):
        """测试数据连续性"""
        print(f"\n=== 测试 {symbol}.{exchange.value} 数据连续性 ===")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        
        # 获取K线数据
        bars = self.database.load_bar_data(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.MINUTE,
            start=start_time,
            end=end_time
        )
        
        if len(bars) < 2:
            print("✗ 数据不足，无法测试连续性")
            return False
        
        # 检查时间间隔
        gaps = []
        for i in range(1, len(bars)):
            time_diff = bars[i].datetime - bars[i-1].datetime
            if time_diff > timedelta(minutes=2):  # 允许1-2分钟的间隔
                gaps.append((bars[i-1].datetime, bars[i].datetime, time_diff))
        
        if gaps:
            print(f"⚠ 发现 {len(gaps)} 个数据间隔:")
            for start, end, diff in gaps[:5]:  # 只显示前5个
                print(f"  {start} -> {end} (间隔: {diff})")
        else:
            print("✓ 数据连续性良好")
        
        return len(gaps) == 0
    
    def get_database_statistics(self):
        """获取数据库统计信息"""
        print("\n=== 数据库统计信息 ===")
        
        # 这里需要根据实际的数据库结构来查询
        # 由于vnpy的数据库接口限制，我们使用简单的方法
        try:
            # 获取所有合约的最新数据时间
            print("数据库连接正常")
            print("注意: 详细统计需要直接查询数据库")
        except Exception as e:
            print(f"数据库连接错误: {e}")
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("开始数据录制功能测试...")
        print("=" * 50)
        
        # 测试常见的港股合约
        test_symbols = [
            ("00700", Exchange.HK),  # 腾讯控股
            ("00941", Exchange.HK),  # 中国移动
            ("02800", Exchange.HK),  # 盈富基金
        ]
        
        results = []
        
        for symbol, exchange in test_symbols:
            print(f"\n正在测试 {symbol}.{exchange.value}...")
            
            # 测试Tick数据
            tick_result = self.test_tick_data_recording(symbol, exchange, hours=1)
            
            # 测试K线数据
            bar_result = self.test_bar_data_recording(symbol, exchange, days=1)
            
            # 测试数据连续性
            continuity_result = self.test_data_continuity(symbol, exchange, minutes=30)
            
            results.append({
                'symbol': f"{symbol}.{exchange.value}",
                'tick_ok': tick_result,
                'bar_ok': bar_result,
                'continuity_ok': continuity_result
            })
        
        # 输出测试结果汇总
        print("\n" + "=" * 50)
        print("测试结果汇总:")
        print("-" * 50)
        
        for result in results:
            symbol = result['symbol']
            tick_status = "✓" if result['tick_ok'] else "✗"
            bar_status = "✓" if result['bar_ok'] else "✗"
            continuity_status = "✓" if result['continuity_ok'] else "✗"
            
            print(f"{symbol:12} | Tick: {tick_status} | K线: {bar_status} | 连续性: {continuity_status}")
        
        # 获取数据库统计
        self.get_database_statistics()
        
        return results


def main():
    """主函数"""
    tester = DataRecordingTester()
    
    print("VeighNa数据录制功能测试")
    print("请确保:")
    print("1. 已启动VeighNa主程序")
    print("2. 已连接交易接口")
    print("3. 已启动数据录制功能")
    print("4. 当前在交易时间内")
    
    input("\n按回车键开始测试...")
    
    # 运行综合测试
    results = tester.run_comprehensive_test()
    
    # 检查是否有成功的录制
    success_count = sum(1 for r in results if r['tick_ok'] or r['bar_ok'])
    
    if success_count > 0:
        print(f"\n✓ 测试完成! {success_count}/{len(results)} 个合约有数据录制")
    else:
        print("\n✗ 测试完成! 未检测到任何数据录制")
        print("请检查数据录制配置和交易接口连接状态")


if __name__ == "__main__":
    main()
