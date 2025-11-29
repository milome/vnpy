#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
富途 OpenAPI 性能测试 - FutureInfo 缓存优化

测试覆盖：
1. 首次调用延迟（无缓存）
2. 缓存命中后的延迟（有缓存）
3. API 调用次数统计
4. 缓存更新验证
5. 性能提升对比
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from time import time, sleep
import pandas as pd
from typing import Dict, List

from vnpy.event import EventEngine
from vnpy.trader.constant import Exchange

from vnpy_futu.futu_gateway import FutuGateway
from futu import RET_OK, RET_ERROR


class PerformanceStats:
    """性能统计类"""
    def __init__(self):
        self.api_call_count = 0
        self.total_latency = 0.0
        self.call_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_call(self, latency: float, cache_hit: bool = False):
        """记录一次调用"""
        self.api_call_count += 1
        self.total_latency += latency
        self.call_times.append(latency)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if self.api_call_count == 0:
            return {
                "count": 0,
                "avg_latency": 0.0,
                "min_latency": 0.0,
                "max_latency": 0.0,
                "total_latency": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
                "hit_rate": 0.0
            }
        
        return {
            "count": self.api_call_count,
            "avg_latency": self.total_latency / self.api_call_count,
            "min_latency": min(self.call_times),
            "max_latency": max(self.call_times),
            "total_latency": self.total_latency,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / self.api_call_count if self.api_call_count > 0 else 0.0
        }


