#!/usr/bin/env python3
"""
MHI CTA回测系统测试用例 (TDD)
遵循测试驱动开发原则，先编写测试用例，再实现功能
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vnpy.trader.constant import Exchange, Interval, Direction
from vnpy.trader.object import BarData, TickData, TradeData, OrderData


class TestDataFetcher:
    """数据获取模块测试"""
    
    def test_fetch_mhi_history_data_success(self):
        """测试成功获取MHI历史数据"""
        # 这个测试定义了DataFetcher应该如何工作
        from mhi_cta_backtest.data.fetcher import DataFetcher
        
        fetcher = DataFetcher()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # 模拟数据获取
        with patch.object(fetcher, '_fetch_from_futu') as mock_fetch:
            mock_data = pd.DataFrame({
                'datetime': pd.date_range(start_date, end_date, freq='1min'),
                'open': [25000] * 44640,  # 31天 * 24小时 * 60分钟
                'high': [25100] * 44640,
                'low': [24900] * 44640,
                'close': [25050] * 44640,
                'volume': [100] * 44640
            })
            mock_fetch.return_value = mock_data
            
            result = fetcher.fetch_history_data(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                start=start_date,
                end=end_date,
                interval=Interval.MINUTE
            )
            
            assert len(result) == 44640
            assert result['symbol'].iloc[0] == "MHImain"
            assert result['exchange'].iloc[0] == Exchange.HKFE
    
    def test_fetch_data_validation(self):
        """测试数据验证功能"""
        from mhi_cta_backtest.data.fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 测试无效数据检测
        invalid_data = pd.DataFrame({
            'datetime': [datetime.now()],
            'open': [-100],  # 负价格
            'high': [0],     # 零价格
            'low': [200],    # low > high
            'close': [150],
            'volume': [-50]  # 负成交量
        })
        
        with pytest.raises(ValueError, match="数据验证失败"):
            fetcher.validate_data(invalid_data)
    
    def test_data_source_fallback(self):
        """测试数据源故障转移"""
        from mhi_cta_backtest.data.fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 模拟主数据源失败，备用数据源成功
        with patch.object(fetcher, '_fetch_from_futu', side_effect=Exception("连接失败")):
            with patch.object(fetcher, '_fetch_from_local') as mock_local:
                mock_local.return_value = pd.DataFrame({
                    'datetime': [datetime.now()],
                    'open': [25000], 'high': [25100], 'low': [24900], 
                    'close': [25050], 'volume': [100]
                })
                
                result = fetcher.fetch_history_data("MHImain", Exchange.HKFE, 
                                                  datetime.now(), datetime.now())
                assert len(result) == 1


class TestDataStorage:
    """数据存储模块测试"""
    
    def test_save_and_load_bar_data(self):
        """测试K线数据保存和加载"""
        from mhi_cta_backtest.data.storage import DataStorage
        
        storage = DataStorage("./test_data")
        
        # 创建测试数据
        test_bars = [
            BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2024, 1, 1, 9, 30),
                interval=Interval.MINUTE,
                volume=100,
                open_price=25000,
                high_price=25100,
                low_price=24900,
                close_price=25050,
                gateway_name="test"
            )
        ]
        
        # 保存数据
        storage.save_bars(test_bars)
        
        # 加载数据
        loaded_bars = storage.load_bars(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2)
        )
        
        assert len(loaded_bars) == 1
        assert loaded_bars[0].symbol == "MHImain"
        assert loaded_bars[0].close_price == 25050
    
    def test_data_compression(self):
        """测试数据压缩功能"""
        from mhi_cta_backtest.data.storage import DataStorage
        
        storage = DataStorage("./test_data")
        
        # 创建大量测试数据
        large_dataset = []
        for i in range(10000):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2024, 1, 1) + timedelta(minutes=i),
                interval=Interval.MINUTE,
                volume=100,
                open_price=25000 + i,
                high_price=25100 + i,
                low_price=24900 + i,
                close_price=25050 + i,
                gateway_name="test"
            )
            large_dataset.append(bar)
        
        # 保存并检查压缩效果
        storage.save_bars(large_dataset, compress=True)
        file_size = storage.get_file_size("MHImain", Exchange.HKFE)
        
        # 压缩后文件大小应该合理
        assert file_size < 1024 * 1024  # 小于1MB


class TestMHIStrategy:
    """MHI策略测试"""
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        from mhi_cta_backtest.strategy.mhi_trend import MHITrendStrategy
        
        strategy = MHITrendStrategy()
        strategy.on_init()
        
        assert strategy.fast_window > 0
        assert strategy.slow_window > strategy.fast_window
        assert strategy.atr_window > 0
        assert strategy.atr_multiplier > 0
    
    def test_strategy_signal_generation(self):
        """测试策略信号生成"""
        from mhi_cta_backtest.strategy.mhi_trend import MHITrendStrategy
        
        strategy = MHITrendStrategy()
        strategy.on_init()
        
        # 模拟上升趋势数据
        for i in range(50):
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2024, 1, 1) + timedelta(minutes=i),
                interval=Interval.MINUTE,
                volume=100,
                open_price=25000 + i * 10,
                high_price=25100 + i * 10,
                low_price=24900 + i * 10,
                close_price=25050 + i * 10,
                gateway_name="test"
            )
            strategy.on_bar(bar)
        
        # 检查是否生成了买入信号
        assert strategy.pos > 0  # 应该有多头持仓
    
    def test_strategy_risk_management(self):
        """测试策略风险管理"""
        from mhi_cta_backtest.strategy.mhi_trend import MHITrendStrategy
        
        strategy = MHITrendStrategy()
        strategy.max_daily_trades = 5
        strategy.on_init()
        
        # 模拟频繁交易场景
        for i in range(10):
            # 模拟震荡行情，触发频繁交易
            direction = 1 if i % 2 == 0 else -1
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=datetime(2024, 1, 1) + timedelta(minutes=i),
                interval=Interval.MINUTE,
                volume=100,
                open_price=25000 + direction * 50,
                high_price=25100 + direction * 50,
                low_price=24900 + direction * 50,
                close_price=25050 + direction * 50,
                gateway_name="test"
            )
            strategy.on_bar(bar)
        
        # 检查是否限制了交易次数
        assert strategy.daily_trade_count <= strategy.max_daily_trades


class TestBacktestEngine:
    """回测引擎测试"""
    
    def test_backtest_engine_initialization(self):
        """测试回测引擎初始化"""
        from mhi_cta_backtest.engine.backtest import BacktestEngine
        
        engine = BacktestEngine()
        engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            rate=0.0003,  # 手续费
            slippage=1,   # 滑点
            size=10,      # 合约乘数
            pricetick=1,  # 最小价格变动
            capital=100000  # 初始资金
        )
        
        assert engine.vt_symbol == "MHImain.HKFE"
        assert engine.capital == 100000
        assert engine.rate == 0.0003
    
    def test_backtest_execution(self):
        """测试回测执行"""
        from mhi_cta_backtest.engine.backtest import BacktestEngine
        from mhi_cta_backtest.strategy.mhi_trend import MHITrendStrategy
        
        engine = BacktestEngine()
        engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
            rate=0.0003,
            slippage=1,
            size=10,
            pricetick=1,
            capital=100000
        )
        
        # 添加策略
        engine.add_strategy(MHITrendStrategy, {})
        
        # 模拟数据加载
        with patch.object(engine, 'load_data') as mock_load:
            mock_load.return_value = True
            
            # 执行回测
            result = engine.run_backtesting()
            
            assert result is not None
            assert hasattr(result, 'total_return')
            assert hasattr(result, 'sharpe_ratio')
            assert hasattr(result, 'max_drawdown')
    
    def test_transaction_cost_calculation(self):
        """测试交易成本计算"""
        from mhi_cta_backtest.engine.backtest import BacktestEngine
        
        engine = BacktestEngine()
        engine.rate = 0.0003  # 0.03%手续费
        engine.slippage = 1   # 1港币滑点
        engine.size = 10      # 合约乘数
        
        # 测试买入成本
        buy_cost = engine.calculate_transaction_cost(
            price=25000,
            volume=1,
            direction=Direction.LONG
        )
        
        expected_commission = 25000 * 1 * 10 * 0.0003  # 75港币
        expected_slippage = 1 * 1 * 10  # 10港币
        expected_total = expected_commission + expected_slippage  # 85港币
        
        assert abs(buy_cost - expected_total) < 0.01


class TestParameterOptimizer:
    """参数优化器测试"""
    
    def test_grid_search_optimization(self):
        """测试网格搜索优化"""
        from mhi_cta_backtest.optimizer.grid_search import GridSearchOptimizer
        
        optimizer = GridSearchOptimizer()
        
        # 定义参数空间
        param_space = {
            'fast_window': [5, 10, 15],
            'slow_window': [20, 30, 40],
            'atr_multiplier': [1.5, 2.0, 2.5]
        }
        
        # 模拟优化过程
        with patch.object(optimizer, '_run_single_backtest') as mock_backtest:
            mock_backtest.return_value = {
                'total_return': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': 0.08
            }
            
            results = optimizer.optimize(param_space, target='sharpe_ratio')
            
            assert len(results) == 3 * 3 * 3  # 27种组合
            assert 'best_params' in results
            assert 'best_score' in results
    
    def test_walk_forward_analysis(self):
        """测试滚动窗口分析"""
        from mhi_cta_backtest.optimizer.walk_forward import WalkForwardAnalyzer
        
        analyzer = WalkForwardAnalyzer()
        
        # 设置滚动窗口参数
        analyzer.set_parameters(
            train_period=90,  # 90天训练期
            test_period=30,   # 30天测试期
            step=30          # 30天步长
        )
        
        # 模拟滚动分析
        with patch.object(analyzer, '_optimize_period') as mock_optimize:
            mock_optimize.return_value = {'fast_window': 10, 'slow_window': 30}
            
            with patch.object(analyzer, '_test_period') as mock_test:
                mock_test.return_value = {'return': 0.05, 'sharpe': 0.8}
                
                results = analyzer.analyze(
                    start=datetime(2024, 1, 1),
                    end=datetime(2024, 12, 31)
                )
                
                assert len(results) > 0
                assert 'periods' in results
                assert 'stability' in results


class TestPerformanceAnalyzer:
    """性能分析器测试"""
    
    def test_calculate_performance_metrics(self):
        """测试性能指标计算"""
        from mhi_cta_backtest.analyzer.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer()
        
        # 创建模拟交易记录
        trades = [
            {'datetime': datetime(2024, 1, 1), 'pnl': 100, 'return': 0.001},
            {'datetime': datetime(2024, 1, 2), 'pnl': -50, 'return': -0.0005},
            {'datetime': datetime(2024, 1, 3), 'pnl': 200, 'return': 0.002},
            {'datetime': datetime(2024, 1, 4), 'pnl': -30, 'return': -0.0003},
            {'datetime': datetime(2024, 1, 5), 'pnl': 150, 'return': 0.0015},
        ]
        
        metrics = analyzer.calculate_metrics(trades)
        
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        assert 'profit_loss_ratio' in metrics
        
        # 验证计算结果
        assert metrics['total_return'] > 0
        assert metrics['win_rate'] == 0.6  # 3胜2负
    
    def test_risk_metrics_calculation(self):
        """测试风险指标计算"""
        from mhi_cta_backtest.analyzer.performance import PerformanceAnalyzer
        
        analyzer = PerformanceAnalyzer()
        
        # 创建净值曲线数据
        equity_curve = pd.Series([
            100000, 100100, 100050, 100250, 100220, 100370,
            100340, 100290, 100440, 100410, 100560
        ])
        
        risk_metrics = analyzer.calculate_risk_metrics(equity_curve)
        
        assert 'volatility' in risk_metrics
        assert 'var_95' in risk_metrics  # 95% VaR
        assert 'cvar_95' in risk_metrics  # 95% CVaR
        assert 'calmar_ratio' in risk_metrics
        
        assert risk_metrics['volatility'] > 0
        assert risk_metrics['var_95'] < 0  # VaR应为负值


class TestReportGenerator:
    """报告生成器测试"""
    
    def test_generate_html_report(self):
        """测试HTML报告生成"""
        from mhi_cta_backtest.report.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # 模拟回测结果
        backtest_results = {
            'strategy_name': 'MHI趋势策略',
            'period': '2024-01-01 to 2024-01-31',
            'total_return': 0.15,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.08,
            'win_rate': 0.65,
            'total_trades': 25
        }
        
        # 生成报告
        report_path = generator.generate_html_report(
            results=backtest_results,
            output_dir="./test_reports"
        )
        
        assert Path(report_path).exists()
        assert Path(report_path).suffix == '.html'
        
        # 检查报告内容
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'MHI趋势策略' in content
            assert '15.0%' in content  # 总收益率
            assert '1.2' in content    # 夏普比率
    
    def test_generate_charts(self):
        """测试图表生成"""
        from mhi_cta_backtest.report.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        # 模拟净值曲线数据
        equity_data = pd.DataFrame({
            'datetime': pd.date_range('2024-01-01', periods=30, freq='D'),
            'equity': [100000 + i * 500 + (i % 5 - 2) * 200 for i in range(30)]
        })
        
        # 生成图表
        chart_paths = generator.generate_charts(
            equity_data=equity_data,
            output_dir="./test_charts"
        )
        
        assert 'equity_curve' in chart_paths
        assert 'drawdown_curve' in chart_paths
        assert Path(chart_paths['equity_curve']).exists()
        assert Path(chart_paths['drawdown_curve']).exists()


class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_backtest(self):
        """端到端回测测试"""
        from mhi_cta_backtest.main import MHIBacktestSystem
        
        system = MHIBacktestSystem()
        
        # 配置系统
        config = {
            'data_source': 'mock',
            'strategy': 'MHITrendStrategy',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'initial_capital': 100000,
            'commission_rate': 0.0003,
            'slippage': 1
        }
        
        # 执行完整流程
        with patch.object(system.data_fetcher, 'fetch_history_data') as mock_fetch:
            # 模拟数据
            mock_data = self._create_mock_data()
            mock_fetch.return_value = mock_data
            
            # 运行回测
            results = system.run_backtest(config)
            
            # 验证结果
            assert results is not None
            assert 'performance_metrics' in results
            assert 'trade_list' in results
            assert 'equity_curve' in results
            assert 'report_path' in results
            
            # 验证报告文件存在
            assert Path(results['report_path']).exists()
    
    def _create_mock_data(self):
        """创建模拟数据"""
        dates = pd.date_range('2024-01-01', '2024-01-31', freq='1min')
        data = []
        
        base_price = 25000
        for i, dt in enumerate(dates):
            # 模拟价格波动
            price_change = (i % 100 - 50) * 2
            open_price = base_price + price_change
            high_price = open_price + abs(price_change) * 0.5
            low_price = open_price - abs(price_change) * 0.5
            close_price = open_price + price_change * 0.3
            
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=dt,
                interval=Interval.MINUTE,
                volume=100,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                gateway_name="mock"
            )
            data.append(bar)
        
        return data


# 性能测试
class TestPerformance:
    """性能测试"""
    
    @pytest.mark.benchmark
    def test_large_dataset_processing(self, benchmark):
        """测试大数据集处理性能"""
        from mhi_cta_backtest.data.storage import DataStorage
        
        storage = DataStorage("./test_data")
        
        # 创建大数据集（1年分钟数据）
        large_dataset = []
        start_date = datetime(2024, 1, 1)
        
        for i in range(365 * 24 * 60):  # 约52万条数据
            bar = BarData(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                datetime=start_date + timedelta(minutes=i),
                interval=Interval.MINUTE,
                volume=100,
                open_price=25000,
                high_price=25100,
                low_price=24900,
                close_price=25050,
                gateway_name="test"
            )
            large_dataset.append(bar)
        
        # 基准测试数据保存性能
        result = benchmark(storage.save_bars, large_dataset)
        
        # 验证性能要求（应在5秒内完成）
        assert benchmark.stats['mean'] < 5.0
    
    @pytest.mark.benchmark  
    def test_backtest_performance(self, benchmark):
        """测试回测性能"""
        from mhi_cta_backtest.engine.backtest import BacktestEngine
        from mhi_cta_backtest.strategy.mhi_trend import MHITrendStrategy
        
        engine = BacktestEngine()
        engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 1, 1),
            end=datetime(2024, 3, 31),  # 3个月数据
            rate=0.0003,
            slippage=1,
            size=10,
            pricetick=1,
            capital=100000
        )
        
        engine.add_strategy(MHITrendStrategy, {})
        
        # 模拟数据加载
        with patch.object(engine, 'load_data', return_value=True):
            # 基准测试回测性能
            result = benchmark(engine.run_backtesting)
            
            # 验证性能要求（应在30秒内完成）
            assert benchmark.stats['mean'] < 30.0


if __name__ == "__main__":
    # 运行测试
    pytest.main([
        __file__,
        "-v",
        "--cov=mhi_cta_backtest",
        "--cov-report=html",
        "--benchmark-only",
        "--benchmark-sort=mean"
    ])
