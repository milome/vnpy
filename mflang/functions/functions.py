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


def SUMBARS(X: Union[np.ndarray, list], A: Union[int, float, np.ndarray]) -> np.ndarray:
    """
    求累加到指定值的周期数
    
    参数:
        X: 时间序列数组（numpy数组或列表），最新的值在数组末尾
        A: 目标值，可以是整数、浮点数或数组（支持变量）
        
    返回值:
        返回一个整数数组，每个元素表示从该位置向前累加X的值，直到累加和>=A所需的周期数
        - 如果累加不到目标值A，返回NaN（使用浮点数组以支持NaN）
        - 非NaN值都是整数
        
    规则:
        1. 从当前位置向前（向历史）累加X的值，直到累加和>=A
        2. 返回需要多少个周期（包括当前位置）
        3. 如果累加完所有历史数据还是不够，返回NaN
        4. A可以为变量（数组）
        
    获取当前值:
        由于返回的是numpy数组，要获取当前值（最后一个元素）可以使用：
        - result[-1] 获取最后一个值（当前值）
        - 需要先检查是否为NaN: if not np.isnan(result[-1])
        - 转换为整数: periods = int(result[-1])
        - 示例: periods = int(SUMBARS(vol, 20000)[-1]) if not np.isnan(SUMBARS(vol, 20000)[-1]) else None
        
    示例:
        >>> # 例1: 成交量累加到20000需要的周期数
        >>> vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
        >>> SUMBARS(vol, 20000)
        array([nan, nan, nan, nan, nan, nan])  # 累加不到20000
        
        >>> vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
        >>> SUMBARS(vol, 10000)
        array([nan, nan, nan, nan, 3., 2.])
        # 位置4: 5000<10000(1周期), 5000+4000=9000<10000(2周期), 5000+4000+3000=12000>=10000(3周期)
        # 位置5: 6000<10000(1周期), 6000+5000=11000>=10000(2周期)
        
        >>> # 例2: A为变量（数组）
        >>> vol = np.array([1000, 2000, 3000, 4000, 5000])
        >>> A = np.array([5000, 6000, 7000, 8000, 9000])
        >>> SUMBARS(vol, A)
        array([nan, nan, nan, 3., 2.])
        # 位置3: 4000+3000+2000=9000>=8000, 需要3个周期
        # 位置4: 5000+4000=9000>=9000, 需要2个周期
    """
    # 转换为numpy数组以便处理
    if not isinstance(X, np.ndarray):
        X = np.array(X, dtype=float)
    else:
        X = X.astype(float)
    
    # 处理A为空值或NaN的情况
    if A is None:
        return np.full_like(X, np.nan, dtype=float)
    
    if isinstance(A, (float, np.floating)) and np.isnan(A):
        return np.full_like(X, np.nan, dtype=float)
    
    # 初始化结果数组（使用float以支持NaN，但值都是整数）
    result = np.full(len(X), np.nan, dtype=float)
    
    # 处理A为数组的情况
    if isinstance(A, (np.ndarray, list)):
        A = np.array(A, dtype=float)
        # 如果A是标量数组，转换为标量
        if A.ndim == 0:
            A = float(A)
        else:
            # A是数组，需要逐元素处理
            for i in range(len(X)):
                if i < len(A):
                    a_val = A[i]
                elif len(A) > 0:
                    a_val = A[-1]  # 使用最后一个值
                else:
                    a_val = np.nan
                
                if np.isnan(a_val) or a_val <= 0:
                    result[i] = np.nan
                    continue
                
                # 从当前位置向前累加
                cumulative_sum = 0.0
                periods = 0
                for j in range(i, -1, -1):  # 从i向前到0
                    cumulative_sum += X[j]
                    periods += 1
                    if cumulative_sum >= a_val:
                        result[i] = int(periods)
                        break
                # 如果循环结束还没达到目标，result[i]保持为NaN
            return result
    
    # A是标量，转换为浮点数
    try:
        A = float(A)
    except (ValueError, TypeError):
        return np.full_like(X, np.nan, dtype=float)
    
    # 处理A为负数或0的情况
    if A <= 0:
        return np.full_like(X, np.nan, dtype=float)
    
    # 对于每个位置，从当前位置向前累加
    for i in range(len(X)):
        cumulative_sum = 0.0
        periods = 0
        for j in range(i, -1, -1):  # 从i向前到0
            cumulative_sum += X[j]
            periods += 1
            if cumulative_sum >= A:
                result[i] = int(periods)
                break
        # 如果循环结束还没达到目标，result[i]保持为NaN
    
    return result