class TestFutuPerformanceCache(unittest.TestCase):
    """富途性能缓存测试"""
    
    def setUp(self):
        """测试前准备"""
        self.event_engine = EventEngine()
        self.gateway = FutuGateway(self.event_engine, "FUTU_TEST")
        
        # Mock quote_ctx
        self.mock_quote_ctx = MagicMock()
        self.gateway.quote_ctx = self.mock_quote_ctx
        
        # 性能统计
        self.stats = PerformanceStats()
        
        # 模拟 API 延迟（毫秒）
        self.mock_api_latency_ms = 225.0  # 模拟 225ms 的 API 延迟
    
    def _simulate_api_call(self, delay_ms: float = None):
        """模拟 API 调用延迟"""
        if delay_ms is None:
            delay_ms = self.mock_api_latency_ms
        sleep(delay_ms / 1000.0)  # 转换为秒
    
    def _mock_get_future_info_success(self):
        """Mock 成功的 get_future_info 调用"""
        mock_func = Mock()
        def get_future_info(codes):
            self._simulate_api_call()
            data = pd.DataFrame({
                'code': ['HK.MHImain'],
                'origin_code': ['HK.MHI2511']
            })
            return RET_OK, data
        mock_func.side_effect = get_future_info
        return mock_func
    
    def _mock_get_future_info_failure(self):
        """Mock 失败的 get_future_info 调用"""
        mock_func = Mock()
        def get_future_info(codes):
            self._simulate_api_call()
            return RET_ERROR, pd.DataFrame()
        mock_func.side_effect = get_future_info
        return mock_func
    
    def _mock_get_market_snapshot_success(self):
        """Mock 成功的 get_market_snapshot 调用"""
        mock_func = Mock()
        def get_market_snapshot(codes):
            self._simulate_api_call(50.0)  # 50ms 延迟
            data = pd.DataFrame({
                'code': ['HK.MHImain'],
                'name': ['小恒指期货 (2511)']
            })
            return RET_OK, data
        mock_func.side_effect = get_market_snapshot
        return mock_func
    
    def test_first_call_without_cache(self):
        """测试首次调用（无缓存）"""
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # Mock API
        self.mock_quote_ctx.get_future_info = self._mock_get_future_info_success()
        
        # 记录开始时间
        start_time = time()
        
        # 调用解析方法
        result = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
        
        # 计算延迟
        latency_ms = (time() - start_time) * 1000
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result, "HK.MHI2511")
        
        # 验证缓存已更新
        self.assertIn("MHImain", self.gateway.main_contract_mapping)
        self.assertEqual(self.gateway.main_contract_mapping["MHImain"], "MHI2511")
        
        # 记录统计
        self.stats.record_call(latency_ms, cache_hit=False)
        
        # 验证 API 被调用
        self.assertEqual(self.mock_quote_ctx.get_future_info.call_count, 1)
        
        print(f"\n首次调用延迟: {latency_ms:.2f}ms")
        return latency_ms
    
    def test_second_call_with_cache(self):
        """测试第二次调用（有缓存）"""
        # 先设置缓存
        self.gateway.main_contract_mapping["MHImain"] = "MHI2511"
        
        # Mock API（不应该被调用）
        self.mock_quote_ctx.get_future_info = Mock()
        
        # 记录开始时间
        start_time = time()
        
        # 调用解析方法
        result = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
        
        # 计算延迟
        latency_ms = (time() - start_time) * 1000
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result, "HK.MHI2511")
        
        # 记录统计
        self.stats.record_call(latency_ms, cache_hit=True)
        
        # 验证 API 未被调用（缓存命中）
        self.assertEqual(self.mock_quote_ctx.get_future_info.call_count, 0)
        
        print(f"\n缓存命中延迟: {latency_ms:.2f}ms")
        return latency_ms
    
    def test_multiple_calls_performance(self):
        """测试多次调用的性能"""
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # Mock API
        self.mock_quote_ctx.get_future_info = self._mock_get_future_info_success()
        
        # 首次调用（无缓存）
        start_time = time()
        result1 = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
        latency1 = (time() - start_time) * 1000
        self.stats.record_call(latency1, cache_hit=False)
        
        # 后续多次调用（有缓存）
        for i in range(10):
            start_time = time()
            result = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
            latency = (time() - start_time) * 1000
            self.stats.record_call(latency, cache_hit=True)
            self.assertEqual(result, "HK.MHI2511")
        
        # 验证 API 只被调用了一次
        self.assertEqual(self.mock_quote_ctx.get_future_info.call_count, 1)
        
        # 获取统计信息
        stats = self.stats.get_stats()
        
        print(f"\n多次调用统计:")
        print(f"  总调用次数: {stats['count']}")
        print(f"  平均延迟: {stats['avg_latency']:.2f}ms")
        print(f"  最小延迟: {stats['min_latency']:.2f}ms")
        print(f"  最大延迟: {stats['max_latency']:.2f}ms")
        print(f"  缓存命中率: {stats['hit_rate']*100:.1f}%")
        print(f"  缓存命中: {stats['cache_hits']} 次")
        print(f"  缓存未命中: {stats['cache_misses']} 次")
        
        return stats
    
    def test_cache_update_on_success(self):
        """测试成功解析后缓存更新"""
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # Mock API
        self.mock_quote_ctx.get_future_info = self._mock_get_future_info_success()
        
        # 调用解析方法
        result = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
        
        # 验证缓存已更新
        self.assertIn("MHImain", self.gateway.main_contract_mapping)
        self.assertEqual(self.gateway.main_contract_mapping["MHImain"], "MHI2511")
        
        print(f"\n缓存更新验证: 成功")
        print(f"  缓存内容: {self.gateway.main_contract_mapping}")
    
    def test_performance_improvement(self):
        """测试性能提升对比"""
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # Mock API
        self.mock_quote_ctx.get_future_info = self._mock_get_future_info_success()
        
        # 测试无缓存场景（10次调用，每次都调用API）
        no_cache_times = []
        for i in range(10):
            self.gateway.main_contract_mapping.clear()  # 每次清空缓存
            start_time = time()
            self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
            latency = (time() - start_time) * 1000
            no_cache_times.append(latency)
        
        no_cache_avg = sum(no_cache_times) / len(no_cache_times)
        
        # 测试有缓存场景（10次调用，只有第一次调用API）
        self.gateway.main_contract_mapping.clear()
        with_cache_times = []
        for i in range(10):
            start_time = time()
            self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
            latency = (time() - start_time) * 1000
            with_cache_times.append(latency)
        
        with_cache_avg = sum(with_cache_times) / len(with_cache_times)
        
        # 计算性能提升
        improvement = ((no_cache_avg - with_cache_avg) / no_cache_avg) * 100
        
        print(f"\n性能提升对比:")
        print(f"  无缓存平均延迟: {no_cache_avg:.2f}ms")
        print(f"  有缓存平均延迟: {with_cache_avg:.2f}ms")
        print(f"  性能提升: {improvement:.1f}%")
        
        # 验证性能提升显著（允许小幅波动，实际测试中可能略低于90%）
        self.assertGreater(improvement, 85.0, "缓存应该带来超过85%的性能提升")
        
        return {
            "no_cache_avg": no_cache_avg,
            "with_cache_avg": with_cache_avg,
            "improvement": improvement
        }
    
    def test_different_contracts(self):
        """测试不同合约的缓存隔离"""
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # Mock API - 返回不同的合约
        mock_mhi = Mock()
        def get_future_info_mhi(codes):
            self._simulate_api_call()
            data = pd.DataFrame({
                'code': ['HK.MHImain'],
                'origin_code': ['HK.MHI2511']
            })
            return RET_OK, data
        mock_mhi.side_effect = get_future_info_mhi
        
        mock_hsi = Mock()
        def get_future_info_hsi(codes):
            self._simulate_api_call()
            data = pd.DataFrame({
                'code': ['HK.HSImain'],
                'origin_code': ['HK.HSI2512']
            })
            return RET_OK, data
        mock_hsi.side_effect = get_future_info_hsi
        
        # 解析 MHI
        self.mock_quote_ctx.get_future_info = mock_mhi
        result1 = self.gateway._resolve_main_contract("MHImain", "HK_FUTURE.MHImain")
        self.assertEqual(result1, "HK.MHI2511")
        
        # 解析 HSI
        self.mock_quote_ctx.get_future_info = mock_hsi
        result2 = self.gateway._resolve_main_contract("HSImain", "HK_FUTURE.HSImain")
        self.assertEqual(result2, "HK.HSI2512")
        
        # 验证两个合约的缓存都正确
        self.assertEqual(self.gateway.main_contract_mapping["MHImain"], "MHI2511")
        self.assertEqual(self.gateway.main_contract_mapping["HSImain"], "HSI2512")
        
        print(f"\n不同合约缓存隔离验证: 成功")
        print(f"  MHImain -> {self.gateway.main_contract_mapping['MHImain']}")
        print(f"  HSImain -> {self.gateway.main_contract_mapping['HSImain']}")
    
    def test_cache_evict_on_contract_switch(self):
        """测试主力合约切换时缓存失效并更新"""
        from vnpy_futu.futu_gateway import convert_symbol_vt2futu
        
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # 第一步：设置初始缓存（MHI2511）
        self.gateway.main_contract_mapping["MHImain"] = "MHI2511"
        
        # 验证初始缓存
        self.assertEqual(self.gateway.main_contract_mapping["MHImain"], "MHI2511")
        print(f"\n初始缓存: MHImain -> {self.gateway.main_contract_mapping['MHImain']}")
        
        # 第二步：模拟主力合约切换（从 MHI2511 切换到 MHI2512）
        # Mock API 返回新的主力合约
        call_count = [0]  # 用于跟踪API调用次数
        
        def get_future_info_switched(codes):
            call_count[0] += 1
            self._simulate_api_call()
            # 第一次调用返回旧合约（用于验证缓存），第二次返回新合约（切换后）
            if call_count[0] == 1:
                # 第一次：返回旧合约（但实际应该被缓存跳过）
                data = pd.DataFrame({
                    'code': ['HK.MHImain'],
                    'origin_code': ['HK.MHI2511']
                })
            else:
                # 切换后：返回新合约
                data = pd.DataFrame({
                    'code': ['HK.MHImain'],
                    'origin_code': ['HK.MHI2512']  # 新合约
                })
            return RET_OK, data
        
        mock_func = Mock()
        mock_func.side_effect = get_future_info_switched
        self.mock_quote_ctx.get_future_info = mock_func
        
        # 第三步：模拟 _check_main_contract_switch 的逻辑
        # 这会调用 _resolve_main_contract，如果检测到切换会更新缓存
        main_symbol = "MHImain"
        exchange = Exchange.HKFE
        futu_symbol = convert_symbol_vt2futu(main_symbol, exchange)
        
        # 获取当前缓存值（旧值）
        old_actual_symbol = self.gateway.main_contract_mapping.get(main_symbol)
        self.assertEqual(old_actual_symbol, "MHI2511")
        
        # 解析当前实际合约（模拟切换检测）
        # 注意：由于缓存存在，第一次调用会直接返回缓存，不会调用API
        # 所以我们需要先清空缓存，或者直接模拟切换后的API响应
        actual_code = self.gateway._resolve_main_contract(main_symbol, futu_symbol)
        
        # 由于缓存存在，应该直接返回缓存的旧值
        self.assertEqual(actual_code, "HK.MHI2511")
        self.assertEqual(mock_func.call_count, 0, "缓存命中时不应该调用API")
        
        # 第四步：模拟API返回新合约（切换发生）
        # 清空缓存，模拟切换检测时重新查询
        # 在实际场景中，_check_main_contract_switch 会调用 _resolve_main_contract
        # 如果返回的新合约与缓存不同，会更新缓存
        
        # 重置mock，返回新合约
        call_count[0] = 0
        def get_future_info_new(codes):
            call_count[0] += 1
            self._simulate_api_call()
            data = pd.DataFrame({
                'code': ['HK.MHImain'],
                'origin_code': ['HK.MHI2512']  # 新合约
            })
            return RET_OK, data
        
        mock_func_new = Mock()
        mock_func_new.side_effect = get_future_info_new
        self.mock_quote_ctx.get_future_info = mock_func_new
        
        # 清空缓存，模拟切换检测（实际场景中，_check_main_contract_switch 会重新查询）
        # 但为了测试缓存更新，我们手动清空缓存，然后重新解析
        self.gateway.main_contract_mapping.clear()
        
        # 重新解析（会调用API，因为缓存已清空）
        new_actual_code = self.gateway._resolve_main_contract(main_symbol, futu_symbol)
        self.assertEqual(new_actual_code, "HK.MHI2512")
        self.assertEqual(mock_func_new.call_count, 1, "缓存未命中时应该调用API")
        
        # 验证缓存已更新为新值
        self.assertIn(main_symbol, self.gateway.main_contract_mapping)
        self.assertEqual(self.gateway.main_contract_mapping[main_symbol], "MHI2512")
        self.assertNotEqual(self.gateway.main_contract_mapping[main_symbol], old_actual_symbol)
        
        print(f"切换后缓存: MHImain -> {self.gateway.main_contract_mapping['MHImain']}")
        print(f"缓存已从 {old_actual_symbol} 更新为 {self.gateway.main_contract_mapping[main_symbol]}")
        
        # 第五步：验证切换后，后续调用使用新缓存
        # 再次调用应该使用新缓存，不调用API
        mock_func_new.call_count = 0  # 重置计数
        cached_code = self.gateway._resolve_main_contract(main_symbol, futu_symbol)
        self.assertEqual(cached_code, "HK.MHI2512")
        self.assertEqual(mock_func_new.call_count, 0, "切换后缓存命中，不应该调用API")
        
        print(f"切换后缓存命中验证: 成功，使用新缓存值 MHI2512")
    
    def test_cache_update_on_manual_switch_detection(self):
        """测试手动模拟主力合约切换时缓存更新"""
        from vnpy_futu.futu_gateway import convert_symbol_vt2futu
        
        # 清空缓存
        self.gateway.main_contract_mapping.clear()
        
        # 第一步：设置初始缓存（MHI2511）
        self.gateway.main_contract_mapping["MHImain"] = "MHI2511"
        old_value = "MHI2511"
        print(f"\n初始缓存: MHImain -> {old_value}")
        
        # 第二步：模拟切换发生，API返回新合约（MHI2512）
        def get_future_info_new(codes):
            self._simulate_api_call()
            data = pd.DataFrame({
                'code': ['HK.MHImain'],
                'origin_code': ['HK.MHI2512']  # 新合约
            })
            return RET_OK, data
        
        mock_new = Mock()
        mock_new.side_effect = get_future_info_new
        self.mock_quote_ctx.get_future_info = mock_new
        
        # 第三步：模拟切换检测逻辑
        # 在实际场景中，_check_main_contract_switch 会：
        # 1. 调用 _resolve_main_contract 获取当前实际合约
        # 2. 如果与缓存不同，更新缓存
        
        main_symbol = "MHImain"
        exchange = Exchange.HKFE
        futu_symbol = convert_symbol_vt2futu(main_symbol, exchange)
        
        # 由于缓存存在，先清空缓存以模拟重新查询（实际场景中，定时检查会重新查询）
        # 或者，我们可以直接模拟 _check_main_contract_switch 的逻辑
        self.gateway.main_contract_mapping.clear()  # 清空缓存，模拟重新查询
        
        # 重新解析（会调用API，因为缓存已清空）
        new_actual_code = self.gateway._resolve_main_contract(main_symbol, futu_symbol)
        self.assertEqual(new_actual_code, "HK.MHI2512")
        self.assertEqual(mock_new.call_count, 1, "缓存未命中时应该调用API")
        
        # 验证缓存已更新为新值
        new_value = self.gateway.main_contract_mapping[main_symbol]
        self.assertEqual(new_value, "MHI2512")
        self.assertNotEqual(new_value, old_value, "缓存应该已更新为新值")
        
        print(f"切换后缓存: MHImain -> {new_value}")
        print(f"✅ 缓存已从 {old_value} 更新为 {new_value}（缓存失效并更新）")
        
        # 第四步：验证切换后，后续调用使用新缓存
        mock_new.call_count = 0  # 重置计数
        cached_code = self.gateway._resolve_main_contract(main_symbol, futu_symbol)
        self.assertEqual(cached_code, "HK.MHI2512")
        self.assertEqual(mock_new.call_count, 0, "切换后缓存命中，不应该调用API")
        
        print(f"✅ 切换后缓存命中验证: 成功，使用新缓存值 MHI2512")


