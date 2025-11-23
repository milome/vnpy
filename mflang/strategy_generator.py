#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略代码生成器
将 mflang/mmodels 目录下的模型文件转换为符合 vnpy_ctastrategy 格式的策略文件
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from mflang.import_parser import ImportParser, ImportStatement, PeriodType
from mflang.model_loader import ModelLoader, load_model


@dataclass
class TradingInstruction:
    """交易指令信息"""
    instruction_type: str  # 'BP', 'SP', 'BK', 'SK' 等
    condition: str  # 条件表达式
    group: Optional[str] = None  # 分组参数，'A' 到 'I'


@dataclass
class VariableInfo:
    """变量信息"""
    name: str
    expression: str
    uses_cross_period: bool = False
    cross_period_refs: List[str] = None  # 如 ["MIN5.PREV_OPEN"]
    trading_instruction: Optional[TradingInstruction] = None  # 交易指令信息


class StrategyGenerator:
    """策略代码生成器"""
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        初始化生成器
        
        参数:
            models_dir: 模型文件目录，默认为 mflang/mmodels/
        """
        self.model_loader = ModelLoader(models_dir)
        self.import_parser = ImportParser()
    
    def generate_strategy(
        self,
        model_name: str,
        strategy_class_name: Optional[str] = None,
        output_file: Optional[str] = None,
        author: str = "MFLang Generator"
    ) -> str:
        """
        生成策略代码
        
        参数:
            model_name: 模型文件名（不含路径）
            strategy_class_name: 策略类名，如果为None则自动生成
            output_file: 输出文件路径，如果为None则不写入文件
            author: 策略作者
            
        返回:
            生成的策略代码字符串
        """
        # 读取模型文件内容
        model_file = self.model_loader.models_dir / model_name
        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")
        
        with open(model_file, 'r', encoding='utf-8') as f:
            model_content = f.read()
        
        # 解析 #IMPORT 语句
        import_statements = ImportParser.parse_code(model_content)
        
        # 解析 T_COMMAND 函数调用
        t_command_volume = self._parse_t_command(model_content)
        
        # 清除缓存，确保加载最新的模型文件（忽略注释掉的变量）
        self.model_loader.clear_cache()
        # 同时清除全局加载器的缓存
        from mflang.model_loader import get_model_loader
        get_model_loader().clear_cache()
        
        # 加载模型文件中的变量定义
        model_variables = self.model_loader.load_model(model_name)
        
        # 解析变量信息
        variables_info = self._parse_variables(model_variables, import_statements)
        
        # 生成策略类名
        if strategy_class_name is None:
            strategy_class_name = self._generate_class_name(model_name)
        
        # 生成代码
        code = self._generate_code(
            model_name=model_name,
            strategy_class_name=strategy_class_name,
            import_statements=import_statements,
            variables_info=variables_info,
            t_command_volume=t_command_volume,
            author=author
        )
        
        # 写入文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code)
            # 验证文件是否成功写入
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"策略文件已生成: {output_path}")
            else:
                raise IOError(f"文件写入失败: {output_path}")
        
        return code
    
    def _parse_variables(
        self,
        model_variables: Dict[str, str],
        import_statements: List[ImportStatement]
    ) -> List[VariableInfo]:
        """解析变量信息"""
        variables_info = []
        import_var_names = {stmt.var_name for stmt in import_statements}
        
        for var_name, var_expr in model_variables.items():
            # 检查是否包含交易指令（BP, SP, BK, SK等）
            trading_instruction = self._parse_trading_instruction(var_expr)
            
            # 如果包含交易指令，提取条件表达式
            if trading_instruction:
                # 从表达式中提取条件部分（去掉交易指令部分）
                condition_expr = trading_instruction.condition
            else:
                condition_expr = var_expr
            
            # 检查是否使用跨周期引用（基于条件表达式）
            cross_period_refs = self._extract_cross_period_refs(condition_expr, import_var_names)
            uses_cross_period = len(cross_period_refs) > 0
            
            variables_info.append(VariableInfo(
                name=var_name,
                expression=condition_expr,  # 使用条件表达式作为 expression
                uses_cross_period=uses_cross_period,
                cross_period_refs=cross_period_refs,
                trading_instruction=trading_instruction
            ))
        
        return variables_info
    
    def _parse_t_command(self, content: str) -> Optional[int]:
        """
        解析 T_COMMAND 函数调用
        
        支持的格式：
        - T_COMMAND(N);
        
        参数:
            content: 模型文件内容
            
        返回:
            T_COMMAND 设置的手数，如果未找到则返回 None
        """
        # 匹配 T_COMMAND(N); 格式
        pattern = r'T_COMMAND\s*\(\s*(\d+)\s*\)\s*;'
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            volume = int(match.group(1))
            return volume
        
        return None
    
    def _parse_trading_instruction(self, expression: str) -> Optional[TradingInstruction]:
        """
        解析交易指令
        
        支持的格式：
        - COND,BP; 或 COND,BP('A');
        - COND,SP; 或 COND,SP('A');
        - COND,BK; 或 COND,BK('A');
        - COND,SK; 或 COND,SK('A');
        
        参数:
            expression: 变量表达式
            
        返回:
            TradingInstruction 对象，如果不包含交易指令则返回 None
        """
        # 匹配交易指令模式：COND,INSTRUCTION; 或 COND,INSTRUCTION('GROUP');
        # 支持的指令：BP, SP, BK, SK, BPK, SPK
        # 注意：模型加载器可能已经去掉了分号，所以分号是可选的
        pattern = r'(.+?),\s*(BP|SP|BK|SK|BPK|SPK)\s*(?:\([\'"]?([A-I])[\'"]?\))?\s*;?$'
        match = re.search(pattern, expression, re.IGNORECASE)
        
        if match:
            condition = match.group(1).strip()
            instruction_type = match.group(2).upper()
            group = match.group(3) if match.group(3) else None
            
            return TradingInstruction(
                instruction_type=instruction_type,
                condition=condition,
                group=group
            )
        
        return None
    
    def _extract_cross_period_refs(
        self,
        expression: str,
        import_var_names: Set[str]
    ) -> List[str]:
        """提取跨周期引用"""
        refs = []
        # 匹配 VAR.VARIABLE_NAME 格式
        pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.finditer(pattern, expression)
        
        for match in matches:
            var_ref = match.group(1)
            if var_ref in import_var_names:
                refs.append(f"{var_ref}.{match.group(2)}")
        
        return refs
    
    def _generate_class_name(self, model_name: str) -> str:
        """生成策略类名"""
        # 将模型名转换为驼峰式类名
        # 例如: TEST_IMPORT -> TestImportStrategy
        parts = model_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        return f"{class_name}Strategy"
    
    def _generate_code(
        self,
        model_name: str,
        strategy_class_name: str,
        import_statements: List[ImportStatement],
        variables_info: List[VariableInfo],
        t_command_volume: Optional[int],
        author: str
    ) -> str:
        """生成策略代码"""
        lines = []
        
        # 文件头
        lines.append('#!/usr/bin/env python3')
        lines.append('# -*- coding: utf-8 -*-')
        lines.append(f'"""')
        lines.append(f'自动生成的策略文件')
        lines.append(f'基于模型文件: {model_name}')
        lines.append(f'"""')
        lines.append('')
        
        # 导入语句
        lines.append('from vnpy_ctastrategy import (')
        lines.append('    CtaTemplate,')
        lines.append('    StopOrder,')
        lines.append('    TickData,')
        lines.append('    BarData,')
        lines.append('    TradeData,')
        lines.append('    OrderData,')
        lines.append('    BarGenerator,')
        lines.append('    ArrayManager')
        lines.append(')')
        lines.append('')
        lines.append('from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV')
        lines.append('from mflang.functions import BP, BPK, SPK')
        lines.append('from mflang.import_parser import ImportParser, PeriodType')
        lines.append('from mflang.model_loader import load_model')
        lines.append('from vnpy.trader.constant import Interval, Direction, Offset')
        lines.append('from vnpy.trader.database import get_database')
        lines.append('from indicators import IndicatorManager')
        lines.append('from typing import List')
        lines.append('import numpy as np')
        lines.append('')
        
        # 策略类定义
        lines.append(f'class {strategy_class_name}(CtaTemplate):')
        lines.append(f'    """基于模型文件 {model_name} 生成的策略"""')
        lines.append('')
        
        # 作者
        lines.append(f'    author = "{author}"')
        lines.append('')
        
        # 参数和变量
        lines.append('    # 策略参数')
        lines.append('    parameters = [')
        lines.append('        "fixed_size",      # 固定交易手数')
        lines.append('        "stop_loss_pct",   # 止损百分比（如0.02表示2%）')
        lines.append('        "take_profit_pct", # 止盈百分比（如0.04表示4%）')
        lines.append('        "max_daily_trades", # 每日最大交易次数')
        lines.append('        "max_consecutive_losses", # 最大连续亏损次数')
        lines.append('    ]')
        lines.append('')
        lines.append('    # 参数默认值')
        lines.append('    fixed_size: int = 1')
        lines.append('    stop_loss_pct: float = 0.02  # 2%止损')
        lines.append('    take_profit_pct: float = 0.04  # 4%止盈')
        lines.append('    max_daily_trades: int = 10')
        lines.append('    max_consecutive_losses: int = 5')
        lines.append('')
        lines.append('    # 策略变量')
        variables_list = [f'"{var.name}"' for var in variables_info]
        # 添加风控相关变量
        lines.append('    variables = [')
        lines.append('        ' + ', '.join(variables_list) + ',')
        lines.append('        "entry_price",      # 开仓价格')
        lines.append('        "long_stop",        # 多头止损价')
        lines.append('        "short_stop",       # 空头止损价')
        lines.append('        "daily_trade_count", # 每日交易次数')
        lines.append('        "consecutive_losses", # 连续亏损次数')
        lines.append('        "total_trades",     # 总交易次数')
        lines.append('        "win_trades",       # 盈利交易次数')
        lines.append('        "last_trade_date",  # 上次交易日期')
        lines.append('    ]')
        lines.append('')
        
        # 变量初始化
        for var in variables_info:
            lines.append(f'    {var.name} = 0.0')
        lines.append('')
        
        # 风控相关变量初始化
        lines.append('    # 风控相关变量')
        lines.append('    entry_price = 0.0')
        lines.append('    long_stop = 0.0')
        lines.append('    short_stop = 0.0')
        lines.append('    daily_trade_count = 0')
        lines.append('    consecutive_losses = 0')
        lines.append('    total_trades = 0')
        lines.append('    win_trades = 0')
        lines.append('    last_trade_date = None')
        lines.append('')
        
        # T_COMMAND 设置的手数（如果存在）
        if t_command_volume is not None:
            lines.append(f'    # T_COMMAND 设置的手数: {t_command_volume}')
            lines.append(f'    t_command_volume = {t_command_volume}')
        else:
            lines.append('    # 未设置 T_COMMAND，使用固定手数')
            lines.append('    t_command_volume = None')
        lines.append('')
        
        # __init__ 方法
        lines.append('    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):')
        lines.append('        """初始化策略"""')
        lines.append('        super().__init__(cta_engine, strategy_name, vt_symbol, setting)')
        lines.append('        ')
        lines.append('        # K线管理器（1分钟K线）')
        lines.append('        self.bg = BarGenerator(self.on_bar)')
        lines.append('        self.am = ArrayManager()')
        lines.append('        ')
        
        # 创建 IndicatorManager（用于跨周期指标管理）
        if import_statements:
            lines.append('        # 创建 IndicatorManager 用于管理跨周期指标')
            lines.append('        self.indicator_manager = IndicatorManager(')
            lines.append('            vt_symbol=self.vt_symbol,')
            lines.append('            storage_path=None,  # 使用默认路径 .vntrader/indicators/')
            lines.append('            use_database=True  # 使用数据库加载历史数据')
            lines.append('        )')
            lines.append('        ')
        
        # 跨周期数据管理器
        if import_statements:
            lines.append('        # 跨周期数据管理器')
            lines.append('        # 根据 PERIOD 和 N 的组合创建 BarGenerator 和 ArrayManager，相同周期的引用共享')
            # 收集所有唯一的周期组合
            period_managers = {}  # key: period_key, value: list of stmt
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            # 为每个唯一的周期组合创建 BarGenerator 和 ArrayManager
            for period_key, stmts in period_managers.items():
                # 使用第一个 stmt 的信息作为代表（它们都有相同的 PERIOD 和 N）
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                manager_name = f"{period_type.lower()}_{period_n}_am"
                bg_name = f"bg_{period_type.lower()}_{period_n}"
                callback_name = f"on_{period_type.lower()}_{period_n}_bar"
                
                # 根据周期类型确定 Interval 和 window
                if period_type == "MIN":
                    interval = "Interval.MINUTE"
                    window = period_n
                    lines.append(f'        # {period_type}{period_n}周期 BarGenerator 和 ArrayManager')
                    lines.append(f'        self.{bg_name} = BarGenerator(self.on_bar, {window}, self.{callback_name})')
                    lines.append(f'        self.{manager_name} = ArrayManager()  # {period_type}{period_n}周期数据（共享）')
                elif period_type == "HOUR" or period_type == "CUSHOUR":
                    interval = "Interval.HOUR"
                    window = period_n
                    lines.append(f'        # {period_type}{period_n}周期 BarGenerator 和 ArrayManager')
                    lines.append(f'        self.{bg_name} = BarGenerator(self.on_bar, {window}, self.{callback_name}, {interval})')
                    lines.append(f'        self.{manager_name} = ArrayManager()  # {period_type}{period_n}周期数据（共享）')
                elif period_type == "DAY":
                    interval = "Interval.DAILY"
                    lines.append(f'        # {period_type}周期 BarGenerator 和 ArrayManager')
                    lines.append(f'        from datetime import time')
                    lines.append(f'        self.{bg_name} = BarGenerator(self.on_bar, 0, self.{callback_name}, {interval}, daily_end=time(15, 0))')
                    lines.append(f'        self.{manager_name} = ArrayManager()  # {period_type}周期数据（共享）')
                else:
                    # 其他周期类型暂时不支持 BarGenerator，只创建 ArrayManager
                    lines.append(f'        # {period_type}{period_n}周期 ArrayManager（不支持 BarGenerator 合成）')
                    lines.append(f'        self.{manager_name} = ArrayManager()  # {period_type}{period_n}周期数据（共享）')
            lines.append('        ')
            lines.append('        # 跨周期变量缓存（每个 var_name 有独立的缓存）')
            for stmt in import_statements:
                lines.append(f'        self.{stmt.var_name.lower()}_vars = {{}}  # {stmt.var_name} 的变量缓存')
            lines.append('        ')
        
        lines.append('        # 解析 #IMPORT 语句')
        lines.append(f'        self.import_statements = ImportParser.parse_code("""')
        for stmt in import_statements:
            lines.append(f'        {stmt}')
        lines.append('        """)')
        lines.append('        ')
        lines.append('        # 加载被引用的模型文件')
        for stmt in import_statements:
            lines.append(f'        self.{stmt.var_name.lower()}_model = load_model("{stmt.formula}")')
        lines.append('')
        
        # on_init 方法
        lines.append('    def on_init(self):')
        lines.append('        """策略初始化回调"""')
        lines.append('        self.write_log("策略初始化")')
        lines.append('        ')
        
        # 注册跨周期指标
        if import_statements:
            # 收集所有唯一的周期组合和对应的模型
            period_models = {}  # key: period_key, value: list of (stmt, model_vars)
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_models:
                    period_models[period_key] = []
                # 加载模型文件获取变量定义
                model_vars = self.model_loader.load_model(stmt.formula)
                period_models[period_key].append((stmt, model_vars))
            
            # 为每个周期注册指标
            for period_key, stmt_models in period_models.items():
                first_stmt = stmt_models[0][0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                
                # 确定 Interval
                interval = self._get_interval_string(period_type, period_n)
                
                # 为每个模型变量注册指标
                for stmt, model_vars in stmt_models:
                    for var_name, var_expr in model_vars.items():
                        # 生成指标计算函数名
                        func_name = f"_calculate_{stmt.formula.lower()}_{var_name.lower()}"
                        lines.append(f'        # 注册 {stmt.var_name}.{var_name} 指标（{period_type}{period_n}周期）')
                        lines.append(f'        self.indicator_manager.register_indicator(')
                        lines.append(f'            interval={interval},')
                        lines.append(f'            indicator_name="{stmt.var_name}.{var_name}",')
                        lines.append(f'            calculator=self.{func_name},')
                        lines.append(f'            max_history=10000')
                        lines.append(f'        )')
            
            lines.append('        ')
            lines.append('        # 初始化指标（加载历史数据并计算）')
            lines.append('        # 获取数据库（兼容回测和实盘环境）')
            lines.append('        try:')
            lines.append('            # 实盘环境：从 cta_engine 获取数据库')
            lines.append('            database = self.cta_engine.database')
            lines.append('            # 实盘环境不使用快速模式，直接加载完整数据')
            lines.append('            is_backtesting = False')
            lines.append('        except AttributeError:')
            lines.append('            # 回测环境：使用 get_database() 函数')
            lines.append('            database = get_database()')
            lines.append('            # 回测环境使用快速模式：先加载30天数据快速初始化，然后在后台继续加载完整数据')
            lines.append('            is_backtesting = True')
            for period_key, stmt_models in period_models.items():
                first_stmt = stmt_models[0][0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                interval = self._get_interval_string(period_type, period_n)
                lines.append(f'        self.indicator_manager.initialize_indicators(')
                lines.append(f'            {interval},')
                lines.append(f'            days=365,  # 加载1年历史数据')
                lines.append(f'            database=database,')
                lines.append(f'            fast_mode=is_backtesting,  # 回测环境使用快速模式')
                lines.append(f'            fast_days=30  # 快速模式先加载30天数据')
                lines.append(f'        )')
        
        lines.append('        ')
        lines.append('        self.load_bar(10)  # 加载10根K线')
        lines.append('')
        
        # on_start 方法
        lines.append('    def on_start(self):')
        lines.append('        """策略启动回调"""')
        lines.append('        self.write_log("策略启动")')
        lines.append('')
        
        # on_stop 方法
        lines.append('    def on_stop(self):')
        lines.append('        """策略停止回调"""')
        lines.append('        self.write_log("策略停止")')
        lines.append('        ')
        
        # 保存指标数据
        if import_statements:
            period_managers = {}
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            for period_key, stmts in period_managers.items():
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                interval = self._get_interval_string(period_type, period_n)
                lines.append(f'        # 保存{period_type}{period_n}周期的指标数据')
                lines.append(f'        self.indicator_manager._save_indicator_to_file({interval})')
        
        lines.append('        ')
        lines.append('        # 输出交易统计')
        lines.append('        if self.total_trades > 0:')
        lines.append('            win_rate = self.win_trades / self.total_trades * 100')
        lines.append('            self.write_log(f"交易统计: 总交易次数={self.total_trades}, 盈利次数={self.win_trades}, 胜率={win_rate:.2f}%")')
        lines.append('        ')
        lines.append('        # 更新UI显示')
        lines.append('        self.put_event()')
        lines.append('')
        
        # on_trade 方法
        lines.append('    def on_trade(self, trade: TradeData):')
        lines.append('        """成交回调"""')
        lines.append('        # 更新交易统计')
        lines.append('        if self.entry_price > 0:')
        lines.append('            # 计算盈亏')
        lines.append('            if trade.direction == Direction.LONG:')
        lines.append('                # 买入成交（开仓或平空）')
        lines.append('                if trade.offset == Offset.OPEN:')
        lines.append('                    # 买入开仓，记录开仓价格')
        lines.append('                    self.entry_price = trade.price')
        lines.append('                elif trade.offset == Offset.CLOSE:')
        lines.append('                    # 买入平仓，计算盈亏')
        lines.append('                    if self.entry_price > 0:')
        lines.append('                        pnl = (self.entry_price - trade.price) * trade.volume')
        lines.append('                        self.total_trades += 1')
        lines.append('                        if pnl > 0:')
        lines.append('                            self.win_trades += 1')
        lines.append('                            self.consecutive_losses = 0')
        lines.append('                        else:')
        lines.append('                            self.consecutive_losses += 1')
        lines.append('                        self.entry_price = 0.0  # 重置开仓价格')
        lines.append('            elif trade.direction == Direction.SHORT:')
        lines.append('                # 卖出成交（开仓或平多）')
        lines.append('                if trade.offset == Offset.OPEN:')
        lines.append('                    # 卖出开仓，记录开仓价格')
        lines.append('                    self.entry_price = trade.price')
        lines.append('                elif trade.offset == Offset.CLOSE:')
        lines.append('                    # 卖出平仓，计算盈亏')
        lines.append('                    if self.entry_price > 0:')
        lines.append('                        pnl = (trade.price - self.entry_price) * trade.volume')
        lines.append('                        self.total_trades += 1')
        lines.append('                        if pnl > 0:')
        lines.append('                            self.win_trades += 1')
        lines.append('                            self.consecutive_losses = 0')
        lines.append('                        else:')
        lines.append('                            self.consecutive_losses += 1')
        lines.append('                        self.entry_price = 0.0  # 重置开仓价格')
        lines.append('        ')
        lines.append('        # 更新UI显示')
        lines.append('        self.put_event()')
        lines.append('')
        
        # on_tick 方法
        lines.append('    def on_tick(self, tick: TickData):')
        lines.append('        """Tick数据回调"""')
        lines.append('        self.bg.update_tick(tick)')
        # 更新所有跨周期的 BarGenerator
        if import_statements:
            period_managers = {}
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            for period_key, stmts in period_managers.items():
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                if period_type in ["MIN", "HOUR", "CUSHOUR", "DAY"]:
                    bg_name = f"bg_{period_type.lower()}_{period_n}"
                    lines.append(f'        self.{bg_name}.update_tick(tick)')
        lines.append('')
        
        # on_bar 方法
        lines.append('    def on_bar(self, bar: BarData):')
        lines.append('        """1分钟K线数据回调"""')
        lines.append('        self.am.update_bar(bar)')
        lines.append('        ')
        # 将1分钟K线推送到跨周期 BarGenerator
        if import_statements:
            period_managers = {}
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            for period_key, stmts in period_managers.items():
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                if period_type in ["MIN", "HOUR", "CUSHOUR", "DAY"]:
                    bg_name = f"bg_{period_type.lower()}_{period_n}"
                    lines.append(f'        # 将1分钟K线推送到{period_type}{period_n}周期BarGenerator')
                    lines.append(f'        self.{bg_name}.update_bar(bar)')
        lines.append('        ')
        lines.append('        if not self.am.inited:')
        lines.append('            return')
        lines.append('        ')
        lines.append('        # 重置每日交易计数和连续亏损计数（如果是新的一天）')
        lines.append('        current_date = bar.datetime.date()')
        lines.append('        if self.last_trade_date != current_date:')
        lines.append('            self.daily_trade_count = 0')
        lines.append('            self.consecutive_losses = 0  # 每日重置连续亏损计数')
        lines.append('            self.last_trade_date = current_date')
        lines.append('        ')
        # 更新跨周期指标的运行时值（基于正在聚合的K线）
        if import_statements:
            period_managers = {}
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            for period_key, stmts in period_managers.items():
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                if period_type in ["MIN", "HOUR", "CUSHOUR", "DAY"]:
                    bg_name = f"bg_{period_type.lower()}_{period_n}"
                    interval = self._get_interval_string(period_type, period_n)
                    
                    # 更新运行时指标值（基于正在聚合的K线）
                    lines.append(f'        # 更新{period_type}{period_n}周期的运行时指标值（基于正在聚合的K线）')
                    lines.append(f'        if hasattr(self.{bg_name}, \'window_bar\') and self.{bg_name}.window_bar is not None:')
                    # 为每个模型变量更新运行时指标（每个指标名称调用一次）
                    indicator_names = set()
                    for stmt in stmts:
                        model_vars = self.model_loader.load_model(stmt.formula)
                        for var_name, var_expr in model_vars.items():
                            indicator_name = f"{stmt.var_name}.{var_name}"
                            if indicator_name not in indicator_names:
                                indicator_names.add(indicator_name)
                                lines.append(f'            # 更新指标 {indicator_name}')
                                lines.append(f'            self.indicator_manager.update_indicator(')
                                lines.append(f'                {interval},')
                                lines.append(f'                self.{bg_name}.window_bar,')
                                lines.append(f'                is_runtime=True')
                                lines.append(f'            )')
        lines.append('        ')
        
        # 计算变量
        lines.append('        # 计算策略变量')
        for var in variables_info:
            if var.uses_cross_period:
                lines.append(f'        # 计算 {var.name}: {var.expression}')
                lines.append(f'        self.{var.name} = self._calculate_variable_{var.name.lower()}()')
            else:
                lines.append(f'        # 计算 {var.name}: {var.expression}')
                lines.append(f'        self.{var.name} = self._calculate_variable_{var.name.lower()}()')
        lines.append('        ')
        lines.append('        # 调试日志：输出关键变量值（每10根K线输出一次）')
        lines.append('        # 已注释，避免日志刷屏')
        # 收集所有跨周期引用变量名（用于判断是否需要生成调试代码）
        cross_period_var_names = set()
        for var in variables_info:
            if var.uses_cross_period:
                for ref in var.cross_period_refs:
                    var_ref = ref.split('.')[0]
                    cross_period_var_names.add(var_ref.lower())
        
        # 注释掉整个调试日志块
        if cross_period_var_names:
            # 构建调试日志，显示跨周期变量（通过 IndicatorManager 获取）
            # 获取第一个跨周期引用用于显示
            first_ref = None
            first_var_ref = None
            first_field = None
            for var in variables_info:
                if var.uses_cross_period and var.cross_period_refs:
                    first_ref = var.cross_period_refs[0]
                    first_var_ref, first_field = first_ref.split('.')
                    break
            
            if first_ref:
                # 找到对应的 IMPORT 语句以确定周期
                import_stmt = None
                for stmt in import_statements:
                    if stmt.var_name == first_var_ref:
                        import_stmt = stmt
                        break
                
                if import_stmt:
                    period_type = import_stmt.period.value
                    period_n = import_stmt.n
                    interval = self._get_interval_string(period_type, period_n)
                    
                    indicator_name = f"{first_var_ref}.{first_field}"
                    lines.append('        # if len(self.am.close) % 10 == 0:')
                    lines.append(f'        #     # 获取跨周期变量 {first_ref}（通过 IndicatorManager）')
                    lines.append(f'        #     {first_field.lower()}_value = self.indicator_manager.get_indicator_smart(')
                    lines.append(f'        #         {interval},')
                    lines.append(f'        #         "{indicator_name}",')
                    lines.append(f'        #         prefer_runtime=True,')
                    lines.append(f'        #         fallback_to_history=True,')
                    lines.append(f'        #         history_index=-1,')
                    lines.append(f'        #         wait_if_not_ready=True,   # 如果指标未初始化完成，等待')
                    lines.append(f'        #         wait_timeout=1.0          # 最多等待1秒')
                    lines.append(f'        #     )')
                    lines.append(f'        #     {first_field.lower()}_str = f"{{{first_field.lower()}_value:.2f}}" if {first_field.lower()}_value is not None and not np.isnan({first_field.lower()}_value) else "NaN"')
                    lines.append(f'        #     self.write_log(f"调试: C={{self.CC:.2f}}, ISBUYTREND={{self.ISBUYTREND}}, {first_var_ref}.{first_field}={{{first_field.lower()}_str}}, BPK_SIGNAL={{self.BPK_SIGNAL}}, SPK_SIGNAL={{self.SPK_SIGNAL}}, pos={{self.pos}}")')
                else:
                    # 如果找不到对应的 IMPORT 语句，使用旧方法（向后兼容）
                    lines.append('        # if len(self.am.close) % 10 == 0:')
                    lines.append(f'        #     {first_var_ref.lower()}_vars = getattr(self, "{first_var_ref.lower()}_vars", {{}})')
                    lines.append(f'        #     prev_open = {first_var_ref.lower()}_vars.get("{first_field}", np.nan)')
                    lines.append(f'        #     prev_open_str = f"{{prev_open:.2f}}" if not np.isnan(prev_open) else "NaN"')
                    lines.append(f'        #     self.write_log(f"调试: C={{self.CC:.2f}}, ISBUYTREND={{self.ISBUYTREND}}, {first_var_ref}.{first_field}={{prev_open_str}}, BPK_SIGNAL={{self.BPK_SIGNAL}}, SPK_SIGNAL={{self.SPK_SIGNAL}}, pos={{self.pos}}")')
            else:
                lines.append('        # if len(self.am.close) % 10 == 0:')
                lines.append('        #     self.write_log(f"调试: C={self.CC:.2f}, ISBUYTREND={self.ISBUYTREND}, BPK_SIGNAL={self.BPK_SIGNAL}, SPK_SIGNAL={self.SPK_SIGNAL}, pos={self.pos}")')
        else:
            lines.append('        # if len(self.am.close) % 10 == 0:')
            lines.append('        #     self.write_log(f"调试: C={self.CC:.2f}, ISBUYTREND={self.ISBUYTREND}, BPK_SIGNAL={self.BPK_SIGNAL}, SPK_SIGNAL={self.SPK_SIGNAL}, pos={self.pos}")')
        lines.append('        ')
        lines.append('        # 只有在策略启动后才执行交易逻辑')
        lines.append('        # 避免在初始化阶段（load_bar回放历史数据时）触发交易')
        lines.append('        if self.trading:')
        lines.append('            # 检查止损止盈（风控逻辑）')
        lines.append('            self._check_risk_control(bar)')
        lines.append('            ')
        lines.append('            # 策略逻辑')
        lines.append('            self._on_strategy_logic(bar)')
        lines.append('        ')
        lines.append('        # 更新UI显示')
        lines.append('        self.put_event()')
        lines.append('')
        
        # 添加跨周期K线回调函数
        if import_statements:
            period_managers = {}
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            for period_key, stmts in period_managers.items():
                first_stmt = stmts[0]
                period_type = first_stmt.period.value
                period_n = first_stmt.n
                callback_name = f"on_{period_type.lower()}_{period_n}_bar"
                manager_name = f"{period_type.lower()}_{period_n}_am"
                
                lines.append(f'    def {callback_name}(self, bar: BarData):')
                lines.append(f'        """{period_type}{period_n}周期K线数据回调（由BarGenerator合成）"""')
                lines.append(f'        # 更新{period_type}{period_n}周期ArrayManager')
                lines.append(f'        self.{manager_name}.update_bar(bar)')
                lines.append('        ')
                lines.append(f'        if not self.{manager_name}.inited:')
                lines.append('            return')
                lines.append('        ')
                
                # 确定 Interval
                interval = self._get_interval_string(period_type, period_n)
                
                # 更新历史指标值（5分钟K线收盘时）
                lines.append(f'        # 更新{period_type}{period_n}周期的历史指标值（K线已完成）')
                indicator_names = set()
                for stmt in stmts:
                    model_vars = self.model_loader.load_model(stmt.formula)
                    for var_name, var_expr in model_vars.items():
                        indicator_name = f"{stmt.var_name}.{var_name}"
                        if indicator_name not in indicator_names:
                            indicator_names.add(indicator_name)
                            lines.append(f'        self.indicator_manager.update_indicator(')
                            lines.append(f'            {interval},')
                            lines.append(f'            bar,')
                            lines.append(f'            is_runtime=False  # 历史值：K线已完成')
                            lines.append(f'        )')
                lines.append('')
        
        # 风控方法
        lines.append('    def _check_risk_control(self, bar: BarData):')
        lines.append('        """')
        lines.append('        默认风控逻辑')
        lines.append('        后续可以在模型文件中定义自定义风控逻辑来覆盖此方法')
        lines.append('        """')
        lines.append('        if self.pos == 0:')
        lines.append('            return')
        lines.append('        ')
        lines.append('        # 计算当前浮动盈亏百分比')
        lines.append('        if self.entry_price > 0:')
        lines.append('            if self.pos > 0:  # 多头持仓')
        lines.append('                pnl_pct = (bar.close_price - self.entry_price) / self.entry_price')
        lines.append('                # 止损检查')
        lines.append('                if pnl_pct <= -self.stop_loss_pct:')
        lines.append('                    self.write_log(f"触发止损: 浮动盈亏={pnl_pct*100:.2f}%, 止损比例={self.stop_loss_pct*100:.2f}%")')
        lines.append('                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                        self.sell(bar.close_price, abs(self.pos))')
        lines.append('                    return')
        lines.append('                # 止盈检查')
        lines.append('                if pnl_pct >= self.take_profit_pct:')
        lines.append('                    self.write_log(f"触发止盈: 浮动盈亏={pnl_pct*100:.2f}%, 止盈比例={self.take_profit_pct*100:.2f}%")')
        lines.append('                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                        self.sell(bar.close_price, abs(self.pos))')
        lines.append('                    return')
        lines.append('            elif self.pos < 0:  # 空头持仓')
        lines.append('                pnl_pct = (self.entry_price - bar.close_price) / self.entry_price')
        lines.append('                # 止损检查')
        lines.append('                if pnl_pct <= -self.stop_loss_pct:')
        lines.append('                    self.write_log(f"触发止损: 浮动盈亏={pnl_pct*100:.2f}%, 止损比例={self.stop_loss_pct*100:.2f}%")')
        lines.append('                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                        self.cover(bar.close_price, abs(self.pos))')
        lines.append('                    return')
        lines.append('                # 止盈检查')
        lines.append('                if pnl_pct >= self.take_profit_pct:')
        lines.append('                    self.write_log(f"触发止盈: 浮动盈亏={pnl_pct*100:.2f}%, 止盈比例={self.take_profit_pct*100:.2f}%")')
        lines.append('                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                        self.cover(bar.close_price, abs(self.pos))')
        lines.append('                    return')
        lines.append('')
        
        # 辅助方法：判断是否是目标周期K线
        if import_statements:
            lines.append('    def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:')
            lines.append('        """')
            lines.append('        判断是否是目标周期的K线')
            lines.append('        ')
            lines.append('        参数:')
            lines.append('            period_type: 周期类型（来自 #IMPORT 语句的 PERIOD，如 "MIN", "HOUR", "DAY"）')
            lines.append('            n: 周期参数（来自 #IMPORT 语句的 N，如 5 表示5分钟）')
            lines.append('        ')
            lines.append('        说明:')
            lines.append('            根据 #IMPORT 语句中的 PERIOD 和 N 来判断当前K线是否为目标周期')
            lines.append('            例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5')
            lines.append('                 PERIOD=MIN, N=5，表示需要5分钟周期的数据')
            lines.append('                 判断条件：bar.datetime.minute % 5 == 0')
            lines.append('        """')
            lines.append('        if period_type == "MIN":')
            lines.append('            # 分钟周期：判断分钟数是否能被N整除')
            lines.append('            # 例如：N=5 表示5分钟周期，分钟数 % 5 == 0 时是5分钟K线')
            lines.append('            return bar.datetime.minute % n == 0')
            lines.append('        elif period_type == "HOUR":')
            lines.append('            # 小时周期：判断小时数是否能被N整除，且分钟数为0')
            lines.append('            # 例如：N=2 表示2小时周期，小时数 % 2 == 0 且分钟数为0时是2小时K线')
            lines.append('            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "CUSHOUR":')
            lines.append('            # 自定义小时周期：判断小时数是否能被N整除，且分钟数为0')
            lines.append('            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "DAY":')
            lines.append('            # 日周期：判断是否是交易日开始（小时数为0，分钟数为0）')
            lines.append('            return bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "WEEK":')
            lines.append('            # 周周期：判断是否是周一且小时数为0，分钟数为0')
            lines.append('            return bar.datetime.weekday() == 0 and bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "MONTH":')
            lines.append('            # 月周期：判断是否是月初且小时数为0，分钟数为0')
            lines.append('            return bar.datetime.day == 1 and bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "QUARTER":')
            lines.append('            # 季度周期：判断是否是季度初且小时数为0，分钟数为0')
            lines.append('            # 季度初：1月、4月、7月、10月的1号')
            lines.append('            return (bar.datetime.month in [1, 4, 7, 10] and ')
            lines.append('                    bar.datetime.day == 1 and ')
            lines.append('                    bar.datetime.hour == 0 and ')
            lines.append('                    bar.datetime.minute == 0)')
            lines.append('        elif period_type == "YEAR":')
            lines.append('            # 年周期：判断是否是年初且小时数为0，分钟数为0')
            lines.append('            return (bar.datetime.month == 1 and ')
            lines.append('                    bar.datetime.day == 1 and ')
            lines.append('                    bar.datetime.hour == 0 and ')
            lines.append('                    bar.datetime.minute == 0)')
            lines.append('        else:')
            lines.append('            # 其他周期类型，需要根据实际情况实现')
            lines.append('            return False')
            lines.append('')
        
        # 辅助方法：计算跨周期变量
        if import_statements:
            lines.append('    def _calculate_cross_period_vars(self, var_name: str, model_name: str, period_type: str, period_n: int):')
            lines.append('        """')
            lines.append('        计算跨周期变量')
            lines.append('        ')
            lines.append('        参数:')
            lines.append('            var_name: 跨周期变量名（如 "MIN5"），来自 #IMPORT 语句的 VAR')
            lines.append('            model_name: 模型文件名（如 "MIN5_OPEN"），来自 #IMPORT 语句的 FORMULA')
            lines.append('            period_type: 周期类型（如 "MIN"），来自 #IMPORT 语句的 PERIOD')
            lines.append('            period_n: 周期参数（如 5），来自 #IMPORT 语句的 N')
            lines.append('        ')
            lines.append('        说明:')
            lines.append('            通过 PERIOD 和 N 来确定 ArrayManager，而不是通过 var_name')
            lines.append('            - 相同 PERIOD 和 N 的 #IMPORT 语句共享同一个 ArrayManager')
            lines.append('            - ArrayManager 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）')
            lines.append('            - 每个 var_name 有独立的变量缓存（vars_cache）')
            lines.append('        """')
            lines.append('        # 加载模型文件')
            lines.append('        model = load_model(model_name)')
            lines.append('        ')
            lines.append('        # 根据 PERIOD 和 N 获取对应的 ArrayManager')
            lines.append('        # 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）')
            lines.append('        # 相同周期的引用共享同一个 ArrayManager')
            lines.append('        period_key = f"{period_type.lower()}_{period_n}"')
            lines.append('        am = getattr(self, f"{period_key}_am")')
            lines.append('        ')
            lines.append('        # 计算模型中的变量')
            lines.append('        vars_cache = {}')
            lines.append('        for var_name_in_model, var_expr in model.items():')
            lines.append('            # 解析并计算变量')
            lines.append('            # 这里需要根据表达式类型执行相应的计算')
            lines.append('            # 示例：处理 REF(O,1)')
            lines.append('            var_expr_clean = var_expr.strip()')
            lines.append('            if "REF(O,1)" in var_expr_clean or "REF(O, 1)" in var_expr_clean:')
            lines.append('                if len(am.open) < 2:')
            lines.append('                    vars_cache[var_name_in_model] = np.nan')
            lines.append('                else:')
            lines.append('                    open_prices = am.open')
            lines.append('                    result = REF(open_prices, 1)')
            lines.append('                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan')
            lines.append('            elif "REF(C,1)" in var_expr_clean or "REF(C, 1)" in var_expr_clean:')
            lines.append('                if len(am.close) < 2:')
            lines.append('                    vars_cache[var_name_in_model] = np.nan')
            lines.append('                else:')
            lines.append('                    close_prices = am.close')
            lines.append('                    result = REF(close_prices, 1)')
            lines.append('                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan')
            lines.append('            elif var_expr_clean == "C":')
            lines.append('                vars_cache[var_name_in_model] = am.close[-1] if len(am.close) > 0 else np.nan')
            lines.append('            elif var_expr_clean == "O":')
            lines.append('                vars_cache[var_name_in_model] = am.open[-1] if len(am.open) > 0 else np.nan')
            lines.append('            else:')
            lines.append('                # 默认返回 NaN，避免未处理的表达式导致错误')
            lines.append('                vars_cache[var_name_in_model] = np.nan')
            lines.append('        ')
            lines.append('        # 缓存结果')
            lines.append('        setattr(self, f"{var_name.lower()}_vars", vars_cache)')
            lines.append('        ')
            lines.append('        # 调试日志：输出跨周期变量值')
            lines.append('        # 已注释，避免日志刷屏')
            lines.append('        # if vars_cache:')
            lines.append('        #     for k, v in vars_cache.items():')
            lines.append('        #         if not np.isnan(v):')
            lines.append('        #             self.write_log(f"跨周期变量 {var_name}.{k} = {v:.2f}")')
            lines.append('')
        
        # 辅助方法：生成指标计算函数
        if import_statements:
            # 收集所有唯一的周期组合和对应的模型
            period_models = {}  # key: period_key, value: list of (stmt, model_vars)
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_models:
                    period_models[period_key] = []
                # 加载模型文件获取变量定义
                model_vars = self.model_loader.load_model(stmt.formula)
                period_models[period_key].append((stmt, model_vars))
            
            # 为每个模型变量生成指标计算函数
            for period_key, stmt_models in period_models.items():
                for stmt, model_vars in stmt_models:
                    for var_name, var_expr in model_vars.items():
                        lines.append(self._generate_indicator_calculator(stmt.formula, var_name, var_expr))
        
        # 辅助方法：计算各个变量
        for var in variables_info:
            lines.append(f'    def _calculate_variable_{var.name.lower()}(self) -> float:')
            lines.append(f'        """计算变量 {var.name}: {var.expression}"""')
            
            if var.uses_cross_period:
                # 使用跨周期引用（通过 IndicatorManager 获取）
                # 先获取所有跨周期引用变量
                cross_period_vars = {}
                for ref in var.cross_period_refs:
                    var_ref, var_field = ref.split('.')
                    # 找到对应的 IMPORT 语句以确定周期
                    import_stmt = None
                    for stmt in import_statements:
                        if stmt.var_name == var_ref:
                            import_stmt = stmt
                            break
                    
                    if import_stmt:
                        period_type = import_stmt.period.value
                        period_n = import_stmt.n
                        interval = self._get_interval_string(period_type, period_n)
                        
                        indicator_name = f"{var_ref}.{var_field}"
                        lines.append(f'        # 获取跨周期引用 {ref}（通过 IndicatorManager）')
                        lines.append(f'        {var_field.lower()}_value = self.indicator_manager.get_indicator_smart(')
                        lines.append(f'            {interval},')
                        lines.append(f'            "{indicator_name}",')
                        lines.append(f'            prefer_runtime=True,      # 优先使用运行时值（正在聚合的K线）')
                        lines.append(f'            fallback_to_history=True, # 运行时值不存在时回退到历史值')
                        lines.append(f'            history_index=-1,         # 回退时使用最新历史值')
                        lines.append(f'            wait_if_not_ready=True,   # 如果指标未初始化完成，等待')
                        lines.append(f'            wait_timeout=1.0          # 最多等待1秒')
                        lines.append(f'        )')
                        lines.append(f'        if {var_field.lower()}_value is None:')
                        lines.append(f'            {var_field.lower()}_value = np.nan')
                        cross_period_vars[ref] = f'{var_field.lower()}_value'
                    else:
                        # 如果找不到对应的 IMPORT 语句，使用旧方法（向后兼容）
                        lines.append(f'        # 获取跨周期引用 {ref}（向后兼容）')
                        lines.append(f'        {var_ref.lower()}_vars = getattr(self, "{var_ref.lower()}_vars", {{}})')
                        lines.append(f'        {var_field.lower()}_value = {var_ref.lower()}_vars.get("{var_field}", np.nan)')
                        cross_period_vars[ref] = f'{var_field.lower()}_value'
                lines.append('        ')
                
                # 解析表达式并计算
                # 处理包含 AND 操作符的复杂表达式
                expr = var.expression.strip()
                
                # 检查是否包含 AND 操作符
                if ' AND ' in expr.upper() or ' AND' in expr.upper() or 'AND ' in expr.upper():
                    # 处理 AND 表达式，如 ISBUYTREND>0 AND C<MIN5.PREV_OPEN
                    # 按 AND 分割（不区分大小写）
                    import re
                    and_parts = re.split(r'\s+AND\s+', expr, flags=re.IGNORECASE)
                    
                    # 生成每个条件的代码
                    condition_results = []
                    for i, part in enumerate(and_parts):
                        part = part.strip()
                        cond_var = f'cond_{i}'
                        condition_results.append(cond_var)
                        
                        # 解析单个条件（可能是比较表达式）
                        if '>' in part:
                            if '>=' in part:
                                op = '>='
                                parts = part.split('>=')
                            else:
                                op = '>'
                                parts = part.split('>')
                        elif '<' in part:
                            if '<=' in part:
                                op = '<='
                                parts = part.split('<=')
                            else:
                                op = '<'
                                parts = part.split('<')
                        elif '==' in part or '=' in part:
                            op = '=='
                            parts = part.split('==') if '==' in part else part.split('=')
                        else:
                            # 简单变量，如 ISBUYTREND>0
                            if '>' in part:
                                parts = part.split('>')
                                op = '>'
                            elif '<' in part:
                                parts = part.split('<')
                                op = '<'
                            else:
                                # 无法解析，使用默认逻辑
                                lines.append(f'        # 无法解析表达式: {part}')
                                lines.append(f'        {cond_var} = False')
                                continue
                        
                        left = parts[0].strip()
                        right = parts[1].strip() if len(parts) > 1 else None
                        
                        # 处理左侧
                        if left == 'C':
                            lines.append(f'        left_{i} = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                            left_value = f'left_{i}'
                        elif left == 'O':
                            lines.append(f'        left_{i} = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                            left_value = f'left_{i}'
                        elif left == 'H':
                            lines.append(f'        left_{i} = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                            left_value = f'left_{i}'
                        elif left == 'L':
                            lines.append(f'        left_{i} = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                            left_value = f'left_{i}'
                        elif left.endswith('>0') or left.endswith('<=0'):
                            # 处理 ISBUYTREND>0 这种情况
                            var_name = left.rstrip('>0').rstrip('<=0').strip()
                            lines.append(f'        left_{i} = self.{var_name}')
                            left_value = f'left_{i}'
                            if '>0' in left:
                                op = '>'
                                right = '0'
                            elif '<=' in left:
                                op = '<='
                                right = '0'
                        else:
                            # 可能是变量名
                            if left in [v.name for v in variables_info]:
                                lines.append(f'        left_{i} = self.{left}')
                                left_value = f'left_{i}'
                            else:
                                left_value = left.lower().replace(' ', '_')
                                lines.append(f'        left_{i} = self.{left} if hasattr(self, "{left}") else 0.0')
                                left_value = f'left_{i}'
                        
                        # 处理右侧
                        if right:
                            if '.' in right:
                                # 跨周期引用，如 MIN5.PREV_OPEN
                                var_ref, var_field = right.split('.')
                                ref_key = f'{var_ref}.{var_field}'
                                if ref_key in var.cross_period_refs:
                                    right_value = f'{var_field.lower()}_value'
                                else:
                                    lines.append(f'        {var_ref.lower()}_vars_{i} = getattr(self, "{var_ref.lower()}_vars", {{}})')
                                    right_value = f'{var_ref.lower()}_vars_{i}.get("{var_field}", np.nan)'
                            elif right == 'C':
                                lines.append(f'        right_{i} = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                                right_value = f'right_{i}'
                            elif right == 'O':
                                lines.append(f'        right_{i} = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                                right_value = f'right_{i}'
                            elif right == 'H':
                                lines.append(f'        right_{i} = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                                right_value = f'right_{i}'
                            elif right == 'L':
                                lines.append(f'        right_{i} = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                                right_value = f'right_{i}'
                            elif right.isdigit() or (right.startswith('-') and right[1:].isdigit()):
                                right_value = right
                            else:
                                # 可能是变量名
                                if right in [v.name for v in variables_info]:
                                    lines.append(f'        right_{i} = self.{right}')
                                    right_value = f'right_{i}'
                                else:
                                    right_value = right.lower().replace(' ', '_')
                                    lines.append(f'        right_{i} = self.{right} if hasattr(self, "{right}") else 0.0')
                                    right_value = f'right_{i}'
                            
                            lines.append(f'        if np.isnan({left_value}) or np.isnan({right_value}):')
                            lines.append(f'            {cond_var} = False')
                            lines.append('        else:')
                            lines.append(f'            {cond_var} = {left_value} {op} {right_value}')
                        else:
                            # 只有左侧，可能是 ISBUYTREND>0 这种情况（已在上面处理）
                            lines.append(f'        {cond_var} = {left_value} {op} 0')
                    
                    # 组合所有条件
                    if condition_results:
                        all_conditions = ' and '.join(condition_results)
                        lines.append(f'        result = {all_conditions}')
                        lines.append('        return 1.0 if result else 0.0')
                    else:
                        lines.append('        return 0.0')
                elif '>' in expr or '<' in expr or '==' in expr or '=' in expr:
                    # 处理简单比较表达式，如 C > MIN5.PREV_OPEN
                    if '>=' in expr:
                        op = '>='
                        parts = expr.split('>=')
                    elif '<=' in expr:
                        op = '<='
                        parts = expr.split('<=')
                    elif '>' in expr:
                        op = '>'
                        parts = expr.split('>')
                    elif '<' in expr:
                        op = '<'
                        parts = expr.split('<')
                    elif '==' in expr:
                        op = '=='
                        parts = expr.split('==')
                    else:
                        op = '='
                        parts = expr.split('=')
                    
                    left = parts[0].strip()
                    right = parts[1].strip() if len(parts) > 1 else None
                    
                    # 处理左侧
                    if left == 'C':
                        lines.append('        current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                        left_value = 'current_close'
                    elif left == 'O':
                        lines.append('        current_open = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                        left_value = 'current_open'
                    elif left == 'H':
                        lines.append('        current_high = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                        left_value = 'current_high'
                    elif left == 'L':
                        lines.append('        current_low = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                        left_value = 'current_low'
                    elif left in [v.name for v in variables_info]:
                        lines.append(f'        left_val = self.{left}')
                        left_value = 'left_val'
                    else:
                        left_value = left.lower().replace(' ', '_')
                        lines.append(f'        left_val = self.{left} if hasattr(self, "{left}") else 0.0')
                        left_value = 'left_val'
                    
                    # 处理右侧
                    if right:
                        if '.' in right:
                            # 跨周期引用，如 MIN5.PREV_OPEN
                            var_ref, var_field = right.split('.')
                            ref_key = f'{var_ref}.{var_field}'
                            if ref_key in var.cross_period_refs:
                                right_value = f'{var_field.lower()}_value'
                            else:
                                lines.append(f'        {var_ref.lower()}_vars = getattr(self, "{var_ref.lower()}_vars", {{}})')
                                right_value = f'{var_ref.lower()}_vars.get("{var_field}", np.nan)'
                        elif right == 'C':
                            lines.append('        right_value = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'O':
                            lines.append('        right_value = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'H':
                            lines.append('        right_value = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'L':
                            lines.append('        right_value = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right.isdigit() or (right.startswith('-') and right[1:].isdigit()):
                            right_value = right
                        elif right in [v.name for v in variables_info]:
                            lines.append(f'        right_value = self.{right}')
                            right_value = 'right_value'
                        else:
                            right_value = right.lower().replace(' ', '_')
                            lines.append(f'        right_value = self.{right} if hasattr(self, "{right}") else 0.0')
                            right_value = 'right_value'
                        
                        lines.append(f'        if np.isnan({left_value}) or np.isnan({right_value}):')
                        lines.append('            return 0.0')
                        lines.append(f'        result = {left_value} {op} {right_value}')
                        lines.append('        return 1.0 if result else 0.0')
                    else:
                        # 只有左侧，可能是 ISBUYTREND>0 这种情况
                        # 这种情况应该不会发生，因为表达式应该包含操作符
                        lines.append('        # 需要根据实际表达式实现计算逻辑')
                        lines.append('        return 0.0')
                else:
                    # 简单变量引用，如 ISBUYTREND
                    if expr in [v.name for v in variables_info]:
                        lines.append(f'        return self.{expr} if hasattr(self, "{expr}") else 0.0')
                    else:
                        lines.append('        # 需要根据实际表达式实现计算逻辑')
                        lines.append('        return 0.0')
            else:
                # 不使用跨周期引用
                expr = var.expression.strip()
                if expr == 'C':
                    lines.append('        return self.am.close[-1] if len(self.am.close) > 0 else 0.0')
                elif expr == 'O':
                    lines.append('        return self.am.open[-1] if len(self.am.open) > 0 else 0.0')
                elif expr == 'H':
                    lines.append('        return self.am.high[-1] if len(self.am.high) > 0 else 0.0')
                elif expr == 'L':
                    lines.append('        return self.am.low[-1] if len(self.am.low) > 0 else 0.0')
                elif '>' in expr or '<' in expr or '==' in expr or '=' in expr:
                    # 处理简单比较表达式，如 ISBUYTREND>0
                    if '>=' in expr:
                        op = '>='
                        parts = expr.split('>=')
                    elif '<=' in expr:
                        op = '<='
                        parts = expr.split('<=')
                    elif '>' in expr:
                        op = '>'
                        parts = expr.split('>')
                    elif '<' in expr:
                        op = '<'
                        parts = expr.split('<')
                    elif '==' in expr:
                        op = '=='
                        parts = expr.split('==')
                    else:
                        op = '='
                        parts = expr.split('=')
                    
                    left = parts[0].strip()
                    right = parts[1].strip() if len(parts) > 1 else None
                    
                    # 处理左侧
                    if left in [v.name for v in variables_info]:
                        lines.append(f'        left_val = self.{left}')
                        left_value = 'left_val'
                    elif left == 'C':
                        lines.append('        left_val = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                        left_value = 'left_val'
                    elif left == 'O':
                        lines.append('        left_val = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                        left_value = 'left_val'
                    elif left == 'H':
                        lines.append('        left_val = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                        left_value = 'left_val'
                    elif left == 'L':
                        lines.append('        left_val = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                        left_value = 'left_val'
                    else:
                        left_value = left.lower().replace(' ', '_')
                        lines.append(f'        left_val = self.{left} if hasattr(self, "{left}") else 0.0')
                        left_value = 'left_val'
                    
                    # 处理右侧
                    if right:
                        if right.isdigit() or (right.startswith('-') and right[1:].isdigit()):
                            right_value = right
                        elif right == 'C':
                            lines.append('        right_val = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                            right_value = 'right_val'
                        elif right == 'O':
                            lines.append('        right_val = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                            right_value = 'right_val'
                        elif right == 'H':
                            lines.append('        right_val = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                            right_value = 'right_val'
                        elif right == 'L':
                            lines.append('        right_val = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                            right_value = 'right_val'
                        elif right in [v.name for v in variables_info]:
                            lines.append(f'        right_val = self.{right}')
                            right_value = 'right_val'
                        else:
                            right_value = right.lower().replace(' ', '_')
                            lines.append(f'        right_val = self.{right} if hasattr(self, "{right}") else 0.0')
                            right_value = 'right_val'
                        
                        lines.append(f'        if np.isnan({left_value}) or np.isnan({right_value}):')
                        lines.append('            return 0.0')
                        lines.append(f'        result = {left_value} {op} {right_value}')
                        lines.append('        return 1.0 if result else 0.0')
                    else:
                        # 只有左侧，可能是 ISBUYTREND>0 这种情况
                        if '>' in left:
                            var_name = left.split('>')[0].strip()
                            lines.append(f'        var_val = self.{var_name} if hasattr(self, "{var_name}") else 0.0')
                            lines.append('        return 1.0 if var_val > 0 else 0.0')
                        elif '<=' in left:
                            var_name = left.split('<=')[0].strip()
                            lines.append(f'        var_val = self.{var_name} if hasattr(self, "{var_name}") else 0.0')
                            lines.append('        return 1.0 if var_val <= 0 else 0.0')
                        else:
                            lines.append('        # 需要根据实际表达式实现计算逻辑')
                            lines.append('        return 0.0')
                elif expr in [v.name for v in variables_info]:
                    # 简单变量引用
                    lines.append(f'        return self.{expr} if hasattr(self, "{expr}") else 0.0')
                else:
                    lines.append('        # 需要根据实际表达式实现计算逻辑')
                    lines.append('        return 0.0')
            lines.append('')
        
        # 策略逻辑方法
        lines.append('    def _on_strategy_logic(self, bar: BarData):')
        lines.append('        """策略逻辑"""')
        lines.append('        # 检查价格有效性')
        lines.append('        if bar.close_price is None or np.isnan(bar.close_price) or bar.close_price <= 0:')
        lines.append('            self.write_log(f"价格无效，跳过交易: close_price={bar.close_price}")')
        lines.append('            return')
        lines.append('        ')
        lines.append('        # 强制持仓限制：严格遵守只有一手持仓')
        lines.append('        # 如果持仓超过1手，强制平仓到1手')
        lines.append('        current_pos = self.pos')
        lines.append('        if current_pos > 1:')
        lines.append('            # 多仓超过1手，强制平仓到1手')
        lines.append('            excess_volume = current_pos - 1')
        lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                self.sell(bar.close_price, excess_volume)')
        lines.append('                self.write_log(f"强制平仓：多仓超过1手，平掉多余 {excess_volume} 手")')
        lines.append('        elif current_pos < -1:')
        lines.append('            # 空仓超过1手，强制平仓到1手')
        lines.append('            excess_volume = abs(current_pos) - 1')
        lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
        lines.append('                self.cover(bar.close_price, excess_volume)')
        lines.append('                self.write_log(f"强制平仓：空仓超过1手，平掉多余 {excess_volume} 手")')
        lines.append('        ')
        lines.append('        # 在这里实现策略的交易逻辑')
        lines.append('        # 可以使用计算好的变量进行判断')
        for var in variables_info:
            lines.append(f'        # {var.name} = self.{var.name}')
        lines.append('        ')
        
        # 处理交易指令
        trading_vars = [v for v in variables_info if v.trading_instruction is not None]
        if trading_vars:
            lines.append('        # 处理交易指令')
            for var in trading_vars:
                instr = var.trading_instruction
                if instr.instruction_type == 'BP':
                    # BP指令：买入平仓，平掉空头持仓
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    else:
                        lines.append(f'        # {instr.instruction_type}指令，平掉所有持仓')
                    
                    # 检查条件是否满足
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 风控检查：每日交易次数限制')
                    lines.append('            if self.daily_trade_count >= self.max_daily_trades:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 风控检查：连续亏损限制')
                    lines.append('            if self.consecutive_losses >= self.max_consecutive_losses:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 获取当前持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            ')
                    lines.append('            # BP指令：买入平仓，平掉空头持仓')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的平仓操作')
                    lines.append('            if pos < 0:  # 如果有空头持仓')
                    lines.append('                # 买入平仓，平掉所有空头持仓')
                    lines.append('                volume = abs(pos)  # 平仓数量为当前空头持仓的绝对值')
                    lines.append('                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                    self.cover(bar.close_price, volume)')
                    if instr.group:
                        lines.append(f'                self.write_log("BP指令({instr.group})触发: 买入平仓 %d 手" % volume)')
                    else:
                        lines.append('                self.write_log("BP指令触发: 买入平仓 %d 手" % volume)')
                    lines.append('        ')
                elif instr.instruction_type == 'SP':
                    # SP指令：卖出平仓，平掉多头持仓
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    else:
                        lines.append(f'        # {instr.instruction_type}指令，平掉所有持仓')
                    
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 获取当前持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            ')
                    lines.append('            # SP指令：卖出平仓，平掉多头持仓')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的平仓操作')
                    lines.append('            if pos > 0:  # 如果有多头持仓')
                    lines.append('                # 卖出平仓，平掉所有多头持仓')
                    lines.append('                volume = pos  # 平仓数量为当前多头持仓')
                    lines.append('                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                    self.sell(bar.close_price, volume)')
                    if instr.group:
                        lines.append(f'                self.write_log("SP指令({instr.group})触发: 卖出平仓 %d 手" % volume)')
                    else:
                        lines.append('                self.write_log("SP指令触发: 卖出平仓 %d 手" % volume)')
                    lines.append('        ')
                elif instr.instruction_type == 'BK':
                    # BK指令：买入开仓
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 风控检查：每日交易次数限制')
                    lines.append('            if self.daily_trade_count >= self.max_daily_trades:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 风控检查：连续亏损限制')
                    lines.append('            if self.consecutive_losses >= self.max_consecutive_losses:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 持仓检查：严格遵守只有一手持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            if pos != 0:  # 如果已有持仓，不允许开仓')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # BK指令：买入开仓')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的开仓操作')
                    lines.append('            # 买入开仓，确定交易手数：T_COMMAND 设置的手数优先于固定手数')
                    lines.append('            if self.t_command_volume is not None:')
                    lines.append('                volume = self.t_command_volume')
                    lines.append('            else:')
                    lines.append('                volume = self.fixed_size if hasattr(self, "fixed_size") else 1')
                    lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                self.buy(bar.close_price, volume)')
                    lines.append('                # 记录开仓价格')
                    lines.append('                self.entry_price = bar.close_price')
                    lines.append('                self.daily_trade_count += 1')
                    if instr.group:
                        lines.append(f'                self.write_log("BK指令({instr.group})触发: 买入开仓 %d 手, 开仓价=%.2f" % (volume, self.entry_price))')
                    else:
                        lines.append('                self.write_log("BK指令触发: 买入开仓 %d 手, 开仓价=%.2f" % (volume, self.entry_price))')
                    lines.append('        ')
                elif instr.instruction_type == 'SK':
                    # SK指令：卖出开仓
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 风控检查：每日交易次数限制')
                    lines.append('            if self.daily_trade_count >= self.max_daily_trades:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 风控检查：连续亏损限制')
                    lines.append('            if self.consecutive_losses >= self.max_consecutive_losses:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 持仓检查：严格遵守只有一手持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            if pos != 0:  # 如果已有持仓，不允许开仓')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # SK指令：卖出开仓')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的开仓操作')
                    lines.append('            # 卖出开仓，确定交易手数：T_COMMAND 设置的手数优先于固定手数')
                    lines.append('            if self.t_command_volume is not None:')
                    lines.append('                volume = self.t_command_volume')
                    lines.append('            else:')
                    lines.append('                volume = self.fixed_size if hasattr(self, "fixed_size") else 1')
                    lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                self.short(bar.close_price, volume)')
                    lines.append('                # 记录开仓价格')
                    lines.append('                self.entry_price = bar.close_price')
                    lines.append('                self.daily_trade_count += 1')
                    if instr.group:
                        lines.append(f'                self.write_log("SK指令({instr.group})触发: 卖出开仓 %d 手, 开仓价=%.2f" % (volume, self.entry_price))')
                    else:
                        lines.append('                self.write_log("SK指令触发: 卖出开仓 %d 手, 开仓价=%.2f" % (volume, self.entry_price))')
                    lines.append('        ')
                elif instr.instruction_type == 'BPK':
                    # BPK指令：买平后买开，空单转多单
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    else:
                        lines.append(f'        # {instr.instruction_type}指令，买平后买开')
                    
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 风控检查：每日交易次数限制')
                    lines.append('            if self.daily_trade_count >= self.max_daily_trades:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 风控检查：连续亏损限制')
                    lines.append('            if self.consecutive_losses >= self.max_consecutive_losses:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 获取当前持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            ')
                    lines.append('            # 持仓检查：严格遵守只有一手持仓')
                    lines.append('            # BPK指令允许：空头持仓转多头持仓，或空仓开多')
                    lines.append('            if pos > 0:  # 如果已有多头持仓，不允许再次开仓')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # BPK指令：买平后买开，空单转多单')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的买平开操作')
                    lines.append('            # 强制限制最终持仓只有1手')
                    lines.append('            target_volume = 1')
                    lines.append('            ')
                    lines.append('            if pos < 0:  # 如果有空头持仓')
                    lines.append('                # 先买入平仓，平掉所有空头持仓')
                    lines.append('                cover_volume = abs(pos)  # 平仓数量为当前空头持仓的绝对值')
                    lines.append('                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                    self.cover(bar.close_price, cover_volume)')
                    if instr.group:
                        lines.append(f'                    self.write_log("BPK指令({instr.group})触发: 买入平仓 %d 手" % cover_volume)')
                    else:
                        lines.append('                    self.write_log("BPK指令触发: 买入平仓 %d 手" % cover_volume)')
                    lines.append('                    # 平仓后，计算需要开仓的数量（确保最终持仓为1手）')
                    lines.append('                    # 平仓后持仓变为0，所以需要开1手')
                    lines.append('                    open_volume = target_volume')
                    lines.append('                else:')
                    lines.append('                    return  # 价格无效，跳过')
                    lines.append('            else:')
                    lines.append('                # 空仓，直接开1手')
                    lines.append('                open_volume = target_volume')
                    lines.append('            ')
                    lines.append('            # 买入开仓（确保只有1手）')
                    lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                if open_volume > 0:')
                    lines.append('                    # 开仓前再次检查持仓，防止同一根K线上多个信号重复开仓')
                    lines.append('                    current_pos = self.pos')
                    lines.append('                    if current_pos >= 1:  # 如果已有多头持仓，不再开仓')
                    lines.append('                        return  # 静默跳过，避免重复开仓')
                    lines.append('                    # 计算实际需要开仓的数量（确保最终持仓不超过1手）')
                    lines.append('                    actual_open_volume = min(open_volume, max(0, 1 - current_pos))')
                    lines.append('                    if actual_open_volume > 0:')
                    lines.append('                        self.buy(bar.close_price, actual_open_volume)')
                    lines.append('                        # 记录开仓价格')
                    lines.append('                        self.entry_price = bar.close_price')
                    lines.append('                        self.daily_trade_count += 1')
                    if instr.group:
                        lines.append(f'                        self.write_log("BPK指令({instr.group})触发: 买入开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))')
                    else:
                        lines.append('                        self.write_log("BPK指令触发: 买入开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))')
                    lines.append('        ')
                elif instr.instruction_type == 'SPK':
                    # SPK指令：卖平后卖开，多单转空单
                    lines.append(f'        # {var.name}: {instr.condition}, {instr.instruction_type}')
                    if instr.group:
                        lines.append(f'        # {instr.instruction_type}指令，分组: {instr.group}')
                    else:
                        lines.append(f'        # {instr.instruction_type}指令，卖平后卖开')
                    
                    lines.append(f'        if self.{var.name} > 0:  # 条件满足')
                    lines.append('            # 风控检查：每日交易次数限制')
                    lines.append('            if self.daily_trade_count >= self.max_daily_trades:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 风控检查：连续亏损限制')
                    lines.append('            if self.consecutive_losses >= self.max_consecutive_losses:')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # 获取当前持仓')
                    lines.append('            pos = self.pos')
                    lines.append('            ')
                    lines.append('            # 持仓检查：严格遵守只有一手持仓')
                    lines.append('            # SPK指令允许：多头持仓转空头持仓，或多仓开空')
                    lines.append('            if pos < 0:  # 如果已有空头持仓，不允许再次开仓')
                    lines.append('                return  # 静默跳过，避免日志刷屏')
                    lines.append('            ')
                    lines.append('            # SPK指令：卖平后卖开，多单转空单')
                    if instr.group:
                        lines.append(f'            # 分组 {instr.group} 的卖平开操作')
                    lines.append('            # 强制限制最终持仓只有1手')
                    lines.append('            target_volume = 1')
                    lines.append('            ')
                    lines.append('            if pos > 0:  # 如果有多头持仓')
                    lines.append('                # 先卖出平仓，平掉所有多头持仓')
                    lines.append('                sell_volume = pos  # 平仓数量为当前多头持仓')
                    lines.append('                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                    self.sell(bar.close_price, sell_volume)')
                    if instr.group:
                        lines.append(f'                    self.write_log("SPK指令({instr.group})触发: 卖出平仓 %d 手" % sell_volume)')
                    else:
                        lines.append('                    self.write_log("SPK指令触发: 卖出平仓 %d 手" % sell_volume)')
                    lines.append('                    # 平仓后，计算需要开仓的数量（确保最终持仓为1手）')
                    lines.append('                    # 平仓后持仓变为0，所以需要开1手空仓')
                    lines.append('                    open_volume = target_volume')
                    lines.append('                else:')
                    lines.append('                    return  # 价格无效，跳过')
                    lines.append('            else:')
                    lines.append('                # 空仓，直接开1手空仓')
                    lines.append('                open_volume = target_volume')
                    lines.append('            ')
                    lines.append('            # 卖出开仓（确保只有1手）')
                    lines.append('            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:')
                    lines.append('                if open_volume > 0:')
                    lines.append('                    # 开仓前再次检查持仓，防止同一根K线上多个信号重复开仓')
                    lines.append('                    current_pos = self.pos')
                    lines.append('                    if current_pos <= -1:  # 如果已有空头持仓，不再开仓')
                    lines.append('                        return  # 静默跳过，避免重复开仓')
                    lines.append('                    # 计算实际需要开仓的数量（确保最终持仓不超过1手）')
                    lines.append('                    actual_open_volume = min(open_volume, max(0, 1 + current_pos))  # current_pos可能是正数，需要先平多再开空')
                    lines.append('                    if actual_open_volume > 0:')
                    lines.append('                        self.short(bar.close_price, actual_open_volume)')
                    lines.append('                        # 记录开仓价格')
                    lines.append('                        self.entry_price = bar.close_price')
                    lines.append('                        self.daily_trade_count += 1')
                    if instr.group:
                        lines.append(f'                        self.write_log("SPK指令({instr.group})触发: 卖出开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))')
                    else:
                        lines.append('                        self.write_log("SPK指令触发: 卖出开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))')
                    lines.append('        ')
        else:
            # 没有交易指令时，使用示例逻辑
            lines.append('        # 示例：根据ISBUYTREND判断趋势')
            isbuytrend_vars = [v for v in variables_info if 'TREND' in v.name.upper() or 'BUY' in v.name.upper()]
            if isbuytrend_vars:
                trend_var = isbuytrend_vars[0]
                lines.append(f'        if self.{trend_var.name} > 0:')
                lines.append('            self.write_log(f"检测到多头趋势")')
                lines.append('            # 可以在这里添加买入逻辑')
            else:
                lines.append('        # 根据策略变量实现交易逻辑')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _get_period_key(self, stmt: ImportStatement) -> str:
        """获取周期键"""
        return f"{stmt.period.value}_{stmt.n}"
    
    def _get_interval_string(self, period_type: str, period_n: int) -> str:
        """
        根据周期类型和周期数确定 Interval 字符串
        
        参数:
            period_type: 周期类型（如 "MIN", "HOUR", "DAY"）
            period_n: 周期数（如 1, 5, 15）
        
        返回:
            Interval 字符串（如 "Interval.MINUTE", "Interval.MINUTE_5"）
        """
        if period_type == "MIN":
            if period_n == 1:
                return "Interval.MINUTE"
            elif period_n == 5:
                return "Interval.MINUTE_5"
            else:
                # 其他分钟周期暂时使用 MINUTE，后续可以根据需要扩展
                return "Interval.MINUTE"
        elif period_type == "HOUR" or period_type == "CUSHOUR":
            return "Interval.HOUR"
        elif period_type == "DAY":
            return "Interval.DAILY"
        else:
            return "Interval.MINUTE"  # 默认
    
    def _get_variable_value(self, var_name: str) -> str:
        """获取变量值的字符串表示"""
        return f"self.{var_name}"
    
    def _generate_indicator_calculator(self, model_name: str, var_name: str, expression: str) -> str:
        """
        生成指标计算函数代码
        
        参数:
            model_name: 模型文件名（如 "MIN5_OPEN"）
            var_name: 变量名（如 "PREV_OPEN"）
            expression: 表达式（如 "REF(O,1)"）
        
        返回:
            指标计算函数的代码字符串
        """
        lines = []
        func_name = f"_calculate_{model_name.lower()}_{var_name.lower()}"
        lines.append(f'    def {func_name}(self, bars: List[BarData]) -> np.ndarray:')
        lines.append(f'        """计算指标 {var_name}: {expression}"""')
        lines.append('        if len(bars) < 2:')
        lines.append('            return np.array([np.nan] * len(bars))')
        lines.append('        ')
        
        # 解析表达式
        expr_clean = expression.strip()
        
        # 处理 REF(O,1) 或 REF(O, 1)
        if 'REF(O' in expr_clean or 'REF(O,' in expr_clean:
            # 提取周期数
            import re
            match = re.search(r'REF\(O\s*,\s*(\d+)\)', expr_clean)
            if match:
                period = int(match.group(1))
                lines.append('        # 提取开盘价')
                lines.append('        opens = np.array([bar.open_price for bar in bars])')
                lines.append(f'        # 计算 REF(O, {period})')
                lines.append(f'        result = REF(opens, {period})')
                lines.append('        return result')
            else:
                lines.append('        # 无法解析表达式，返回NaN')
                lines.append('        return np.array([np.nan] * len(bars))')
        elif 'REF(C' in expr_clean or 'REF(C,' in expr_clean:
            # 提取周期数
            import re
            match = re.search(r'REF\(C\s*,\s*(\d+)\)', expr_clean)
            if match:
                period = int(match.group(1))
                lines.append('        # 提取收盘价')
                lines.append('        closes = np.array([bar.close_price for bar in bars])')
                lines.append(f'        # 计算 REF(C, {period})')
                lines.append(f'        result = REF(closes, {period})')
                lines.append('        return result')
            else:
                lines.append('        # 无法解析表达式，返回NaN')
                lines.append('        return np.array([np.nan] * len(bars))')
        elif expr_clean == 'O':
            lines.append('        # 提取开盘价')
            lines.append('        opens = np.array([bar.open_price for bar in bars])')
            lines.append('        return opens')
        elif expr_clean == 'C':
            lines.append('        # 提取收盘价')
            lines.append('        closes = np.array([bar.close_price for bar in bars])')
            lines.append('        return closes')
        elif expr_clean == 'H':
            lines.append('        # 提取最高价')
            lines.append('        highs = np.array([bar.high_price for bar in bars])')
            lines.append('        return highs')
        elif expr_clean == 'L':
            lines.append('        # 提取最低价')
            lines.append('        lows = np.array([bar.low_price for bar in bars])')
            lines.append('        return lows')
        else:
            lines.append('        # 无法解析表达式，返回NaN')
            lines.append('        return np.array([np.nan] * len(bars))')
        
        lines.append('')
        return '\n'.join(lines)


def generate_strategy_from_model(
    model_name: str,
    strategy_class_name: Optional[str] = None,
    output_file: Optional[str] = None,
    author: str = "MFLang Generator"
) -> str:
    """
    便捷函数：从模型文件生成策略代码
    
    参数:
        model_name: 模型文件名（不含路径）
        strategy_class_name: 策略类名，如果为None则自动生成
        output_file: 输出文件路径，如果为None则不写入文件
        author: 策略作者
        
    返回:
        生成的策略代码字符串
    """
    generator = StrategyGenerator()
    return generator.generate_strategy(
        model_name=model_name,
        strategy_class_name=strategy_class_name,
        output_file=output_file,
        author=author
    )


if __name__ == "__main__":
    # 示例：生成 TEST_IMPORT 模型的策略文件
    print("生成策略文件...")
    code = generate_strategy_from_model(
        model_name="TEST_IMPORT",
        strategy_class_name="TestImportStrategy",
        output_file="vnpy_ctastrategy/vnpy_ctastrategy/strategies/test_import_strategy.py",
        author="MFLang Generator"
    )
    print("策略代码生成完成！")
    print("\n生成的代码预览（前50行）：")
    print("\n".join(code.split('\n')[:50]))

