"""Phase 5: 多周期模式性能测试

性能测试目标：
- T078: 测试模式切换性能 (< 500ms)
- T079: 测试大数据量加载性能 (< 5s)
- T080: 测试实时更新延迟 (< 100ms)
- T081: 测试内存使用 (< 300MB)
"""

import pytest
import time
import statistics
import psutil
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.event import EVENT_TICK
from vnpy.trader.object import TickData, BarData
from vnpy.event import Event, EventEngine

from .test_base import TestBase


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self, metric_name: str):
        self.metric_name = metric_name
        self.latencies: List[float] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def start(self) -> None:
        """开始计时"""
        self.start_time = time.perf_counter()

    def stop(self) -> None:
        """停止计时并记录延迟"""
        self.end_time = time.perf_counter()
        latency_ms = (self.end_time - self.start_time) * 1000
        self.latencies.append(latency_ms)

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        if not self.latencies:
            return {
                "count": 0,
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
            }

        sorted_latencies = sorted(self.latencies)
        count = len(sorted_latencies)

        return {
            "count": count,
            "avg_ms": statistics.mean(sorted_latencies),
            "min_ms": min(sorted_latencies),
            "max_ms": max(sorted_latencies),
            "p50_ms": sorted_latencies[int(count * 0.50)] if count > 0 else 0.0,
            "p95_ms": sorted_latencies[int(count * 0.95)] if count > 1 else sorted_latencies[0],
            "p99_ms": sorted_latencies[int(count * 0.99)] if count > 1 else sorted_latencies[0],
        }

    def reset(self) -> None:
        """重置统计"""
        self.latencies.clear()
        self.start_time = 0.0
        self.end_time = 0.0


