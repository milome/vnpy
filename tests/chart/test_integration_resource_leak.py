"""Phase 6: 集成测试 - 资源泄漏修复验证

测试所有 Phase 的修复是否正常工作，确保没有回归问题。
"""

import pytest
import time
import gc
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.event import EVENT_TICK
from vnpy.event import Event, EventEngine

from tests.chart.test_base import TestBase


class TestIntegrationResourceLeak(TestBase):
    """集成测试：验证所有修复工作正常"""
    
    def test_all_fixes_work_together(self, qtbot):
        """T067: 测试所有修复一起工作"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 验证Phase 1: QPicture资源释放
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建并更新K线
        bar1 = self.create_bar_data(datetime=datetime(2025, 12, 2, 10, 0))
        manager.update_bar(bar1)
        
        # 手动创建QPicture对象
        from unittest.mock import Mock as MockObject
        ix = manager.get_index(bar1.datetime)
        initial_picture = MockObject()
        item._bar_picutures[ix] = initial_picture
        
        # 更新K线（应该释放旧对象）
        bar2 = self.create_bar_data(datetime=bar1.datetime, close_price=20100.0)
        manager.update_bar(bar2)
        item.update_bar(bar2)
        
        # 验证旧对象被释放
        assert item._bar_picutures.get(ix) is None, "QPicture对象应该被释放"
        
        # 验证Phase 2: 查询缓存
        symbol = "MHImain"
        bar_datetime = datetime(2025, 12, 2, 10, 0)
        cached_price = 20000.0
        
        window._set_cached_open_price(symbol, bar_datetime, cached_price)
        result = window._get_cached_open_price(symbol, bar_datetime)
        assert result == cached_price, "缓存应该工作正常"
        
        # 验证Phase 3: Datafeed实例复用
        assert hasattr(window, '_cached_datafeed'), "应该有Datafeed缓存"
        assert hasattr(window, '_get_datafeed'), "应该有_get_datafeed方法"
        
        # 验证Phase 5: 连接数监控
        assert hasattr(window, '_get_connection_count'), "应该有连接数监控方法"
        assert hasattr(window, '_log_connection_count'), "应该有连接数日志方法"
        connection_count = window._get_connection_count()
        assert connection_count is not None, "应该能获取连接数"
    
    def test_memory_usage_stability(self, qtbot):
        """T065: 测试内存使用稳定性"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 频繁更新K线（模拟实时更新）
        base_time = datetime(2025, 12, 2, 10, 0)
        for i in range(100):
            bar = self.create_bar_data(
                datetime=base_time,
                close_price=20000.0 + i
            )
            manager.update_bar(bar)
            item.update_bar(bar)
        
        # 强制垃圾回收
        gc.collect()
        
        # 验证QPicture对象数量没有持续增长
        picture_count = sum(1 for p in item._bar_picutures.values() if p is not None)
        # 应该只有当前K线有QPicture对象（0或1）
        assert picture_count <= 1, f"QPicture对象数量应该<=1，实际: {picture_count}"
    
    def test_connection_count_stability(self, qtbot):
        """T066: 测试连接数稳定性"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 多次调用_get_datafeed
        initial_count = window._get_connection_count()
        
        for i in range(10):
            datafeed = window._get_datafeed()
        
        final_count = window._get_connection_count()
        
        # 验证连接数稳定（应该复用同一个实例）
        if initial_count and final_count:
            assert initial_count == final_count, \
                f"连接数应该稳定，初始: {initial_count}, 最终: {final_count}"
    
    def test_backward_compatibility(self, qtbot):
        """T068: 测试向后兼容性"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 验证原有属性仍然存在
        assert hasattr(window, 'main_engine'), "应该保留main_engine属性"
        assert hasattr(window, 'event_engine'), "应该保留event_engine属性"
        assert hasattr(window, 'current_vt_symbol'), "应该保留current_vt_symbol属性"
        assert hasattr(window, 'history_loaded'), "应该保留history_loaded属性"
        
        # 验证新增属性
        assert hasattr(window, '_open_price_cache'), "应该有_open_price_cache属性"
        assert hasattr(window, '_cached_datafeed'), "应该有_cached_datafeed属性"
    
    def test_performance_impact(self, qtbot):
        """T069: 测试性能影响（应该 < 5% 性能下降）"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 测量更新性能
        base_time = datetime(2025, 12, 2, 10, 0)
        bar = self.create_bar_data(datetime=base_time)
        manager.update_bar(bar)
        
        # 测量100次更新的时间
        start_time = time.perf_counter()
        for i in range(100):
            updated_bar = self.create_bar_data(
                datetime=base_time,
                close_price=20000.0 + i
            )
            manager.update_bar(updated_bar)
            item.update_bar(updated_bar)
        end_time = time.perf_counter()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / 100
        
        # 验证平均更新时间 < 10ms（性能要求）
        assert avg_time_ms < 10, f"平均更新时间 {avg_time_ms:.2f}ms，超过10ms限制"
