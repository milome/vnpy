"""
配置管理模块
管理系统配置参数和设置
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from vnpy.trader.constant import Exchange, Interval


@dataclass
class DataConfig:
    """数据配置"""
    source: str = "futu"  # 数据源: futu, rqdata, local
    host: str = "127.0.0.1"
    port: int = 11111
    cache_dir: str = "./data"
    compress: bool = True
    validate: bool = True


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str = "MHITrendStrategy"
    fast_window: int = 12
    slow_window: int = 26
    atr_window: int = 20
    atr_multiplier: float = 2.5
    max_daily_trades: int = 10
    max_consecutive_losses: int = 3


@dataclass
class BacktestConfig:
    """回测配置"""
    symbol: str = "MHImain"
    exchange: Exchange = Exchange.HKFE
    interval: Interval = Interval.MINUTE
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003  # 0.03%
    slippage: float = 1.0  # 1港币
    contract_size: int = 10  # 合约乘数
    price_tick: float = 1.0  # 最小价格变动


@dataclass
class OptimizationConfig:
    """优化配置"""
    method: str = "grid_search"  # grid_search, genetic, bayesian
    target_metric: str = "sharpe_ratio"
    max_workers: int = 4
    param_ranges: Dict[str, list] = None
    
    def __post_init__(self):
        if self.param_ranges is None:
            self.param_ranges = {
                'fast_window': [5, 10, 15, 20],
                'slow_window': [20, 30, 40, 50],
                'atr_multiplier': [1.5, 2.0, 2.5, 3.0]
            }


@dataclass
class ReportConfig:
    """报告配置"""
    output_dir: str = "./reports"
    format: str = "html"  # html, pdf, json
    include_charts: bool = True
    chart_style: str = "seaborn"
    language: str = "zh"  # zh, en


class Config:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化配置管理器"""
        self.config_file = config_file or "mhi_backtest_config.json"
        
        # 默认配置
        self.data = DataConfig()
        self.strategy = StrategyConfig()
        self.backtest = BacktestConfig()
        self.optimization = OptimizationConfig()
        self.report = ReportConfig()
        
        # 加载配置文件
        self.load()
    
    def load(self) -> None:
        """从文件加载配置"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置
                if 'data' in config_data:
                    self.data = DataConfig(**config_data['data'])
                if 'strategy' in config_data:
                    self.strategy = StrategyConfig(**config_data['strategy'])
                if 'backtest' in config_data:
                    # 处理Exchange和Interval枚举
                    backtest_data = config_data['backtest'].copy()
                    if 'exchange' in backtest_data:
                        backtest_data['exchange'] = Exchange[backtest_data['exchange']]
                    if 'interval' in backtest_data:
                        backtest_data['interval'] = Interval[backtest_data['interval']]
                    self.backtest = BacktestConfig(**backtest_data)
                if 'optimization' in config_data:
                    self.optimization = OptimizationConfig(**config_data['optimization'])
                if 'report' in config_data:
                    self.report = ReportConfig(**config_data['report'])
                    
                print(f"配置已从 {self.config_file} 加载")
                
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                print("使用默认配置")
        else:
            print(f"配置文件 {self.config_file} 不存在，使用默认配置")
            self.save()  # 保存默认配置
    
    def save(self) -> None:
        """保存配置到文件"""
        config_data = {
            'data': asdict(self.data),
            'strategy': asdict(self.strategy),
            'backtest': self._serialize_backtest_config(),
            'optimization': asdict(self.optimization),
            'report': asdict(self.report)
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到 {self.config_file}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _serialize_backtest_config(self) -> Dict[str, Any]:
        """序列化回测配置（处理枚举类型）"""
        data = asdict(self.backtest)
        data['exchange'] = self.backtest.exchange.name
        data['interval'] = self.backtest.interval.name
        return data
    
    def update_strategy_params(self, **kwargs) -> None:
        """更新策略参数"""
        for key, value in kwargs.items():
            if hasattr(self.strategy, key):
                setattr(self.strategy, key, value)
            else:
                print(f"警告: 策略参数 {key} 不存在")
    
    def update_backtest_params(self, **kwargs) -> None:
        """更新回测参数"""
        for key, value in kwargs.items():
            if hasattr(self.backtest, key):
                setattr(self.backtest, key, value)
            else:
                print(f"警告: 回测参数 {key} 不存在")
    
    def get_strategy_dict(self) -> Dict[str, Any]:
        """获取策略参数字典"""
        return asdict(self.strategy)
    
    def get_backtest_dict(self) -> Dict[str, Any]:
        """获取回测参数字典"""
        return self._serialize_backtest_config()
    
    def validate(self) -> bool:
        """验证配置有效性"""
        errors = []
        
        # 验证日期格式
        try:
            datetime.strptime(self.backtest.start_date, "%Y-%m-%d")
            datetime.strptime(self.backtest.end_date, "%Y-%m-%d")
        except ValueError:
            errors.append("日期格式错误，应为 YYYY-MM-DD")
        
        # 验证数值范围
        if self.backtest.initial_capital <= 0:
            errors.append("初始资金必须大于0")
        
        if self.backtest.commission_rate < 0:
            errors.append("手续费率不能为负数")
        
        if self.strategy.fast_window >= self.strategy.slow_window:
            errors.append("快速均线周期必须小于慢速均线周期")
        
        if self.strategy.atr_multiplier <= 0:
            errors.append("ATR倍数必须大于0")
        
        # 验证目录存在性
        data_dir = Path(self.data.cache_dir)
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                errors.append(f"无法创建数据目录: {self.data.cache_dir}")
        
        report_dir = Path(self.report.output_dir)
        if not report_dir.exists():
            try:
                report_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                errors.append(f"无法创建报告目录: {self.report.output_dir}")
        
        if errors:
            print("配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("配置验证通过")
        return True
    
    def create_preset_configs(self) -> Dict[str, 'Config']:
        """创建预设配置"""
        presets = {}
        
        # 保守型配置
        conservative = Config()
        conservative.strategy.fast_window = 10
        conservative.strategy.slow_window = 20
        conservative.strategy.atr_multiplier = 3.0
        conservative.strategy.max_daily_trades = 5
        presets['conservative'] = conservative
        
        # 平衡型配置（默认）
        balanced = Config()
        presets['balanced'] = balanced
        
        # 激进型配置
        aggressive = Config()
        aggressive.strategy.fast_window = 8
        aggressive.strategy.slow_window = 18
        aggressive.strategy.atr_multiplier = 2.0
        aggressive.strategy.max_daily_trades = 20
        presets['aggressive'] = aggressive
        
        # 剥头皮配置
        scalping = Config()
        scalping.strategy.fast_window = 5
        scalping.strategy.slow_window = 12
        scalping.strategy.atr_multiplier = 1.5
        scalping.strategy.max_daily_trades = 50
        scalping.backtest.interval = Interval.MINUTE
        presets['scalping'] = scalping
        
        return presets
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"""
MHI回测系统配置:
数据源: {self.data.source}
策略: {self.strategy.name}
回测周期: {self.backtest.start_date} 至 {self.backtest.end_date}
初始资金: {self.backtest.initial_capital:,.0f}
快慢均线: {self.strategy.fast_window}/{self.strategy.slow_window}
ATR倍数: {self.strategy.atr_multiplier}
"""


# 全局配置实例
config = Config()


def load_config(config_file: str) -> Config:
    """加载指定配置文件"""
    return Config(config_file)


def create_default_config() -> None:
    """创建默认配置文件"""
    default_config = Config()
    default_config.save()
    print("默认配置文件已创建")


if __name__ == "__main__":
    # 测试配置管理
    test_config = Config()
    print(test_config)
    
    # 验证配置
    test_config.validate()
    
    # 创建预设配置
    presets = test_config.create_preset_configs()
    for name, preset in presets.items():
        print(f"\n{name.upper()}配置:")
        print(f"快慢均线: {preset.strategy.fast_window}/{preset.strategy.slow_window}")
        print(f"ATR倍数: {preset.strategy.atr_multiplier}")
        print(f"最大交易: {preset.strategy.max_daily_trades}")
