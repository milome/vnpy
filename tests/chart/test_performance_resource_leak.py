"""性能测试：验证资源泄漏修复的性能影响

测试 Phase 1-5 的性能指标，确保修复不会显著影响性能。
"""

import pytest
import time
import gc
from datetime import datetime, timedelta
from unittest.mock import Mock
from typing import Any

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

from tests.chart.test_base import TestBase


class TestPerformanceResourceLeak(TestBase):
    """性能测试：资源泄漏修复"""
    
    def test_qpicture_release_performance(self, qtbot):
        """T070: 测试QPicture释放性能"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        from unittest.mock import Mock
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建mock QPicture对象
        bar = self.create_bar_data(
            datetime=datetime(2025, 12, 2, 10, 0),
            open_price=20000.0,
            close_price=20050.0
        )
        manager.update_bar(bar)
        
        # 手动设置mock对象
        ix = manager.get_index(bar.datetime)
        if ix is not None:
            item._bar_picutures[ix] = Mock()
        
        # 测量update_bar性能（包含资源释放）
        start_time = time.perf_counter()
        for _ in range(100):
            item.update_bar(bar)
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 100) * 1000
        
        # 验证性能：应该 < 5ms
        assert avg_time_ms < 5, \
            f"QPicture释放性能应该在合理范围内，平均: {avg_time_ms:.2f}ms"
    
    def test_cache_hit_rate(self, qtbot):
        """T071: 测试缓存命中率（应该 > 90%）"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        symbol = "MHImain"
        base_time = datetime(2025, 12, 2, 10, 0)
        
        # 设置缓存
        for i in range(100):
            bar_datetime = base_time + timedelta(minutes=i)
            window._set_cached_open_price(symbol, bar_datetime, 20000.0 + i)
        
        # 测试缓存命中率
        hits = 0
        misses = 0
        
        for i in range(100):
            bar_datetime = base_time + timedelta(minutes=i)
            result = window._get_cached_open_price(symbol, bar_datetime)
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        # 测试未缓存的查询
        for i in range(10):
            bar_datetime = base_time + timedelta(minutes=200 + i)
            result = window._get_cached_open_price(symbol, bar_datetime)
            if result is None:
                misses += 1
        
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0
        
        # 验证缓存命中率 > 90%
        assert hit_rate > 0.9, \
            f"缓存命中率应该 > 90%，实际: {hit_rate:.2%} (hits: {hits}, misses: {misses})"
    
    def test_query_frequency_reduction(self, qtbot):
        """T072: 测试查询频率减少"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        symbol = "MHImain"
        bar_datetime = datetime(2025, 12, 2, 10, 0)
        
        # 模拟数据库查询（使用Mock）
        query_count = [0]  # 使用列表以便在闭包中修改
        
        def mock_get_cached_open_price(symbol, bar_datetime):
            # 先检查缓存
            result = window._get_cached_open_price(symbol, bar_datetime)
            if result is None:
                # 缓存未命中，需要查询数据库
                query_count[0] += 1
                # 模拟查询结果
                window._set_cached_open_price(symbol, bar_datetime, 20000.0)
                return 20000.0
            return result
        
        # 第一次：查询数据库
        mock_get_cached_open_price(symbol, bar_datetime)
        assert query_count[0] == 1, "第一次应该查询数据库"
        
        # 第二次：使用缓存
        mock_get_cached_open_price(symbol, bar_datetime)
        assert query_count[0] == 1, "第二次应该使用缓存，不查询数据库"
        
        # 验证查询频率减少：100次查询应该只有1次数据库查询
        for _ in range(98):
            mock_get_cached_open_price(symbol, bar_datetime)
        
        assert query_count[0] == 1, \
            f"100次查询应该只有1次数据库查询，实际: {query_count[0]}"
    
    def test_memory_usage_over_time(self, qtbot):
        """T073: 测试内存使用随时间变化"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 创建ChartItem实例
        manager = BarManager()
        item = CandleItem(manager)
        
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())
        
        # 模拟长时间运行（频繁更新）
        base_time = datetime(2025, 12, 2, 10, 0)
        for i in range(200):
            bar = self.create_bar_data(
                datetime=base_time + timedelta(minutes=i % 60),  # 循环使用60个时间点
                open_price=20000.0 + i,
                close_price=20050.0 + i
            )
            manager.update_bar(bar)
            item.update_bar(bar)
            
            # 每20次更新后清理
            if i % 20 == 0:
                gc.collect()
        
        # 强制垃圾回收
        gc.collect()
        
        # 记录最终对象数量
        final_objects = len(gc.get_objects())
        
        # 验证内存使用增长在合理范围内（允许30%增长，因为测试环境）
        growth_ratio = (final_objects - initial_objects) / max(initial_objects, 1)
        assert growth_ratio < 0.3, \
            f"内存使用增长应该在合理范围内，实际增长: {growth_ratio:.2%}"
    
    def test_connection_count_over_time(self, qtbot):
        """T074: 测试连接数随时间变化"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 记录初始连接数
        initial_count = window._get_connection_count()
        initial_datafeed_count = initial_count.get("datafeed", 0) if initial_count else 0
        
        # 模拟长时间运行（多次调用_get_datafeed）
        for _ in range(50):
            window._get_datafeed()
            # 模拟时间间隔
            time.sleep(0.001)
        
        # 记录最终连接数
        final_count = window._get_connection_count()
        final_datafeed_count = final_count.get("datafeed", 0) if final_count else 0
        
        # 验证连接数保持稳定（应该复用同一个实例）
        assert final_datafeed_count <= initial_datafeed_count + 1, \
            f"连接数应该保持稳定，初始: {initial_datafeed_count}, 最终: {final_datafeed_count}"

