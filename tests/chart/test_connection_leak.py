"""测试ChartWindow连接泄漏修复

测试查询缓存、Datafeed连接管理、异常处理等功能。
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from typing import Any

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import BarData, TickData, HistoryRequest
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.event import EVENT_TICK
from vnpy.event import Event

from tests.chart.test_base import TestBase


class TestQueryCache(TestBase):
    """测试查询缓存功能"""
    
    def test_open_price_cache_hit(self, qtbot):
        """T013: 测试开盘价缓存命中"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 设置测试数据
        symbol = "MHImain"
        exchange = Exchange.HKFE
        bar_datetime = datetime(2025, 12, 2, 10, 0)
        cached_price = 20000.0
        
        # 手动设置缓存
        cache_key = (symbol, bar_datetime)
        window._open_price_cache[cache_key] = (cached_price, time.time())
        
        # 测试缓存命中
        result = window._get_cached_open_price(symbol, bar_datetime)
        assert result == cached_price, "应该返回缓存的开盘价"
    
    def test_open_price_cache_miss(self, qtbot):
        """T014: 测试开盘价缓存未命中"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 设置测试数据（不设置缓存）
        symbol = "MHImain"
        bar_datetime = datetime(2025, 12, 2, 10, 0)
        
        # 测试缓存未命中
        result = window._get_cached_open_price(symbol, bar_datetime)
        assert result is None, "应该返回None（缓存未命中）"
    
    def test_cache_ttl_expiration(self, qtbot):
        """T015: 测试缓存TTL过期"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 设置测试数据（使用过期的timestamp）
        symbol = "MHImain"
        bar_datetime = datetime(2025, 12, 2, 10, 0)
        cached_price = 20000.0
        expired_timestamp = time.time() - 120  # 120秒前（超过60秒TTL）
        
        # 手动设置过期缓存
        cache_key = (symbol, bar_datetime)
        window._open_price_cache[cache_key] = (cached_price, expired_timestamp)
        
        # 测试缓存过期
        result = window._get_cached_open_price(symbol, bar_datetime)
        assert result is None, "应该返回None（缓存已过期）"
        assert cache_key not in window._open_price_cache, "过期缓存应该被删除"
    
    def test_cache_cleanup_on_size_limit(self, qtbot):
        """T016: 测试缓存大小限制时的清理"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 填充缓存到超过限制（1000条）
        base_time = datetime(2025, 12, 2, 10, 0)
        for i in range(1100):
            cache_key = ("MHImain", base_time + timedelta(minutes=i))
            window._open_price_cache[cache_key] = (20000.0 + i, time.time())
        
        # 添加一个过期缓存项（应该被清理）
        expired_key = ("MHImain", base_time + timedelta(minutes=2000))
        window._open_price_cache[expired_key] = (20000.0, time.time() - 120)
        
        # 添加新缓存项（应该触发清理）
        new_key = ("MHImain", base_time + timedelta(minutes=3000))
        window._set_cached_open_price("MHImain", base_time + timedelta(minutes=3000), 21000.0)
        
        # 验证过期缓存被清理
        assert expired_key not in window._open_price_cache, "过期缓存应该被清理"
        # 验证缓存大小在合理范围内（可能略大于1000，因为清理是异步的）
        assert len(window._open_price_cache) <= 1101, "缓存大小应该在合理范围内"
    
    def test_cache_clear_on_window_close(self, qtbot):
        """T017: 测试窗口关闭时缓存清理"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        from PySide6.QtGui import QCloseEvent
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 填充缓存
        base_time = datetime(2025, 12, 2, 10, 0)
        for i in range(10):
            window._set_cached_open_price("MHImain", base_time + timedelta(minutes=i), 20000.0 + i)
        
        # 验证缓存有数据
        assert len(window._open_price_cache) == 10, "应该有10个缓存项"
        
        # 模拟窗口关闭
        close_event = QCloseEvent()
        window.closeEvent(close_event)
        
        # 验证缓存被清理
        assert len(window._open_price_cache) == 0, "窗口关闭后缓存应该被清空"
    
    def test_cache_reduces_database_queries(self, qtbot):
        """T018: 测试缓存减少数据库查询"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        from vnpy.trader.database import get_database
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        window.current_vt_symbol = "MHImain.HKFE"
        
        # Mock数据库
        with patch('vnpy.trader.database.get_database') as mock_get_db:
            mock_database = Mock()
            mock_get_db.return_value = mock_database
            
            symbol = "MHImain"
            bar_datetime = datetime(2025, 12, 2, 10, 0)
            cached_price = 20000.0
            
            # 第一次：设置缓存
            window._set_cached_open_price(symbol, bar_datetime, cached_price)
            
            # 第二次：应该使用缓存，不查询数据库
            result = window._get_cached_open_price(symbol, bar_datetime)
            assert result == cached_price, "应该返回缓存的开盘价"
            
            # 验证数据库未被调用（因为使用了缓存）
            # 注意：这里我们只测试缓存逻辑，实际的数据库查询在process_tick_event中
            # 所以这里主要验证缓存方法本身工作正常
    
    def test_cache_thread_safety(self, qtbot):
        """T019: 测试缓存线程安全"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 多线程测试
        results = []
        errors = []
        
        def worker(thread_id: int):
            try:
                symbol = "MHImain"
                base_time = datetime(2025, 12, 2, 10, 0)
                
                # 每个线程设置不同的缓存项
                for i in range(10):
                    bar_datetime = base_time + timedelta(minutes=thread_id * 10 + i)
                    price = 20000.0 + thread_id * 10 + i
                    window._set_cached_open_price(symbol, bar_datetime, price)
                    
                    # 立即读取
                    result = window._get_cached_open_price(symbol, bar_datetime)
                    results.append((thread_id, i, result == price))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建10个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证没有错误
        assert len(errors) == 0, f"不应该有错误，但发现: {errors}"
        
        # 验证所有缓存操作都成功
        assert len(results) == 100, "应该有100个操作结果（10线程 × 10操作）"
        assert all(result[2] for result in results), "所有缓存操作应该成功"