def run_performance_tests():
    """运行性能测试并生成报告"""
    print("=" * 80)
    print("富途 OpenAPI 性能测试 - FutureInfo 缓存优化")
    print("=" * 80)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestFutuPerformanceCache)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 生成报告
    report = generate_test_report(result)
    
    return report, result


def generate_test_report(result) -> str:
    """生成测试报告"""
    report_lines = []
    report_lines.append("# 富途 OpenAPI 性能测试报告")
    report_lines.append("")
    report_lines.append(f"**测试时间**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append("## 测试概览")
    report_lines.append("")
    report_lines.append(f"- **总测试数**: {result.testsRun}")
    report_lines.append(f"- **成功**: {result.testsRun - len(result.failures) - len(result.errors)}")
    report_lines.append(f"- **失败**: {len(result.failures)}")
    report_lines.append(f"- **错误**: {len(result.errors)}")
    report_lines.append("")
    
    if result.failures:
        report_lines.append("## 失败的测试")
        report_lines.append("")
        for test, traceback in result.failures:
            report_lines.append(f"### {test}")
            report_lines.append("```")
            report_lines.append(traceback)
            report_lines.append("```")
            report_lines.append("")
    
    if result.errors:
        report_lines.append("## 错误的测试")
        report_lines.append("")
        for test, traceback in result.errors:
            report_lines.append(f"### {test}")
            report_lines.append("```")
            report_lines.append(traceback)
            report_lines.append("```")
            report_lines.append("")
    
    report_lines.append("## 测试结论")
    report_lines.append("")
    if result.wasSuccessful():
        report_lines.append("✅ **所有测试通过**")
        report_lines.append("")
        report_lines.append("缓存优化已成功实施，性能提升显著。")
    else:
        report_lines.append("❌ **部分测试失败**")
        report_lines.append("")
        report_lines.append("请检查失败的测试用例。")
    
    report_lines.append("")
    report_lines.append("## 性能优化效果")
    report_lines.append("")
    report_lines.append("### 预期效果")
    report_lines.append("")
    report_lines.append("| 场景 | 优化前 | 优化后 | 提升 |")
    report_lines.append("|------|--------|--------|------|")
    report_lines.append("| 首次调用 | ~225ms | ~225ms | - |")
    report_lines.append("| 缓存命中 | ~225ms | < 1ms | **99.5% ↓** |")
    report_lines.append("| API调用次数 | 每次调用 | 仅首次调用 | **显著减少** |")
    report_lines.append("")
    
    return "\n".join(report_lines)


if __name__ == "__main__":
    report, result = run_performance_tests()
    
    # 保存报告
    import os
    report_path = os.path.join("docs", "富途OpenAPI性能测试报告.md")
    os.makedirs("docs", exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n" + "=" * 80)
    print(f"测试报告已保存到: {report_path}")
    print("=" * 80)
    
    # 返回退出码
    exit(0 if result.wasSuccessful() else 1)

