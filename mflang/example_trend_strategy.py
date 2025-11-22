#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势判断策略示例
从数据库或parquet文件加载5分钟K线数据，通过#IMPORT引用跨周期数据
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from mflang import ImportParser, REF, CrossPeriodDataManager, ImportResolver
from mflang.import_parser import ImportStatement, PeriodType


class DataLoader:
    """数据加载器 - 从数据库或parquet文件加载K线数据"""
    
    @staticmethod
    def load_from_parquet(file_path: str, symbol: str = None) -> pd.DataFrame:
        """
        从parquet文件加载K线数据
        
        参数:
            file_path: parquet文件路径
            symbol: 合约代码（可选，如果文件包含多个合约）
            
        返回:
            DataFrame，包含datetime, open, high, low, close, volume等列
        """
        df = pd.read_parquet(file_path)
        
        # 确保datetime列存在
        if 'datetime' not in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['time'])
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 如果指定了symbol，进行过滤
        if symbol and 'symbol' in df.columns:
            df = df[df['symbol'] == symbol]
        
        # 按时间排序
        df = df.sort_values('datetime').reset_index(drop=True)
        
        return df
    
    @staticmethod
    def load_from_database(
        connection_string: str,
        table_name: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "5m"
    ) -> pd.DataFrame:
        """
        从数据库加载K线数据
        
        参数:
            connection_string: 数据库连接字符串
            table_name: 表名
            symbol: 合约代码
            start_time: 开始时间
            end_time: 结束时间
            interval: 周期（如"5m"表示5分钟）
            
        返回:
            DataFrame，包含datetime, open, high, low, close, volume等列
        """
        # 这里使用pandas的read_sql作为示例
        # 实际使用时需要根据数据库类型调整
        import sqlalchemy
        
        engine = sqlalchemy.create_engine(connection_string)
        
        query = f"""
        SELECT datetime, open, high, low, close, volume
        FROM {table_name}
        WHERE symbol = '{symbol}'
        AND datetime >= '{start_time}'
        AND datetime <= '{end_time}'
        AND interval = '{interval}'
        ORDER BY datetime
        """
        
        df = pd.read_sql(query, engine)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        return df
    
    @staticmethod
    def convert_to_numpy(df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        将DataFrame转换为numpy数组字典
        
        参数:
            df: DataFrame
            
        返回:
            字典，包含open, high, low, close, volume等数组
        """
        return {
            'datetime': df['datetime'].values,
            'open': df['open'].values.astype(float),
            'high': df['high'].values.astype(float),
            'low': df['low'].values.astype(float),
            'close': df['close'].values.astype(float),
            'volume': df['volume'].values.astype(float) if 'volume' in df.columns else None,
        }


class EnhancedCrossPeriodDataManager(CrossPeriodDataManager):
    """增强的跨周期数据管理器，支持从文件或数据库加载数据"""
    
    def __init__(self):
        super().__init__()
        self.data_loader = DataLoader()
        # 存储不同周期的数据
        self.period_data: Dict[str, Dict[str, np.ndarray]] = {}
    
    def load_period_data(
        self,
        period: PeriodType,
        n: int,
        symbol: str,
        source: str,
        source_type: str = "parquet",
        **kwargs
    ) -> bool:
        """
        加载指定周期的数据
        
        参数:
            period: 周期类型
            n: 周期参数
            symbol: 合约代码
            source: 数据源（文件路径或数据库连接字符串）
            source_type: 数据源类型（"parquet" 或 "database"）
            **kwargs: 其他参数（如start_time, end_time等）
            
        返回:
            True如果加载成功，False如果失败
        """
        cache_key = f"{symbol}_{period.value}_{n}"
        
        try:
            if source_type == "parquet":
                df = self.data_loader.load_from_parquet(source, symbol)
            elif source_type == "database":
                df = self.data_loader.load_from_database(
                    source,
                    kwargs.get('table_name', 'kline_data'),
                    symbol,
                    kwargs.get('start_time', datetime(2020, 1, 1)),
                    kwargs.get('end_time', datetime.now()),
                    interval=f"{n}m" if period == PeriodType.MIN else None
                )
            else:
                raise ValueError(f"不支持的数据源类型: {source_type}")
            
            # 转换为numpy数组
            data_dict = self.data_loader.convert_to_numpy(df)
            self.period_data[cache_key] = data_dict
            
            return True
        except Exception as e:
            print(f"加载数据失败: {e}")
            return False
    
    def get_period_data(
        self,
        period: PeriodType,
        n: int,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        获取指定周期的数据
        
        参数:
            period: 周期类型
            n: 周期参数
            symbol: 合约代码
            start_time: 开始时间
            end_time: 结束时间
            
        返回:
            数据字典，如果获取失败返回 None
        """
        cache_key = f"{symbol}_{period.value}_{n}"
        
        if cache_key in self.period_data:
            data = self.period_data[cache_key]
            # 根据时间范围过滤数据
            datetime_array = data['datetime']
            mask = (datetime_array >= start_time) & (datetime_array <= end_time)
            
            filtered_data = {}
            for key, value in data.items():
                if key == 'datetime':
                    filtered_data[key] = value[mask]
                else:
                    filtered_data[key] = value[mask] if value is not None else None
            
            return filtered_data
        
        return None
    
    def execute_formula(
        self,
        formula_name: str,
        period: PeriodType,
        n: int,
        symbol: str,
        data: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        执行被引用的指标公式
        
        参数:
            formula_name: 指标名称
            period: 周期类型
            n: 周期参数
            symbol: 合约代码
            data: K线数据字典
            
        返回:
            指标计算结果字典
        """
        # 根据指标名称执行相应的计算
        # 这里以 MIN5_OPEN 为例，计算前一个周期的开盘价
        if formula_name == "MIN5_OPEN":
            if 'open' in data:
                prev_open = REF(data['open'], 1)
                return {'PREV_OPEN': prev_open}
        
        # 可以添加更多指标公式
        return {}
    
    def resolve_import(
        self,
        import_stmt: ImportStatement,
        symbol: str,
        current_time: datetime,
        current_data: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        解析 #IMPORT 引用，获取跨周期数据
        
        参数:
            import_stmt: #IMPORT 语句对象
            symbol: 当前合约代码
            current_time: 当前时间
            current_data: 当前周期的数据
            
        返回:
            跨周期数据字典
        """
        # 计算目标周期的时间范围（获取足够的历史数据）
        from datetime import timedelta
        
        if import_stmt.period == PeriodType.MIN:
            # 对于5分钟周期，获取最近100根K线的数据
            start_time = current_time - timedelta(minutes=import_stmt.n * 100)
        elif import_stmt.period == PeriodType.DAY:
            start_time = current_time - timedelta(days=100)
        else:
            start_time = current_time - timedelta(days=30)
        
        end_time = current_time
        
        # 获取目标周期的数据
        period_data = self.get_period_data(
            import_stmt.period,
            import_stmt.n,
            symbol,
            start_time,
            end_time
        )
        
        if period_data is None:
            return {}
        
        # 执行被引用的指标公式
        formula_result = self.execute_formula(
            import_stmt.formula,
            import_stmt.period,
            import_stmt.n,
            symbol,
            period_data
        )
        
        # 将结果映射到当前周期（简化版：返回最后一个值）
        # 实际实现中需要更复杂的数据对齐逻辑
        mapped_result = {}
        for key, value in formula_result.items():
            if value is not None and len(value) > 0:
                # 简化处理：返回最后一个值（实际应该对齐到当前时间）
                mapped_result[key] = np.array([value[-1]])
        
        return mapped_result


class TrendStrategy:
    """趋势判断策略示例"""
    
    def __init__(self, symbol: str, data_source: str, source_type: str = "parquet"):
        """
        初始化策略
        
        参数:
            symbol: 合约代码
            data_source: 数据源路径或连接字符串
            source_type: 数据源类型
        """
        self.symbol = symbol
        self.data_source = data_source
        self.source_type = source_type
        
        # 创建数据管理器
        self.data_manager = EnhancedCrossPeriodDataManager()
        
        # 加载5分钟周期数据
        self.load_5min_data()
        
        # 解析 #IMPORT 语句
        self.import_statements = self.parse_import_code()
        
        # 创建解析器
        self.resolver = ImportResolver(self.data_manager)
    
    def load_5min_data(self):
        """加载5分钟周期数据"""
        success = self.data_manager.load_period_data(
            period=PeriodType.MIN,
            n=5,
            symbol=self.symbol,
            source=self.data_source,
            source_type=self.source_type
        )
        
        if success:
            print(f"成功加载 {self.symbol} 的5分钟K线数据")
        else:
            print(f"加载 {self.symbol} 的5分钟K线数据失败")
    
    def parse_import_code(self) -> List[ImportStatement]:
        """解析 #IMPORT 代码"""
        code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""
        return ImportParser.parse_code(code)
    
    def check_trend(self, current_close: float, current_time: datetime) -> bool:
        """
        检查趋势：当前收盘价是否大于前一个5分钟周期的开盘价
        
        参数:
            current_close: 当前收盘价
            current_time: 当前时间
            
        返回:
            True如果满足条件（趋势多），False否则
        """
        # 解析跨周期引用
        results = self.resolver.resolve_imports(
            self.import_statements,
            self.symbol,
            current_time,
            np.array([current_close])
        )
        
        # 获取前一个5分钟周期的开盘价
        if "MIN5" in results and "PREV_OPEN" in results["MIN5"]:
            prev_open_array = results["MIN5"]["PREV_OPEN"]
            if len(prev_open_array) > 0:
                prev_open = prev_open_array[0]
                
                if not np.isnan(prev_open) and current_close > prev_open:
                    return True
        
        return False
    
    def process_bar(self, bar_time: datetime, close_price: float):
        """
        处理一根K线
        
        参数:
            bar_time: K线时间
            close_price: 收盘价
        """
        if self.check_trend(close_price, bar_time):
            print(f"[{bar_time}] 趋势多 - 当前收盘价: {close_price}")


def example_usage():
    """使用示例"""
    
    # 示例1: 从parquet文件加载数据
    print("=" * 60)
    print("示例1: 从parquet文件加载5分钟K线数据")
    print("=" * 60)
    
    # 假设parquet文件路径
    parquet_file = "data/5min_bars.parquet"
    
    # 检查文件是否存在（如果不存在，创建示例数据）
    if not Path(parquet_file).exists():
        print(f"创建示例数据文件: {parquet_file}")
        # 创建示例数据
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        sample_data = pd.DataFrame({
            'datetime': dates,
            'open': 100 + np.random.randn(100).cumsum() * 0.1,
            'high': 100 + np.random.randn(100).cumsum() * 0.1 + 0.5,
            'low': 100 + np.random.randn(100).cumsum() * 0.1 - 0.5,
            'close': 100 + np.random.randn(100).cumsum() * 0.1,
            'volume': np.random.randint(1000, 10000, 100)
        })
        sample_data.to_parquet(parquet_file, index=False)
        print(f"示例数据已创建: {parquet_file}")
    
    # 创建策略实例（小恒指期货主连，交易所HKFE）
    strategy = TrendStrategy(
        symbol="MHImain",  # 小恒指期货主连
        data_source=parquet_file,
        source_type="parquet"
    )
    
    # 模拟处理几根K线
    test_times = pd.date_range(start='2024-01-01 09:00', periods=10, freq='1min')
    test_closes = 100 + np.random.randn(10).cumsum() * 0.1
    
    print("\n处理K线数据:")
    for i, (time, close) in enumerate(zip(test_times, test_closes)):
        strategy.process_bar(time, close)
    
    # 示例2: 从数据库加载数据
    print("\n" + "=" * 60)
    print("示例2: 从数据库加载5分钟K线数据")
    print("=" * 60)
    
    # 数据库连接示例（需要根据实际情况配置）
    # db_connection = "postgresql://user:password@localhost:5432/dbname"
    # 
    # strategy_db = TrendStrategy(
    #     symbol="MHImain",
    #     data_source=db_connection,
    #     source_type="database"
    # )
    # 
    # # 处理数据
    # strategy_db.process_bar(datetime.now(), 105.5)


if __name__ == "__main__":
    example_usage()