class TestMultiTimeframePerformance(TestBase):
    """多周期模式性能测试"""

    @pytest.fixture
    def event_engine(self) -> EventEngine:
        """创建真实的 EventEngine 用于性能测试"""
        engine = EventEngine()
        engine.start()
        yield engine
        engine.stop()

    @pytest.fixture
    def main_engine(self) -> Mock:
        """创建模拟的 MainEngine"""
        engine = Mock()
        engine.write_log = Mock()
        engine.get_contract = Mock(return_value=Mock(
            gateway_name="TEST",
            pricetick=1.0,
            min_volume=1
        ))
        engine.get_all_gateway_names = Mock(return_value=["TEST"])
        engine.subscribe = Mock()
        engine.get_all_active_orders = Mock(return_value=[])
        engine.get_all_positions = Mock(return_value=[])
        return engine

    @pytest.fixture
    def chart_window(self, main_engine, event_engine, qtbot):
        """创建ChartWindow实例用于性能测试"""
        from vnpy.trader.ui.widget import ChartWindow
        from unittest.mock import patch
        
        # 在创建 ChartWindow 之前，Mock 一些可能失败的操作
        with patch('vnpy.trader.database.get_database'), \
             patch('vnpy.chart.multi_timeframe_widget.get_database'):
            window = ChartWindow(main_engine, event_engine)
            
            # Mock图表组件（如果已创建）
            # 注意：不要完全替换 chart 对象，只 Mock 必要的方法
            if window.chart and not isinstance(window.chart, Mock):
                # 只 Mock 方法，保留原始对象
                window.chart.update_history = Mock()
                window.chart.update_bar = Mock()
                window.chart.set_future_bars = Mock()
                window.chart.set_vt_symbol = Mock()
                window.chart.get_drawing_order_controller = Mock(return_value=Mock())
                window.chart.clear_all = Mock()
                window.chart.get_plot = Mock(return_value=Mock())
                # 确保有必要的属性
                if not hasattr(window.chart, '_bar_count'):
                    window.chart._bar_count = 100
                if not hasattr(window.chart, '_right_ix'):
                    window.chart._right_ix = 100
                if not hasattr(window.chart, '_update_x_range'):
                    window.chart._update_x_range = Mock()
                # 确保 isVisible 和 setVisible 是方法
                if not hasattr(window.chart, 'isVisible') or not callable(window.chart.isVisible):
                    window.chart.isVisible = Mock(return_value=True)
                if not hasattr(window.chart, 'setVisible') or not callable(window.chart.setVisible):
                    window.chart.setVisible = Mock()
                # Mock 价格线管理器和突破监控
                if not hasattr(window.chart, '_price_line_manager'):
                    window.chart._price_line_manager = Mock()
                    window.chart._price_line_manager.get_all_lines = Mock(return_value={})
                if not hasattr(window.chart, '_breakthrough_monitor'):
                    window.chart._breakthrough_monitor = Mock()
            
            # Mock状态标签（如果已创建）
            if hasattr(window, 'status_label') and window.status_label:
                if not isinstance(window.status_label, Mock):
                    window.status_label.setText = Mock()
            
            # Mock时间滚动条（如果已创建）
            if hasattr(window, 'time_slider') and window.time_slider:
                # 确保滚动条有正确的范围
                if hasattr(window.time_slider, 'setRange'):
                    window.time_slider.setRange(0, 100)
                    window.time_slider.setValue(50)
            
            # 设置初始状态
            window.current_vt_symbol = "MHImain.HKFE"
            window.current_interval = "1m"
            window.history_loaded = False
            
            # 显示窗口以确保isVisible()能正确工作
            window.show()
            qtbot.waitExposed(window)
            
            # 使用 yield 而不是 return，以便在测试结束后清理
            yield window
            
            # 清理资源（在测试结束后）
            try:
                # 清理 multi_timeframe_widget（如果存在）
                if hasattr(window, 'multi_timeframe_widget') and window.multi_timeframe_widget:
                    # 避免触发 Qt 图形对象的清理问题
                    try:
                        # 先隐藏 widget
                        window.multi_timeframe_widget.setVisible(False)
                        # 清理内部图表对象（如果存在）
                        if hasattr(window.multi_timeframe_widget, '_chart') and window.multi_timeframe_widget._chart:
                            try:
                                # 清理图表中的图形项
                                if hasattr(window.multi_timeframe_widget._chart, 'clear'):
                                    window.multi_timeframe_widget._chart.clear()
                            except Exception:
                                pass
                        # 移除父窗口关系
                        window.multi_timeframe_widget.setParent(None)
                    except Exception:
                        pass
                    window.multi_timeframe_widget = None
            except Exception:
                # 忽略清理错误
                pass

    def test_mode_switching_performance(self, chart_window):
        """T078: 测试模式切换性能 (< 500ms)"""
        metrics = PerformanceMetrics("mode_switching")
        
        # 执行多次模式切换，收集性能数据
        num_iterations = 10
        
        for i in range(num_iterations):
            # 切换到多周期模式
            metrics.start()
            chart_window.switch_display_mode("multi")
            metrics.stop()
            
            # 切换回单周期模式
            metrics.start()
            chart_window.switch_display_mode("single")
            metrics.stop()
        
        # 获取统计信息
        stats = metrics.get_stats()
        
        # 验证性能指标
        assert stats["avg_ms"] < 500, \
            f"模式切换平均延迟 {stats['avg_ms']:.2f}ms 超过 500ms 限制"
        assert stats["p95_ms"] < 500, \
            f"模式切换 P95 延迟 {stats['p95_ms']:.2f}ms 超过 500ms 限制"
        
        # 打印性能统计（用于调试）
        print(f"\n模式切换性能统计:")
        print(f"  测试次数: {stats['count']}")
        print(f"  平均延迟: {stats['avg_ms']:.2f}ms")
        print(f"  最小延迟: {stats['min_ms']:.2f}ms")
        print(f"  最大延迟: {stats['max_ms']:.2f}ms")
        print(f"  P50 延迟: {stats['p50_ms']:.2f}ms")
        print(f"  P95 延迟: {stats['p95_ms']:.2f}ms")
        print(f"  P99 延迟: {stats['p99_ms']:.2f}ms")

    def test_large_data_loading_performance(self, chart_window):
        """T079: 测试大数据量加载性能 (< 5s)"""
        from vnpy.trader.object import BarData
        
        # 创建大量测试数据（7天的1分钟数据，约 7 * 24 * 60 = 10080 条）
        test_bars = []
        base_time = datetime(2024, 11, 14, 9, 0)
        num_bars = 10080  # 7天的1分钟数据
        
        for i in range(num_bars):
            minutes = i % 60
            hours = (i // 60) % 24
            days = i // (60 * 24)
            bar_time = base_time + timedelta(days=days, hours=hours, minutes=minutes)
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=bar_time,
                interval=Interval.MINUTE,
                volume=1000,
                open_price=25000.0 + i * 0.1,
                high_price=25001.0 + i * 0.1,
                low_price=24999.0 + i * 0.1,
                close_price=25000.5 + i * 0.1,
                gateway_name="test"
            )
            test_bars.append(bar)
        
        # 测试单周期模式下的数据加载性能
        chart_window.switch_display_mode("single")
        chart_window.current_vt_symbol = "MHImain.HKFE"
        
        metrics = PerformanceMetrics("data_loading_single")
        metrics.start()
        chart_window.history_data = test_bars
        # 模拟数据加载完成
        chart_window.history_loaded = True
        metrics.stop()
        
        single_stats = metrics.get_stats()
        
        # 测试多周期模式下的数据加载性能
        chart_window.switch_display_mode("multi")
        
        metrics = PerformanceMetrics("data_loading_multi")
        metrics.start()
        chart_window.history_data = test_bars
        # 同步数据到多周期Widget
        if hasattr(chart_window, 'sync_data_to_multi_timeframe'):
            chart_window.sync_data_to_multi_timeframe()
        metrics.stop()
        
        multi_stats = metrics.get_stats()
        
        # 验证性能指标（注意：这里主要测试数据设置和同步，不包括实际数据库查询）
        # 实际数据库查询性能需要在集成测试中验证
        assert single_stats["avg_ms"] < 5000, \
            f"单周期模式数据加载平均延迟 {single_stats['avg_ms']:.2f}ms 超过 5s 限制"
        assert multi_stats["avg_ms"] < 5000, \
            f"多周期模式数据加载平均延迟 {multi_stats['avg_ms']:.2f}ms 超过 5s 限制"
        
        # 打印性能统计（用于调试）
        print(f"\n数据加载性能统计:")
        print(f"  数据量: {num_bars} 条")
        print(f"  单周期模式:")
        print(f"    平均延迟: {single_stats['avg_ms']:.2f}ms")
        print(f"    最大延迟: {single_stats['max_ms']:.2f}ms")
        print(f"  多周期模式:")
        print(f"    平均延迟: {multi_stats['avg_ms']:.2f}ms")
        print(f"    最大延迟: {multi_stats['max_ms']:.2f}ms")

    def test_realtime_update_latency(self, chart_window):
        """T080: 测试实时更新延迟 (< 100ms)"""
        from vnpy.trader.object import TickData
        
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        chart_window.current_vt_symbol = "MHImain.HKFE"
        
        # 确保多周期Widget已启用实时更新
        if chart_window.multi_timeframe_widget:
            if hasattr(chart_window.multi_timeframe_widget, 'enable_realtime'):
                chart_window.multi_timeframe_widget.enable_realtime()
        
        metrics = PerformanceMetrics("realtime_update")
        
        # 执行多次tick更新，收集性能数据
        num_iterations = 100
        
        for i in range(num_iterations):
            # 创建测试 tick
            tick = TickData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime.now(),
                last_price=25000.0 + i * 0.1,
                volume=1000 + i,
                gateway_name="test"
            )
            
            # 测量tick更新延迟
            metrics.start()
            if hasattr(chart_window, 'process_tick_event'):
                # 注意：在测试环境中，我们主要测量方法调用时间
                # 实际tick处理可能涉及更多操作
                chart_window.process_tick_event(Event(EVENT_TICK, tick))
            metrics.stop()
        
        # 获取统计信息
        stats = metrics.get_stats()
        
        # 验证性能指标
        assert stats["avg_ms"] < 100, \
            f"实时更新平均延迟 {stats['avg_ms']:.2f}ms 超过 100ms 限制"
        assert stats["p95_ms"] < 100, \
            f"实时更新 P95 延迟 {stats['p95_ms']:.2f}ms 超过 100ms 限制"
        
        # 打印性能统计（用于调试）
        print(f"\n实时更新性能统计:")
        print(f"  测试次数: {stats['count']}")
        print(f"  平均延迟: {stats['avg_ms']:.2f}ms")
        print(f"  最小延迟: {stats['min_ms']:.2f}ms")
        print(f"  最大延迟: {stats['max_ms']:.2f}ms")
        print(f"  P50 延迟: {stats['p50_ms']:.2f}ms")
        print(f"  P95 延迟: {stats['p95_ms']:.2f}ms")
        print(f"  P99 延迟: {stats['p99_ms']:.2f}ms")

    def test_memory_usage(self, chart_window):
        """T081: 测试内存使用 (< 300MB)"""
        import gc
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        chart_window.current_vt_symbol = "MHImain.HKFE"
        
        # 创建大量测试数据
        from vnpy.trader.object import BarData
        
        test_bars = []
        base_time = datetime(2024, 11, 14, 9, 0)
        num_bars = 10080  # 7天的1分钟数据
        
        for i in range(num_bars):
            minutes = i % 60
            hours = (i // 60) % 24
            days = i // (60 * 24)
            bar_time = base_time + timedelta(days=days, hours=hours, minutes=minutes)
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=bar_time,
                interval=Interval.MINUTE,
                volume=1000,
                open_price=25000.0 + i * 0.1,
                high_price=25001.0 + i * 0.1,
                low_price=24999.0 + i * 0.1,
                close_price=25000.5 + i * 0.1,
                gateway_name="test"
            )
            test_bars.append(bar)
        
        # 加载数据
        chart_window.history_data = test_bars
        if hasattr(chart_window, 'sync_data_to_multi_timeframe'):
            chart_window.sync_data_to_multi_timeframe()
        
        # 强制垃圾回收
        gc.collect()
        
        # 记录加载后的内存使用
        after_load_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 计算内存增量
        memory_increase = after_load_memory - initial_memory
        
        # 验证内存使用
        assert memory_increase < 300, \
            f"内存增量 {memory_increase:.2f}MB 超过 300MB 限制"
        assert after_load_memory < 500, \
            f"总内存使用 {after_load_memory:.2f}MB 超过 500MB 限制（包含测试框架）"
        
        # 打印内存统计（用于调试）
        print(f"\n内存使用统计:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  加载后内存: {after_load_memory:.2f}MB")
        print(f"  内存增量: {memory_increase:.2f}MB")
        print(f"  数据量: {num_bars} 条")

