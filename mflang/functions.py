#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言函数实现
"""

import numpy as np
from typing import Union, Optional


def REF(X: Union[np.ndarray, list], N: Union[int, float, np.ndarray]) -> Union[np.ndarray, float]:
    """
    引用X在N个周期前的值
    
    参数:
        X: 时间序列数组（numpy数组或列表），最新的值在数组末尾
        N: 周期数，可以是整数、浮点数或数组
        
    返回值:
        - 如果X是数组，返回相同形状的数组，每个元素是对应位置N个周期前的值
        - 如果数据不足或N无效，返回NaN值
        
    规则:
        1. 当N为有效值，但当前的k线数不足N根，返回NaN
        2. N为0时返回当前X值
        3. N为空值或NaN时返回NaN
        4. N可以为变量（数组）
        
    获取当前值:
        由于返回的是numpy数组，要获取当前值（最后一个元素）可以使用：
        - result[-1] 获取最后一个值（当前值）
        - 需要先检查是否为NaN: if not np.isnan(result[-1])
        - 示例: ref_value = REF(close, 5)[-1]
        
    示例:
        >>> close = np.array([100, 101, 102, 103, 104, 105])
        >>> REF(close, 2)
        array([nan, nan, 100., 101., 102., 103.])
        
        >>> REF(close, 0)
        array([100., 101., 102., 103., 104., 105.])
        
        >>> REF(close, 5)  # 引用5个周期前的值
        array([nan, nan, nan, nan, nan, 100.])
    """
    # 转换为numpy数组以便处理
    if not isinstance(X, np.ndarray):
        X = np.array(X, dtype=float)
    else:
        X = X.astype(float)
    
    # 处理N为空值或NaN的情况
    if N is None:
        return np.full_like(X, np.nan, dtype=float)
    
    if isinstance(N, (float, np.floating)) and np.isnan(N):
        return np.full_like(X, np.nan, dtype=float)
    
    # 处理N为数组的情况
    if isinstance(N, (np.ndarray, list)):
        N = np.array(N, dtype=float)
        # 如果N是标量数组，转换为标量
        if N.ndim == 0:
            N = float(N)
        else:
            # N是数组，需要逐元素处理
            result = np.full_like(X, np.nan, dtype=float)
            for i in range(len(X)):
                if i < len(N):
                    n_val = N[i]
                elif len(N) > 0:
                    n_val = N[-1]  # 使用最后一个值
                else:
                    n_val = np.nan
                
                if not np.isnan(n_val):
                    n_int = int(n_val)
                    if n_int == 0:
                        result[i] = X[i]
                    elif n_int > 0 and i >= n_int:
                        result[i] = X[i - n_int]
                    # 否则保持NaN
            return result
    
    # N是标量，转换为整数
    try:
        N = int(N)
    except (ValueError, TypeError):
        return np.full_like(X, np.nan, dtype=float)
    
    # 处理N为0的情况
    if N == 0:
        return X.copy()
    
    # 处理N为负数的情况（向后引用，通常不支持，返回NaN）
    if N < 0:
        return np.full_like(X, np.nan, dtype=float)
    
    # 使用numpy的向量化操作提高效率
    result = np.full_like(X, np.nan, dtype=float)
    
    # 对于每个位置i，如果i >= N，则引用X[i-N]的值
    valid_mask = np.arange(len(X)) >= N
    if np.any(valid_mask):
        valid_indices = np.where(valid_mask)[0]
        result[valid_indices] = X[valid_indices - N]
    
    return result


def BARSLAST(COND: Union[np.ndarray, list]) -> np.ndarray:
    """
    上一次条件COND成立到当前的周期数
    
    参数:
        COND: 条件数组（布尔数组或可以转换为布尔的数组），True表示条件成立
        
    返回值:
        返回一个整数数组，每个元素表示从该位置向前查找，最近一次条件成立到当前位置的周期数
        - 如果当前位置条件成立，返回0
        - 如果从开始到当前位置条件从未成立，返回NaN（使用浮点数组以支持NaN）
        - 非NaN值都是整数
        
    规则:
        1. 条件成立的当根k线上BARSLAST(COND)的返回值为0
        2. 如果条件从未成立，返回NaN
        
    获取整数结果:
        由于返回的是numpy数组，要获取整数结果可以使用：
        - result[-1] 获取最后一个值（当前值）
        - int(result[-1]) 转换为整数（需要先检查是否为NaN）
        - 示例: periods = int(result[-1]) if not np.isnan(result[-1]) else None
        
    示例:
        >>> # 例1: 上一根阴线到现在的周期数
        >>> open_price = np.array([100, 101, 102, 103, 104, 105])
        >>> close_price = np.array([99, 100, 101, 102, 103, 104])
        >>> cond = open_price > close_price  # 阴线条件
        >>> BARSLAST(cond)
        array([0., nan, 1., 2., 3., 4.])
        
        >>> # 例2: 当日k线数（分钟周期）
        >>> # N:=BARSLAST(DATE<>REF(DATE,1))+1
        >>> # 由于条件成立的当根k线上BARSLAST(COND)的返回值为0，所以"+1"才是当日k线根数
    """
    # 转换为numpy数组
    if not isinstance(COND, np.ndarray):
        COND = np.array(COND)
    
    # 转换为布尔数组
    cond_bool = COND.astype(bool)
    
    # 初始化结果数组（使用float以支持NaN，但值都是整数）
    result = np.full(len(cond_bool), np.nan, dtype=float)
    
    # 对于每个位置，查找最近一次条件成立的位置
    for i in range(len(cond_bool)):
        # 从当前位置向前查找（包括当前位置）
        for j in range(i, -1, -1):
            if cond_bool[j]:
                # 找到最近一次条件成立的位置，计算周期数（确保是整数）
                result[i] = int(i - j)
                break
        # 如果循环结束还没找到，result[i]保持为NaN
    
    return result

