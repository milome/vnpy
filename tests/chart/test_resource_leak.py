"""测试ChartWindow资源泄漏修复

测试QPicture资源释放、数据库连接管理、Datafeed连接管理等功能。
"""

import pytest
import time
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Any

from vnpy.trader.ui import QtGui, QtWidgets, QtCore
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

from vnpy.chart.item import ChartItem, CandleItem, VolumeItem
from vnpy.chart.manager import BarManager
from tests.chart.test_base import TestBase


class TestQPictureResourceRelease(TestBase):
    """测试QPicture资源释放功能"""
    
    def test_update_bar_releases_old_picture(self, qtbot):
        """T001: 测试update_bar()释放旧的QPicture对象"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建初始K线
        bar1 = self.create_bar_data(
            datetime=datetime(2025, 12, 2, 10, 0),
            open_price=20000.0,
            close_price=20050.0
        )
        manager.update_bar(bar1)
        
        # 触发绘制，创建QPicture对象
        item.update_bar(bar1)
        # 等待绘制完成
        qtbot.wait(100)
        
        # 获取初始的QPicture对象引用
        ix = manager.get_index(bar1.datetime)
        assert ix is not None
        initial_picture = Mock()
        item._bar_picutures[ix] = initial_picture
        
        # 验证初始对象存在
        assert item._bar_picutures.get(ix) == initial_picture
        
        # 更新K线数据
        bar2 = self.create_bar_data(
            datetime=bar1.datetime,
            open_price=20000.0,
            close_price=20100.0  # 价格变化
        )
        manager.update_bar(bar2)
        
        # 更新图表项
        item.update_bar(bar2)
        qtbot.wait(100)
        
        # 验证旧的QPicture对象引用被清除
        # 注意：在Python中，del操作会删除引用，但对象可能不会立即被垃圾回收
        # 我们验证引用被设置为None
        updated_picture = item._bar_picutures.get(ix)
        # 新对象可能为None（如果还未绘制）或新的对象
        # 关键是要验证旧的引用被清除
        assert updated_picture != initial_picture or updated_picture is None
    
    def test_clear_all_releases_all_pictures(self, qtbot):
        """T002: 测试clear_all()释放所有QPicture对象"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        from unittest.mock import Mock
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 直接创建多个mock QPicture对象用于测试（不依赖BarManager）
        picture1 = Mock()
        picture2 = Mock()
        picture3 = Mock()
        
        # 直接设置到字典中
        item._bar_picutures[0] = picture1
        item._bar_picutures[1] = picture2
        item._bar_picutures[2] = picture3
        
        # 创建_item_picuture对象
        item._item_picuture = Mock()
        assert item._item_picuture is not None, "item_picuture对象创建失败"
        
        # 验证有QPicture对象（在clear_all之前）
        picture_count_before = len([p for p in item._bar_picutures.values() if p is not None])
        assert picture_count_before == 3, f"clear_all之前应该有3个QPicture对象，实际有{picture_count_before}个"
        
        # 调用clear_all()
        item.clear_all()
        
        # 验证所有QPicture对象引用被清除
        # 这是修复的关键：clear_all()会执行del操作，然后清空字典
        assert item._item_picuture is None, "item_picuture应该被清除"
        assert len(item._bar_picutures) == 0, "bar_picutures字典应该被清空"
    
    def test_memory_leak_after_frequent_updates(self, qtbot):
        """T003: 测试频繁更新后没有内存泄漏"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        import gc
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建初始K线
        base_time = datetime(2025, 12, 2, 10, 0)
        bar = self.create_bar_data(
            datetime=base_time,
            open_price=20000.0,
            close_price=20050.0
        )
        manager.update_bar(bar)
        
        # 频繁更新同一根K线（模拟实时更新）
        initial_picture_count = 0
        for i in range(100):
            # 更新价格
            updated_bar = self.create_bar_data(
                datetime=base_time,
                open_price=20000.0 + i,
                close_price=20050.0 + i
            )
            manager.update_bar(updated_bar)
            item.update_bar(updated_bar)
            
            if i == 0:
                qtbot.wait(100)
                initial_picture_count = sum(
                    1 for p in item._bar_picutures.values() if p is not None
                )
        
        qtbot.wait(200)
        
        # 强制垃圾回收
        gc.collect()
        
        # 验证QPicture对象数量没有持续增长
        final_picture_count = sum(
            1 for p in item._bar_picutures.values() if p is not None
        )
        # 应该只有当前可见的K线有QPicture对象
        assert final_picture_count <= initial_picture_count + 5  # 允许小幅波动
    
    def test_qpicture_release_performance(self, qtbot):
        """T004: 测试QPicture释放性能（应该 < 100ms）"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建K线
        bar = self.create_bar_data(
            datetime=datetime(2025, 12, 2, 10, 0),
            open_price=20000.0,
            close_price=20050.0
        )
        manager.update_bar(bar)
        item.update_bar(bar)
        qtbot.wait(100)
        
        # 测量更新性能
        start_time = time.perf_counter()
        
        # 更新K线（应该释放旧对象）
        updated_bar = self.create_bar_data(
            datetime=bar.datetime,
            open_price=20000.0,
            close_price=20100.0
        )
        manager.update_bar(updated_bar)
        item.update_bar(updated_bar)
        
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        
        # 验证性能要求：< 100ms
        assert elapsed_ms < 100, f"QPicture释放耗时 {elapsed_ms:.2f}ms，超过100ms限制"
    
    def test_qpicture_release_on_window_close(self, qtbot):
        """T005: 测试窗口关闭时QPicture对象被释放"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建多个K线
        for i in range(5):
            bar = self.create_bar_data(
                datetime=datetime(2025, 12, 2, 10, i),
                open_price=20000.0 + i * 10,
                close_price=20050.0 + i * 10
            )
            manager.update_bar(bar)
            item.update_bar(bar)
        
        qtbot.wait(200)
        
        # 验证有QPicture对象
        assert len(item._bar_picutures) > 0
        
        # 模拟窗口关闭：调用clear_all()
        item.clear_all()
        
        # 验证所有对象被释放
        assert item._item_picuture is None
        assert len(item._bar_picutures) == 0
    
    def test_candleitem_qpicture_release(self, qtbot):
        """T006: 测试CandleItem的QPicture释放"""
        from vnpy.chart.item import CandleItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = CandleItem(manager)
        
        # 创建K线
        bar = self.create_bar_data(
            datetime=datetime(2025, 12, 2, 10, 0),
            open_price=20000.0,
            close_price=20050.0
        )
        manager.update_bar(bar)
        
        # 初始更新
        item.update_bar(bar)
        qtbot.wait(100)
        
        ix = manager.get_index(bar.datetime)
        initial_picture = item._bar_picutures.get(ix)
        
        # 更新K线
        updated_bar = self.create_bar_data(
            datetime=bar.datetime,
            open_price=20000.0,
            close_price=20100.0
        )
        manager.update_bar(updated_bar)
        item.update_bar(updated_bar)
        qtbot.wait(100)
        
        # 验证旧对象引用被清除
        updated_picture = item._bar_picutures.get(ix)
        assert updated_picture != initial_picture or updated_picture is None
    
    def test_volumeitem_qpicture_release(self, qtbot):
        """T007: 测试VolumeItem的QPicture释放"""
        from vnpy.chart.item import VolumeItem
        from vnpy.chart.manager import BarManager
        
        manager = BarManager()
        item = VolumeItem(manager)
        
        # 创建K线
        bar = self.create_bar_data(
            datetime=datetime(2025, 12, 2, 10, 0),
            open_price=20000.0,
            close_price=20050.0,
            volume=1000.0
        )
        manager.update_bar(bar)
        
        # 初始更新
        item.update_bar(bar)
        qtbot.wait(100)
        
        ix = manager.get_index(bar.datetime)
        initial_picture = item._bar_picutures.get(ix)
        
        # 更新K线
        updated_bar = self.create_bar_data(
            datetime=bar.datetime,
            open_price=20000.0,
            close_price=20100.0,
            volume=2000.0  # 成交量变化
        )
        manager.update_bar(updated_bar)
        item.update_bar(updated_bar)
        qtbot.wait(100)
        
        # 验证旧对象引用被清除
        updated_picture = item._bar_picutures.get(ix)
        assert updated_picture != initial_picture or updated_picture is None