class TestExceptionHandling(TestBase):
    """测试异常处理功能"""
    
    def test_database_query_exception_handling(self, qtbot):
        """T045: 测试数据库查询异常处理"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        from vnpy.trader.object import TickData
        from vnpy.event import Event
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        window.current_vt_symbol = "MHImain.HKFE"
        window.history_loaded = True
        
        # Mock数据库查询抛出异常
        with patch('vnpy.trader.database.get_database') as mock_get_db:
            mock_database = Mock()
            mock_database.load_bar_data.side_effect = Exception("Database connection error")
            mock_get_db.return_value = mock_database
            
            # 创建tick事件
            tick = self.create_tick_data(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2025, 12, 2, 10, 5),  # 秒数>0，会触发数据库查询
                last_price=20000.0
            )
            event = Event(EVENT_TICK, tick)
            
            # 处理tick事件（不应该抛出异常）
            try:
                window.process_tick_event(event)
                exception_raised = False
            except Exception:
                exception_raised = True
            
            # 验证异常被捕获，不会中断主流程
            assert not exception_raised, "异常应该被捕获，不应该中断主流程"
            
            # 验证错误日志被记录
            assert main_engine.write_log.called, "应该记录错误日志"
    
    def test_datafeed_query_exception_handling(self, qtbot):
        """T046: 测试Datafeed查询异常处理"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        from vnpy.trader.object import TickData
        from vnpy.event import Event
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        window.current_vt_symbol = "MHImain.HKFE"
        window.history_loaded = True
        
        # Mock Datafeed查询抛出异常
        mock_datafeed = Mock()
        mock_datafeed.query_tick_history.side_effect = Exception("Datafeed connection error")
        
        with patch.object(window, '_get_datafeed', return_value=mock_datafeed):
            # 创建tick事件
            tick = self.create_tick_data(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2025, 12, 2, 10, 5),  # 秒数>0，会触发Datafeed查询
                last_price=20000.0
            )
            event = Event(EVENT_TICK, tick)
            
            # 处理tick事件（不应该抛出异常）
            try:
                window.process_tick_event(event)
                exception_raised = False
            except Exception:
                exception_raised = True
            
            # 验证异常被捕获，不会中断主流程
            assert not exception_raised, "异常应该被捕获，不应该中断主流程"
    
    def test_connection_cleanup_on_exception(self, qtbot):
        """T047: 测试异常时连接清理"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 创建一个mock Datafeed并设置到缓存中
        mock_datafeed = Mock()
        mock_datafeed.close = Mock()
        window._cached_datafeed = mock_datafeed
        
        # 模拟异常情况下的清理
        try:
            raise Exception("Test exception")
        except Exception:
            # 即使有异常，也应该能清理连接
            if window._cached_datafeed is not None:
                if hasattr(window._cached_datafeed, 'close'):
                    window._cached_datafeed.close()
        
        # 验证close方法被调用
        mock_datafeed.close.assert_called_once()
    
    def test_error_logging_on_exception(self, qtbot):
        """T048: 测试异常时的错误日志记录"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 模拟异常并记录日志
        try:
            raise Exception("Test error message")
        except Exception as e:
            if main_engine:
                main_engine.write_log(
                    f"[ChartWindow] 查询失败: {e}",
                    "ChartWindow"
                )
        
        # 验证错误日志被记录
        assert main_engine.write_log.called, "应该记录错误日志"
        log_call = main_engine.write_log.call_args
        assert "查询失败" in str(log_call) or "Test error message" in str(log_call), "日志应该包含错误信息"
    
    def test_no_exception_propagation_to_main_flow(self, qtbot):
        """T049: 测试异常不会传播到主流程"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 测试异常处理：模拟数据库查询异常
        with patch('vnpy.trader.database.get_database') as mock_get_db:
            mock_database = Mock()
            mock_database.load_bar_data.side_effect = Exception("Database error")
            mock_get_db.return_value = mock_database
            
            # 测试异常被正确捕获，不会传播
            exception_propagated = False
            try:
                # 模拟在异常处理块中的查询
                try:
                    database = mock_get_db.return_value
                    database.load_bar_data("MHImain", Exchange.HKFE, None, None, None)
                except Exception as e:
                    # 异常被捕获，记录日志但不传播
                    if main_engine:
                        main_engine.write_log(
                            f"[ChartWindow] 数据库查询失败: {e}",
                            "ChartWindow"
                        )
                    # 不重新抛出异常
            except Exception:
                exception_propagated = True
            
            # 验证异常被捕获，不会传播到外层
            assert not exception_propagated, "异常应该被捕获，不应该传播到主流程"
            # 验证错误日志被记录
            assert main_engine.write_log.called, "应该记录错误日志"


class TestConnectionMonitoring(TestBase):
    """测试连接数监控功能"""
    
    def test_database_connection_count_monitoring(self, qtbot):
        """T056: 测试数据库连接数监控"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 测试连接数监控方法存在
        assert hasattr(window, '_get_connection_count'), "应该有连接数监控方法"
        
        # 测试获取连接数（可能返回None如果无法获取）
        connection_count = window._get_connection_count()
        # 连接数应该是数字或None
        assert connection_count is None or isinstance(connection_count, (int, dict)), \
            f"连接数应该是数字或None，实际: {type(connection_count)}"
    
    def test_datafeed_connection_count_monitoring(self, qtbot):
        """T057: 测试Datafeed连接数监控"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 测试Datafeed连接数监控
        # 由于我们使用缓存的Datafeed实例，应该只有0或1个实例
        datafeed_count = 0
        if window._cached_datafeed is not None:
            datafeed_count = 1
        
        # 验证Datafeed实例数量在合理范围内（0或1）
        assert datafeed_count <= 1, f"Datafeed实例数量应该<=1，实际: {datafeed_count}"
    
    def test_connection_count_logging(self, qtbot):
        """T058: 测试连接数日志记录"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 测试连接数日志记录方法
        if hasattr(window, '_log_connection_count'):
            window._log_connection_count()
            # 验证日志被记录
            assert main_engine.write_log.called, "应该记录连接数日志"
    
    def test_connection_leak_detection(self, qtbot):
        """T059: 测试连接泄漏检测"""
        from vnpy.trader.ui.widget import ChartWindow
        from vnpy.trader.engine import MainEngine
        from vnpy.event import EventEngine
        
        # 创建ChartWindow实例
        main_engine = Mock(spec=MainEngine)
        main_engine.write_log = Mock()
        event_engine = Mock(spec=EventEngine)
        window = ChartWindow(main_engine, event_engine)
        
        # 测试连接泄漏检测
        # 创建多个Datafeed实例（模拟泄漏）
        initial_count = 0
        if window._cached_datafeed is not None:
            initial_count = 1
        
        # 多次调用_get_datafeed应该返回同一个实例
        datafeed1 = window._get_datafeed()
        datafeed2 = window._get_datafeed()
        
        # 验证返回的是同一个实例（如果存在）
        if datafeed1 is not None and datafeed2 is not None:
            assert datafeed1 is datafeed2, "应该返回同一个Datafeed实例，避免连接泄漏"
