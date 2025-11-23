#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析麦语言表达式示例
#IMPORT[MIN,5,MACD] AS MIN5_VAR；
REF(BARPOS, BARSLAST(MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)))

当前为1分钟周期。

BARPOS: 当前1分钟周期里的K线位置，从本机第一根K线开始计数。

需要满足的条件：最近一根满足5分钟MACD大于0且当前收盘价大于前三根K线最高价。
要求使用#IMPORT引用5分钟周期的数据。

返回：REF(BARPOS, BARSLAST结果)，即BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）。
K线位置从本机第一根K线计算，从数据库或者parquet文件加载历史K线数据后计算。
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import talib

from mflang import BARSLAST, BARPOS, HHV
from mflang import ImportParser
from mflang.import_parser import PeriodType


def load_minute_data_from_parquet(file_path: str, symbol: str = "MHImain", interval: str = "1m"):
    """
    从parquet文件加载K线数据
    
    参数:
        file_path: parquet文件路径
        symbol: 合约代码（小恒指期货主连MHImain）
        interval: 周期（"1m"表示1分钟，"5m"表示5分钟）
    """
    df = pd.read_parquet(file_path)
    
    # 确保datetime列存在
    if 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 过滤合约和周期
    if 'symbol' in df.columns:
        df = df[df['symbol'] == symbol]
    if 'interval' in df.columns:
        df = df[df['interval'] == interval]
    
    # 按时间排序
    df = df.sort_values('datetime').reset_index(drop=True)
    
    return df