def BARPOS(X: Union[np.ndarray, list]) -> np.ndarray:
    """
    返回从第一根K线开始到当前的周期数
    
    参数:
        X: 时间序列数组（numpy数组或列表），最新的值在数组末尾
           用于确定K线数量，可以是任意K线数据（如close、high、low等）
        
    返回值:
        返回一个整数数组，每个元素表示从第一根K线到当前位置的周期数
        - 第一根K线返回1
        - 第二根K线返回2
        - 以此类推
        - 返回值都是整数
        
    规则:
        1. BARPOS返回本地已有的K线根数，从本机上存在的数据开始算起
        2. 本机已有的第一根K线上返回值为1
        3. BARPOS函数本身没有参数，但需要传入数组来确定K线数量
        
    获取当前值:
        由于返回的是numpy数组，要获取当前值（最后一个元素）可以使用：
        - result[-1] 获取最后一个值（当前值）
        - 转换为整数: current_pos = int(result[-1])
        - 示例: current_pos = int(BARPOS(close)[-1])  # Python实现需要参数，麦语言中为BARPOS
        
    示例:
        >>> # 例1: 基本用法
        >>> # 在麦语言中：BARPOS
        >>> # 在Python实现中，由于技术限制需要传入数组来确定K线数量
        >>> close = np.array([100, 101, 102, 103, 104, 105])
        >>> BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
        array([1., 2., 3., 4., 5., 6.])
        
        >>> # 例2: 求本地已有数据的最小值（LLV(L, BARPOS)）
        >>> # 在麦语言中：LLV(L, BARPOS)
        >>> low = np.array([99, 100, 101, 102, 103, 104])
        >>> barpos = BARPOS(low)  # Python实现需要参数，麦语言中为BARPOS
        >>> # LLV(L, BARPOS) 等价于 low.min()
        >>> min_value = low.min()
        
        >>> # 例3: 判断是否为第一根K线（IFELSE(BARPOS=1, H, 0)）
        >>> # 在麦语言中：IFELSE(BARPOS=1, H, 0)
        >>> high = np.array([101, 102, 103, 104, 105, 106])
        >>> barpos = BARPOS(high)  # Python实现需要参数，麦语言中为BARPOS
        >>> # IFELSE(BARPOS=1, H, 0)
        >>> result = np.where(barpos == 1, high, 0)
        >>> # 结果: [101., 0., 0., 0., 0., 0.]
    """
    # 转换为numpy数组以便处理
    if not isinstance(X, np.ndarray):
        X = np.array(X, dtype=float)
    else:
        X = X.astype(float)
    
    # 返回从1开始的索引数组（第一根K线为1）
    length = len(X)
    result = np.arange(1, length + 1, dtype=float)
    
    return result


