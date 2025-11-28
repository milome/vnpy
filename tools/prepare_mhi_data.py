#!/usr/bin/env python3
"""
MHI期货历史数据下载脚本
专门为策略开发和回测准备MHI期货的历史K线数据
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加路径以导入本地模块
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest

# 导入网关
from vnpy_futu import FutuGateway


class MHIDataPreparer:
    """MHI数据准备器"""

    def __init__(self):
        """初始化"""
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        # 添加富途网关
        self.main_engine.add_gateway(FutuGateway)

        # MHI合约配置
        self.mhi_contracts = [
            {
                "symbol": "MHImain",
                "exchange": Exchange.HKFE,
                "name": "小恒指主力合约",
                "futu_code": "HK.MHImain"
            },
            {
                "symbol": "MHI2511",
                "exchange": Exchange.HKFE,
                "name": "小恒指2025年11月",
                "futu_code": "HK_FUTURE.MHI2511"
            },
            {
                "symbol": "MHI2512",
                "exchange": Exchange.HKFE,
                "name": "小恒指2025年12月",
                "futu_code": "HK_FUTURE.MHI2512"
            }
        ]

        self.gateway_name = "FUTU"
        self.is_connected = False

    def connect_futu(self):
        """连接富途网关"""
        print("正在连接富途网关...")

        gateway_setting = {
            "host": "127.0.0.1",
            "port": 11111,
            "market": "HK",
            "env": 1  # 模拟交易环境
        }

        self.main_engine.connect(gateway_setting, self.gateway_name)

        # 等待连接建立
        for i in range(10):
            time.sleep(1)
            gateway = self.main_engine.get_gateway(self.gateway_name)
            if gateway and gateway.query_history:
                self.is_connected = True
                print("✓ 富途网关连接成功!")
                break
            print(f"等待连接... ({i+1}/10)")

        if not self.is_connected:
            print("✗ 富途网关连接失败!")
            return False

        return True

    def download_history_data(self, days_back=30):
        """下载历史数据"""
        if not self.is_connected:
            print("网关未连接，无法下载数据")
            return False

        print(f"\n开始下载最近{days_back}天的历史数据...")

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)

        print(f"时间范围: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")

        total_downloaded = 0

        for contract in self.mhi_contracts:
            symbol = contract["symbol"]
            exchange = contract["exchange"]
            name = contract["name"]

            print(f"\n处理合约: {symbol}.{exchange.value} ({name})")

            # 下载1分钟K线数据
            print("  下载1分钟K线数据...")

            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=start_time,
                end=end_time
            )

            try:
                history_data = self.main_engine.query_history(req, self.gateway_name)

                if history_data:
                    print(f"    ✓ 成功获取 {len(history_data)} 条1分钟数据")

                    # 保存数据到数据库
                    database = self.main_engine.get_engine("Database")
                    if database:
                        database.save_bar_data(history_data)
                        print(f"    ✓ 数据已保存到数据库")
                        total_downloaded += len(history_data)
                    else:
                        print(f"    ⚠ 数据库引擎未找到，数据未保存")
                else:
                    print(f"    ✗ 未获取到数据")

            except Exception as e:
                print(f"    ✗ 下载失败: {e}")

            # 下载日K线数据
            print("  下载日K线数据...")

            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=start_time,
                end=end_time
            )

            try:
                history_data = self.main_engine.query_history(req, self.gateway_name)

                if history_data:
                    print(f"    ✓ 成功获取 {len(history_data)} 条日线数据")

                    # 保存数据到数据库
                    database = self.main_engine.get_engine("Database")
                    if database:
                        database.save_bar_data(history_data)
                        print(f"    ✓ 数据已保存到数据库")
                        total_downloaded += len(history_data)
                    else:
                        print(f"    ⚠ 数据库引擎未找到，数据未保存")
                else:
                    print(f"    ✗ 未获取到数据")

            except Exception as e:
                print(f"    ✗ 下载失败: {e}")

        return total_downloaded

    def verify_data(self):
        """验证下载的数据"""
        print("\n验证数据完整性...")

        database = self.main_engine.get_engine("Database")
        if not database:
            print("数据库引擎未找到，无法验证数据")
            return

        for contract in self.mhi_contracts:
            symbol = contract["symbol"]
            exchange = contract["exchange"]
            name = contract["name"]

            print(f"\n检查合约: {symbol}.{exchange.value}")

            # 检查1分钟数据
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=datetime.now() - timedelta(days=7),
                end=datetime.now()
            )

            data = database.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=req.start,
                end=req.end
            )

            print(f"  1分钟数据: {len(data) if data else 0} 条")

            # 检查日线数据
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=datetime.now() - timedelta(days=30),
                end=datetime.now()
            )

            data = database.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=req.start,
                end=req.end
            )

            print(f"  日线数据: {len(data) if data else 0} 条")

    def close(self):
        """关闭连接"""
        self.main_engine.close()


def main():
    """主程序"""
    print("=" * 60)
    print("MHI期货历史数据下载程序")
    print("=" * 60)

    preparer = MHIDataPreparer()

    try:
        # 连接富途网关
        if not preparer.connect_futu():
            print("\n程序退出: 无法连接富途网关")
            return

        # 下载历史数据
        total_count = preparer.download_history_data(days_back=30)

        if total_count > 0:
            print(f"\n✓ 数据下载完成! 总计: {total_count} 条")

            # 验证数据
            preparer.verify_data()

            print("\n✓ MHI期货历史数据准备完成!")
            print("现在可以开始策略开发和回测。")
        else:
            print("\n⚠ 没有下载到任何数据")
            print("请检查:")
            print("1. 富途牛牛客户端是否启动")
            print("2. OpenD服务是否开启")
            print("3. 网络连接是否正常")

    except Exception as e:
        print(f"\n✗ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        preparer.close()
        print("\n程序结束")


if __name__ == "__main__":
    main()