def calculate_macd(close: np.ndarray, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> np.ndarray:
    """
    计算MACD指标
    
    参数:
        close: 收盘价数组
        fast_period: 快线周期
        slow_period: 慢线周期
        signal_period: 信号线周期
        
    返回:
        MACD值数组
    """
    macd, signal, hist = talib.MACD(close, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
    return macd


def align_5min_to_1min(macd_5min: np.ndarray, df_1min: pd.DataFrame, df_5min: pd.DataFrame) -> np.ndarray:
    """
    将5分钟周期的MACD对齐到1分钟周期（保留用于兼容性）
    
    参数:
        macd_5min: 5分钟周期的MACD数组
        df_1min: 1分钟K线数据
        df_5min: 5分钟K线数据
        
    返回:
        对齐到1分钟周期的MACD数组
    """
    return align_cross_period_to_1min(macd_5min, df_1min, df_5min, 5)


def align_cross_period_to_1min(
    macd_target: np.ndarray, 
    df_1min: pd.DataFrame, 
    df_target: pd.DataFrame,
    target_period_minutes: int
) -> np.ndarray:
    """
    将目标周期的MACD对齐到1分钟周期
    
    参数:
        macd_target: 目标周期的MACD数组
        df_1min: 1分钟K线数据
        df_target: 目标周期K线数据
        target_period_minutes: 目标周期分钟数（如5表示5分钟）
        
    返回:
        对齐到1分钟周期的MACD数组
    """
    # 创建对齐数组
    macd_1min = np.full(len(df_1min), np.nan, dtype=float)
    
    # 为每个1分钟K线找到对应的目标周期K线
    for i, dt_1min in enumerate(df_1min['datetime']):
        # 找到包含这个1分钟K线的目标周期K线
        for j, dt_target in enumerate(df_target['datetime']):
            # 目标周期K线的时间范围：dt_target 到 dt_target + target_period_minutes分钟
            if dt_1min >= dt_target and dt_1min < dt_target + timedelta(minutes=target_period_minutes):
                if j < len(macd_target):
                    macd_1min[i] = macd_target[j]
                break
    
    return macd_1min


def parse_formula_ref_barslast(
    df_1min: pd.DataFrame,
    df_cross_period: pd.DataFrame = None,
    import_code: str = None
) -> np.ndarray:
    """
    解析麦语言表达式：
    #IMPORT[MIN,5,MACD] AS MIN5_VAR；
    REF(BARPOS, BARSLAST(MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)))
    
    参数:
        df_1min: 1分钟K线数据（小恒指期货主连MHImain）
        df_cross_period: 跨周期K线数据（根据#IMPORT语句确定周期），通过#IMPORT引用
        import_code: #IMPORT语句代码（可选，如果不提供则使用默认值）
        
    返回:
        返回REF(BARPOS, BARSLAST结果)数组，即BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）
        
    说明:
        1. 解析#IMPORT语句，根据import_stmt.period和import_stmt.n确定跨周期引用对应的周期
        2. BARPOS - 当前1分钟周期里的K线位置，从本机第一根K线开始计数
        3. 使用#IMPORT引用跨周期数据（根据import_stmt确定周期）
        4. 在1分钟周期上通过MIN5_VAR.MACD访问跨周期的MACD值
        5. 条件：MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)
        6. BARSLAST(condition) - 上一次条件成立到当前的周期数
        7. REF(BARPOS, BARSLAST结果) - BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）
    """
    # 步骤1: 定义被引用的指标（MACD标准公式）
    # 被引用的指标名称：MACD（标准公式名称）
    # 该指标在目标周期上计算MACD值
    
    # 步骤2: 解析#IMPORT语句
    # 使用#IMPORT引用跨周期数据
    # 语法：#IMPORT[PERIOD,N,FORMULA] AS VAR
    # 这里：PERIOD=MIN（分钟周期），N=5（5分钟），FORMULA=MACD（被引用的指标名，标准公式名称），VAR=MIN5_VAR（变量名，不能以数字开头）
    if import_code is None:
        import_code = """
#IMPORT[MIN,5,MACD] AS MIN5_VAR
"""
    import_statements = ImportParser.parse_code(import_code)
    
    if not import_statements:
        raise ValueError("无法解析#IMPORT语句")
    
    import_stmt = import_statements[0]
    print(f"解析#IMPORT语句: {import_stmt}")
    print(f"  周期: {import_stmt.period.value}, N: {import_stmt.n}, 指标: {import_stmt.formula}, 变量: {import_stmt.var_name}")
    
    # 步骤3: 根据import_stmt确定跨周期引用对应的周期
    # 使用import_stmt.period和import_stmt.n来确定需要加载的周期数据
    target_period_minutes = None
    if import_stmt.period == PeriodType.MIN:
        target_period_minutes = import_stmt.n
    elif import_stmt.period == PeriodType.HOUR:
        target_period_minutes = import_stmt.n * 60
    elif import_stmt.period == PeriodType.CUSHOUR:
        target_period_minutes = import_stmt.n * 60
    elif import_stmt.period == PeriodType.DAY:
        target_period_minutes = import_stmt.n * 24 * 60
    else:
        raise ValueError(f"不支持的周期类型: {import_stmt.period.value}")
    
    print(f"  目标周期: {target_period_minutes}分钟")
    
    # 步骤4: 加载跨周期数据（如果未提供，则使用传入的df_cross_period）
    if df_cross_period is None:
        raise ValueError(f"需要提供{target_period_minutes}分钟周期的K线数据")
    
    df_target_period = df_cross_period
    
    # 步骤5: 通过#IMPORT获取MIN5_VAR.MACD（跨周期的MACD数据）
    # 被引用的指标MACD应该在目标周期上计算
    # 通过#IMPORT机制，在1分钟周期上可以通过MIN5_VAR.MACD访问目标周期的MACD值
    # 
    # 实现方式：
    # 1. 在目标周期上计算MACD指标（被引用的指标MACD）
    close_target = df_target_period['close'].values
    macd_target = calculate_macd(close_target)  # 这是被引用的指标MACD在目标周期上的计算结果
    
    # 2. 通过#IMPORT的跨周期引用功能，将目标周期MACD对齐到1分钟周期
    # 这是#IMPORT的核心功能：将大周期数据对齐到小周期（1分钟）
    # 对齐后的数据就是MIN5_VAR.MACD（在1分钟周期上访问目标周期的MACD值）
    macd_target_aligned = align_cross_period_to_1min(
        macd_target, 
        df_1min, 
        df_target_period, 
        target_period_minutes
    )
    # macd_target_aligned 就是 MIN5_VAR.MACD（通过#IMPORT引用得到的值）
    
    # 步骤6: 获取1分钟周期的数据
    close_1min = df_1min['close'].values
    high_1min = df_1min['high'].values
    
    # 步骤7: 计算BARPOS - 当前K线位置（从本机第一根K线开始计数）
    barpos = BARPOS(close_1min)  # BARPOS是当前K线位置数组
    
    # 步骤8: 计算HHV(HIGH, 3) - 前3根K线的最高价（包含当前K线）
    hv_high_3 = HHV(high_1min, 3)
    
    # 步骤9: 计算条件：MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)
    # MIN5_VAR.MACD > 0（使用#IMPORT引用的跨周期MACD数据）
    # 通过#IMPORT[MIN,5,MACD] AS MIN5_VAR，可以在1分钟周期上通过MIN5_VAR.MACD访问目标周期的MACD值
    # macd_target_aligned 就是 MIN5_VAR.MACD（通过#IMPORT引用得到的值，已对齐到1分钟周期）
    min5_var_macd = macd_target_aligned  # MIN5_VAR.MACD（根据import_stmt确定的目标周期）
    cond1 = min5_var_macd > 0  # MIN5_VAR.MACD > 0
    # CLOSE > HHV(HIGH, 3)
    cond2 = close_1min > hv_high_3
    # 组合条件
    condition = cond1 & cond2
    
    # 步骤10: 计算BARSLAST(condition) - 上一次条件成立到当前的周期数
    barslast_result = BARSLAST(condition)
    
    # 步骤11: 计算REF(BARPOS, BARSLAST结果)
    # REF(BARPOS, BARSLAST结果) - BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）
    # 如果BARSLAST值是n，表示n根K线前条件成立
    # 那么对应的K线位置（BARPOS）应该是：当前K线位置 - n
    # 然后在BARPOS根K线前，当时的BARSLAST值对应的K线位置
    result = np.full_like(barslast_result, np.nan, dtype=float)
    
    for i in range(len(barslast_result)):
        barpos_val = int(barpos[i])  # 当前K线位置（BARPOS）
        
        # 获取BARSLAST值
        if i < len(barslast_result) and not np.isnan(barslast_result[i]):
            barslast_val = int(barslast_result[i])
        else:
            continue  # 无法获取BARSLAST值，保持NaN
        
        # 计算REF(BARPOS, BARSLAST结果)
        # 在BARPOS根K线前，当时的K线位置 = 当前K线位置 - BARPOS = barpos_val - barpos_val = 0（不存在）
        # 但实际应该理解为：使用当前位置的BARSLAST值来计算对应的K线位置
        # 如果BARSLAST值是n，表示n根K线前条件成立
        # 那么对应的K线位置（BARPOS）应该是：当前K线位置 - n
        if barslast_val >= 0 and barpos_val > barslast_val:
            result[i] = barpos_val - barslast_val
    
    return result


def example_usage():
    """使用示例"""
    print("=" * 80)
    print("解析麦语言表达式示例")
    print("表达式:")
    print("  #IMPORT[MIN,5,MACD] AS MIN5_VAR；")
    print("  REF(BARPOS, BARSLAST(MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)))")
    print("说明:")
    print("  - BARPOS: 当前1分钟周期里的K线位置，从本机第一根K线开始计数")
    print("  - 使用#IMPORT引用5分钟周期的数据：#IMPORT[MIN,5,MACD] AS MIN5_VAR（MACD是标准公式名称）")
    print("  - 在1分钟周期上通过MIN5_VAR.MACD访问5分钟周期的MACD值")
    print("  - 条件：MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)")
    print("  - 返回：REF(BARPOS, BARSLAST结果)，即BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）")
    print("=" * 80)
    
    # 方式1: 从parquet文件加载数据
    print("\n方式1: 从parquet文件加载数据")
    print("-" * 80)
    
    # 加载1分钟K线数据（小恒指期货主连MHImain，交易所HKFE）
    parquet_file_1min = "data/MHImain_1m_bars.parquet"
    parquet_file_5min = "data/MHImain_5m_bars.parquet"
    
    # 如果文件不存在，创建示例数据
    from pathlib import Path
    if not Path(parquet_file_1min).exists():
        print(f"创建示例1分钟K线数据: {parquet_file_1min}")
        dates_1min = pd.date_range(start='2024-01-01 09:00', periods=1000, freq='1min')
        sample_data_1min = pd.DataFrame({
            'datetime': dates_1min,
            'symbol': 'MHImain',
            'interval': '1m',
            'open': 20000 + np.random.randn(1000).cumsum() * 10,
            'high': 20000 + np.random.randn(1000).cumsum() * 10 + 20,
            'low': 20000 + np.random.randn(1000).cumsum() * 10 - 20,
            'close': 20000 + np.random.randn(1000).cumsum() * 10,
            'volume': np.random.randint(1000, 10000, 1000)
        })
        Path(parquet_file_1min).parent.mkdir(parents=True, exist_ok=True)
        sample_data_1min.to_parquet(parquet_file_1min, index=False)
        print(f"示例数据已创建: {parquet_file_1min}")
    
    if not Path(parquet_file_5min).exists():
        print(f"创建示例5分钟K线数据: {parquet_file_5min}")
        dates_5min = pd.date_range(start='2024-01-01 09:00', periods=200, freq='5min')
        sample_data_5min = pd.DataFrame({
            'datetime': dates_5min,
            'symbol': 'MHImain',
            'interval': '5m',
            'open': 20000 + np.random.randn(200).cumsum() * 10,
            'high': 20000 + np.random.randn(200).cumsum() * 10 + 20,
            'low': 20000 + np.random.randn(200).cumsum() * 10 - 20,
            'close': 20000 + np.random.randn(200).cumsum() * 10,
            'volume': np.random.randint(5000, 50000, 200)
        })
        sample_data_5min.to_parquet(parquet_file_5min, index=False)
        print(f"示例数据已创建: {parquet_file_5min}")
    
    # 加载数据
    df_1min = load_minute_data_from_parquet(parquet_file_1min, "MHImain", "1m")
    df_5min = load_minute_data_from_parquet(parquet_file_5min, "MHImain", "5m")
    
    print(f"加载1分钟K线数据: {len(df_1min)} 根")
    print(f"加载5分钟K线数据: {len(df_5min)} 根")
    
    # 解析表达式（传入import_code，函数内部会根据import_stmt确定跨周期）
    import_code = """
#IMPORT[MIN,5,MACD] AS MIN5_VAR
"""
    result = parse_formula_ref_barslast(df_1min, df_5min, import_code)
    
    # 获取当前值（最后一根K线的结果）
    current_result = result[-1]
    current_barpos = int(BARPOS(df_1min['close'].values)[-1])
    
    if not np.isnan(current_result):
        barpos_value = int(current_result)
        print(f"\n结果:")
        print(f"  - 当前K线位置（BARPOS）: {current_barpos}")
        print(f"  - REF(BARPOS, BARSLAST结果): {barpos_value}")
        print(f"  - 说明: 最近一次满足条件的K线位置是第 {barpos_value} 根K线")
        print(f"  - （K线位置从本机第一根K线开始计算）")
    else:
        print("\n结果: 未找到满足条件的K线或数据不足")
    
    # 显示详细结果
    print("\n详细结果（最后10根K线）:")
    print("-" * 80)
    barpos_array = BARPOS(df_1min['close'].values)
    for i in range(max(0, len(result) - 10), len(result)):
        dt = df_1min.iloc[i]['datetime']
        close = df_1min.iloc[i]['close']
        current_pos = int(barpos_array[i])
        if not np.isnan(result[i]):
            barpos_val = int(result[i])
            print(f"第 {current_pos} 根K线 [{dt}]: 收盘价={close:.2f}, BARPOS={current_pos}, REF结果={barpos_val}")
        else:
            print(f"第 {current_pos} 根K线 [{dt}]: 收盘价={close:.2f}, BARPOS={current_pos}, REF结果=NaN")
    
    # 方式2: 从数据库加载数据
    print("\n" + "=" * 80)
    print("方式2: 从数据库加载数据")
    print("-" * 80)
    
    # 数据库连接示例（需要根据实际情况配置）
    # db_connection = "postgresql://user:password@localhost:5432/dbname"
    # 
    # def load_from_database(connection_string, table_name, symbol, interval, start_time, end_time):
    #     import sqlalchemy
    #     engine = sqlalchemy.create_engine(connection_string)
    #     query = f"""
    #     SELECT datetime, open, high, low, close, volume
    #     FROM {table_name}
    #     WHERE symbol = '{symbol}'
    #     AND interval = '{interval}'
    #     AND datetime >= '{start_time}'
    #     AND datetime <= '{end_time}'
    #     ORDER BY datetime
    #     """
    #     df = pd.read_sql(query, engine)
    #     df['datetime'] = pd.to_datetime(df['datetime'])
    #     return df
    # 
    # df_1min = load_from_database(
    #     db_connection, "kline_data", "MHImain", "1m",
    #     datetime(2024, 1, 1), datetime.now()
    # )
    # df_5min = load_from_database(
    #     db_connection, "kline_data", "MHImain", "5m",
    #     datetime(2024, 1, 1), datetime.now()
    # )
    # 
    # result = parse_formula_ref_barslast(df_1min, df_5min, numofday=1)
    # current_result = result[-1]
    # if not np.isnan(current_result):
    #     print(f"最近一根满足条件的K线位置: {int(current_result)}")


if __name__ == "__main__":
    example_usage()