def HHV(X: Union[np.ndarray, list], N: Union[int, float, np.ndarray]) -> np.ndarray:
    """
    求X在N个周期内的最高值
    
    参数:
        X: 时间序列数组（numpy数组或列表），最新的值在数组末尾
        N: 周期数，可以是整数、浮点数或数组
        
    返回值:
        - 如果X是数组，返回相同形状的数组，每个元素是对应位置N个周期内的最高值
        - 如果数据不足或N无效，返回NaN值
        
    规则:
        1. N包含当前k线（重要：N个周期包括当前位置）
        2. 若N为0则从第一个有效值开始算起（从第一根K线到当前位置的最高值）
        3. 当N为有效值，但当前的k线数不足N根，按照实际的根数计算
        4. N为空值或NaN时，返回NaN
        5. N可以是变量（数组）
        
    获取当前值:
        由于返回的是numpy数组，要获取当前值（最后一个元素）可以使用：
        - result[-1] 获取最后一个值（当前值）
        - 需要先检查是否为NaN: if not np.isnan(result[-1])
        - 示例: hhv_value = HHV(high, 3)[-1]
        
    示例:
        >>> # 例1: 基本用法（N=3，包含当前K线）
        >>> high = np.array([100, 101, 102, 103, 104, 105])
        >>> HHV(high, 3)
        array([100., 101., 102., 103., 104., 105.])
        # 位置0: 只有1根K线，最高值=100
        # 位置1: 有2根K线，最高值=max(100,101)=101
        # 位置2: 有3根K线，最高值=max(100,101,102)=102
        # 位置3: 有3根K线，最高值=max(101,102,103)=103
        
        >>> # 例2: N=0的情况（从第一个有效值开始算起）
        >>> high = np.array([100, 101, 102, 103, 104, 105])
        >>> HHV(high, 0)
        array([100., 101., 102., 103., 104., 105.])
        # 每个位置都是从第一根K线到当前位置的最高值
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
        if N.ndim == 0:
            N = float(N)
        else:
            # N是数组，需要逐元素处理
            result = np.full_like(X, np.nan, dtype=float)
            for i in range(len(X)):
                if i < len(N):
                    n_val = N[i]
                elif len(N) > 0:
                    n_val = N[-1]
                else:
                    n_val = np.nan
                
                if not np.isnan(n_val):
                    n_int = int(n_val)
                    if n_int == 0:
                        # N=0: 从第一个有效值开始算起（从第一根K线到当前位置）
                        result[i] = np.max(X[0:i+1])
                    elif n_int > 0:
                        # N>0: 计算N个周期内的最高值（包含当前K线）
                        # 如果数据不足N根，按照实际的根数计算
                        start_idx = max(0, i - n_int + 1)
                        result[i] = np.max(X[start_idx:i+1])
            return result
    
    # N是标量，转换为整数
    try:
        N = int(N)
    except (ValueError, TypeError):
        return np.full_like(X, np.nan, dtype=float)
    
    # 处理N为0的情况：从第一个有效值开始算起
    if N == 0:
        result = np.full_like(X, np.nan, dtype=float)
        for i in range(len(X)):
            # 从第一根K线到当前位置的最高值
            result[i] = np.max(X[0:i+1])
        return result
    
    # 处理N为负数的情况
    if N < 0:
        return np.full_like(X, np.nan, dtype=float)
    
    # 使用numpy的向量化操作
    result = np.full_like(X, np.nan, dtype=float)
    
    # 对于每个位置i，计算N个周期内的最高值（包含当前K线）
    # 如果数据不足N根，按照实际的根数计算
    for i in range(len(X)):
        # 计算起始位置：max(0, i - N + 1)，确保包含当前K线
        start_idx = max(0, i - N + 1)
        # 计算从start_idx到i（包含i）的最高值
        result[i] = np.max(X[start_idx:i+1])
    
    return result


def BP(group: Optional[str] = None) -> Union[np.ndarray, float]:
    """
    BP指令：买入平仓，平掉空头持仓
    
    该指令用于T+0策略，即当天可以买卖。
    满足条件时，买入平仓，平掉空头持仓。
    
    参数:
        group: 可选的分组参数，可以是 'A' 到 'I' 的任意字符，用于指定组别
               如果为 None，则平掉模型内所有持仓
    
    返回值:
        返回一个特殊的交易信号值，用于标记需要执行买入平仓操作
        - 返回 1.0 表示需要执行 BP 操作
        - 返回 0.0 表示不需要执行 BP 操作
    
    规则:
        1. BP指令默认平掉模型内所有持仓，不支持指定手数
        2. 指令支持分组，可指定组别('A'--'I')
        3. BP指令不支持和T+1策略指令一起使用
        4. 在模型文件中，BP指令通常与条件一起使用，如：
           - CLOSE>MA(CLOSE,5),BP;  // 收盘价大于5周期均线，买平仓
           - CROSSUP(C,MA(C,5)),BP('A');  // A组平空仓指令
    
    注意:
        - BP指令是一个交易指令，不是计算函数
        - 在策略生成时，BP指令会被转换为实际的交易代码
        - 当条件满足时，会执行买入平仓操作，平掉所有空头持仓（或指定组的空头持仓）
    
    示例:
        >>> # 在模型文件中使用：
        >>> # CLOSE>MA(CLOSE,5),BP;  // 当收盘价大于5周期均线时，买入平仓
        >>> # CROSSUP(C,MA(C,5)),BP('A');  // A组平空仓指令
        
        >>> # 在Python代码中使用（通常由策略生成器自动生成）：
        >>> condition = np.array([False, False, True, True, False])
        >>> if condition[-1]:  # 当前条件满足
        >>>     bp_signal = BP()  # 生成BP信号
        >>>     # 在策略逻辑中处理BP信号，执行买入平仓操作
    """
    # BP指令返回一个标记值，表示需要执行买入平仓操作
    # 在实际使用中，这个值会被策略生成器转换为实际的交易代码
    
    # 验证分组参数
    if group is not None:
        if not isinstance(group, str) or len(group) != 1:
            raise ValueError(f"分组参数必须是单个字符，范围 'A' 到 'I'，当前值: {group}")
        if group < 'A' or group > 'I':
            raise ValueError(f"分组参数必须在 'A' 到 'I' 之间，当前值: {group}")
    
    # 返回BP信号值（1.0表示需要执行BP操作）
    # 注意：在实际使用中，BP指令通常与条件一起使用
    # 例如：condition,BP() 表示当condition为True时执行BP操作
    return 1.0


def BPK(group: Optional[str] = None) -> Union[np.ndarray, float]:
    """
    BPK指令：买平后买开，空单转多单
    
    该指令用于T+0策略，即当天可以买卖。
    满足条件时，先买入平仓（平掉空头持仓），然后买入开仓（建立多头持仓）。
    
    参数:
        group: 可选的分组参数，可以是 'A' 到 'I' 的任意字符，用于指定组别
               如果为 None，则对模型内所有持仓进行操作
    
    返回值:
        返回一个特殊的交易信号值，用于标记需要执行买平后买开操作
        - 返回 1.0 表示需要执行 BPK 操作
        - 返回 0.0 表示不需要执行 BPK 操作
    
    规则:
        1. BPK指令不指定交易手数，不支持 BPK(3) 这种写法
        2. 交易手数为设置的固定手数或使用T_COMMAND函数设置的手数
        3. 指令支持分组，可指定组别('A'--'I')
        4. T_COMMAND函数设置的手数优先于设置的固定手数
        5. BPK指令不支持和T+1策略指令一起使用
        6. 在模型文件中，BPK指令通常与条件一起使用，如：
           - CLOSE>MA(CLOSE,5),BPK;  // 收盘价大于5周期均线，平掉空仓，再买开仓
           - CROSSUP(C,MA(C,5)),BPK('A');  // A组买平开指令
    
    注意:
        - BPK指令是一个交易指令，不是计算函数
        - 在策略生成时，BPK指令会被转换为实际的交易代码
        - 当条件满足时，会先执行买入平仓操作（如果有空头持仓），然后执行买入开仓操作
        - 交易手数由T_COMMAND函数或固定手数设置决定
    
    示例:
        >>> # 在模型文件中使用：
        >>> # T_COMMAND(3);  // 设置交易手数为3
        >>> # CLOSE>MA(CLOSE,5),BPK;  // 当收盘价大于5周期均线时，买平后买开
        >>> # CROSSUP(C,MA(C,5)),BPK('A');  // A组买平开指令
        
        >>> # 在Python代码中使用（通常由策略生成器自动生成）：
        >>> condition = np.array([False, False, True, True, False])
        >>> if condition[-1]:  # 当前条件满足
        >>>     bpk_signal = BPK()  # 生成BPK信号
        >>>     # 在策略逻辑中处理BPK信号，执行买平后买开操作
    """
    # BPK指令返回一个标记值，表示需要执行买平后买开操作
    # 在实际使用中，这个值会被策略生成器转换为实际的交易代码
    
    # 验证分组参数
    if group is not None:
        if not isinstance(group, str) or len(group) != 1:
            raise ValueError(f"分组参数必须是单个字符，范围 'A' 到 'I'，当前值: {group}")
        if group < 'A' or group > 'I':
            raise ValueError(f"分组参数必须在 'A' 到 'I' 之间，当前值: {group}")
    
    # 返回BPK信号值（1.0表示需要执行BPK操作）
    # 注意：在实际使用中，BPK指令通常与条件一起使用
    # 例如：condition,BPK() 表示当condition为True时执行BPK操作
    # BPK操作包括：1. 如果有空头持仓，先买入平仓；2. 然后买入开仓
    return 1.0


def SPK(group: Optional[str] = None) -> Union[np.ndarray, float]:
    """
    SPK指令：卖平后卖开，多单转空单
    
    该指令用于T+0策略，即当天可以买卖。
    满足条件时，先卖出平仓（平掉多头持仓），然后卖出开仓（建立空头持仓）。
    
    参数:
        group: 可选的分组参数，可以是 'A' 到 'I' 的任意字符，用于指定组别
               如果为 None，则对模型内所有持仓进行操作
    
    返回值:
        返回一个特殊的交易信号值，用于标记需要执行卖平后卖开操作
        - 返回 1.0 表示需要执行 SPK 操作
        - 返回 0.0 表示不需要执行 SPK 操作
    
    规则:
        1. SPK指令不指定交易手数，不支持 SPK(3) 这种写法
        2. 交易手数为设置的固定手数或使用T_COMMAND函数设置的手数
        3. 指令支持分组，可指定组别('A'--'I')
        4. T_COMMAND函数设置的手数优先于设置的固定手数
        5. SPK指令不支持和T+1策略指令一起使用
        6. 在模型文件中，SPK指令通常与条件一起使用，如：
           - CLOSE<MA(CLOSE,5),SPK;  // 收盘价小于5周期均线，平掉多仓，再卖开仓
           - CROSSDOWN(C,MA(C,5)),SPK('A');  // A组卖平开指令
    
    注意:
        - SPK指令是一个交易指令，不是计算函数
        - 在策略生成时，SPK指令会被转换为实际的交易代码
        - 当条件满足时，会先执行卖出平仓操作（如果有多头持仓），然后执行卖出开仓操作
        - 交易手数由T_COMMAND函数或固定手数设置决定
    
    示例:
        >>> # 在模型文件中使用：
        >>> # T_COMMAND(3);  // 设置交易手数为3
        >>> # CLOSE<MA(CLOSE,5),SPK;  // 当收盘价小于5周期均线时，卖平后卖开
        >>> # CROSSDOWN(C,MA(C,5)),SPK('A');  // A组卖平开指令
        
        >>> # 在Python代码中使用（通常由策略生成器自动生成）：
        >>> condition = np.array([False, False, True, True, False])
        >>> if condition[-1]:  # 当前条件满足
        >>>     spk_signal = SPK()  # 生成SPK信号
        >>>     # 在策略逻辑中处理SPK信号，执行卖平后卖开操作
    """
    # SPK指令返回一个标记值，表示需要执行卖平后卖开操作
    # 在实际使用中，这个值会被策略生成器转换为实际的交易代码
    
    # 验证分组参数
    if group is not None:
        if not isinstance(group, str) or len(group) != 1:
            raise ValueError(f"分组参数必须是单个字符，范围 'A' 到 'I'，当前值: {group}")
        if group < 'A' or group > 'I':
            raise ValueError(f"分组参数必须在 'A' 到 'I' 之间，当前值: {group}")
    
    # 返回SPK信号值（1.0表示需要执行SPK操作）
    # 注意：在实际使用中，SPK指令通常与条件一起使用
    # 例如：condition,SPK() 表示当condition为True时执行SPK操作
    # SPK操作包括：1. 如果有多头持仓，先卖出平仓；2. 然后卖出开仓
    return 1.0

