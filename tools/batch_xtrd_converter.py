#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量XTRD文件转换工具
支持从ZIP文件中提取XTRD文件并转换为Python策略
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class XTRDFile:
    """XTRD文件数据结构"""
    filename: str
    code: str
    version: str
    author: str
    edit_time: str
    imports: List[Tuple[str, str, str]]  # (周期类型, 周期数, 模型名, 别名)
    variables: List[str]
    
class XTRDParser:
    """XTRD文件解析器"""
    
    def __init__(self):
        self.import_pattern = re.compile(r'#IMPORT\s*\[([^,]+),\s*(\d+),\s*([^\]]+)\]\s*AS\s*(\w+)', re.IGNORECASE)
        self.variable_pattern = re.compile(r'VARIABLE\s*:\s*(\w+)\s*:=\s*([^;]+);', re.IGNORECASE | re.MULTILINE)
        self.function_calls = re.compile(r'(\w+)\s*\([^)]*\)', re.IGNORECASE)
        self.if_then_pattern = re.compile(r'IF\s+(.+?)\s+THEN\s+BEGIN(.*?)END', re.IGNORECASE | re.DOTALL)
    
    def parse_xtrd_content(self, content: str, filename: str) -> XTRDFile:
        """解析XTRD文件内容"""
        try:
            # 提取XML标签内容
            code_match = re.search(r'<CODE>(.*?)</CODE>', content, re.DOTALL | re.IGNORECASE)
            version_match = re.search(r'<VERSION>(.*?)</VERSION>', content, re.IGNORECASE)
            author_match = re.search(r'<AUTHOR>(.*?)</AUTHOR>', content, re.IGNORECASE)
            edittime_match = re.search(r'<EDITTIME>(.*?)</EDITTIME>', content, re.IGNORECASE)
            
            code = code_match.group(1).strip() if code_match else ""
            version = version_match.group(1).strip() if version_match else "未知"
            author = author_match.group(1).strip() if author_match else "未知"
            edit_time = edittime_match.group(1).strip() if edittime_match else "未知"
            
            # 清理文件名中的路径和特殊字符
            clean_filename = os.path.basename(filename)
            if '/' in clean_filename:
                clean_filename = clean_filename.split('/')[-1]
            
            logger.info(f"解析文件: {clean_filename}")
            logger.info(f"代码长度: {len(code)} 字符")
            
            # 解析导入语句
            imports = []
            import_matches = self.import_pattern.finditer(code)
            for match in import_matches:
                period_type = match.group(1).strip()
                period_num = match.group(2).strip()
                model_name = match.group(3).strip()
                alias = match.group(4).strip()
                imports.append((period_type, period_num, model_name, alias))
                logger.info(f"找到导入: {period_type}, {period_num}, {model_name} AS {alias}")
            
            # 解析变量定义
            variables = []
            variable_matches = self.variable_pattern.finditer(code)
            for match in variable_matches:
                var_name = match.group(1).strip()
                var_expr = match.group(2).strip()
                variables.append(f"{var_name} := {var_expr}")
                logger.info(f"找到变量: {var_name}")
            
            # 如果没找到变量，尝试其他模式
            if not variables:
                # 尝试查找所有可能的变量赋值
                alt_var_pattern = re.compile(r'(\w+)\s*:=\s*([^;\n]+)', re.IGNORECASE | re.MULTILINE)
                for match in alt_var_pattern.finditer(code):
                    var_name = match.group(1).strip()
                    var_expr = match.group(2).strip()
                    if not var_name.upper() in ['IF', 'THEN', 'BEGIN', 'END', 'ELSE']:
                        variables.append(f"{var_name} := {var_expr}")
                        logger.info(f"找到替代变量: {var_name}")
            
            logger.info(f"解析结果: {len(imports)} 个导入, {len(variables)} 个变量")
            
            return XTRDFile(
                filename=clean_filename,
                code=code,
                version=version,
                author=author,
                edit_time=edit_time,
                imports=imports,
                variables=variables
            )
            
        except Exception as e:
            logger.error(f"解析文件 {filename} 时出错: {e}")
            logger.error(f"内容预览: {content[:500]}...")
            raise

class DependencyResolver:
    """依赖关系解析器"""
    
    def __init__(self):
        self.dependency_graph = {}
        self.resolved_order = []
    
    def build_dependency_graph(self, xtrd_files: List[XTRDFile]) -> Dict[str, List[str]]:
        """构建依赖关系图"""
        # 创建文件名到对象的映射
        file_map = {f.filename: f for f in xtrd_files}
        
        # 构建依赖图
        for xtrd_file in xtrd_files:
            dependencies = []
            for period_type, period_num, model_name, alias in xtrd_file.imports:
                # 查找对应的文件
                for other_file in xtrd_files:
                    if model_name in other_file.filename or other_file.filename in model_name:
                        dependencies.append(other_file.filename)
                        break
            
            self.dependency_graph[xtrd_file.filename] = dependencies
        
        logger.info(f"依赖关系图: {self.dependency_graph}")
        return self.dependency_graph
    
    def topological_sort(self) -> List[str]:
        """拓扑排序确定转换顺序"""
        visited = set()
        temp_visited = set()
        result = []
        
        def dfs(node):
            if node in temp_visited:
                raise ValueError(f"检测到循环依赖: {node}")
            if node in visited:
                return
            
            temp_visited.add(node)
            for dependency in self.dependency_graph.get(node, []):
                dfs(dependency)
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in self.dependency_graph:
            if node not in visited:
                dfs(node)
        
        self.resolved_order = result
        logger.info(f"转换顺序: {result}")
        return result

class PythonCodeGenerator:
    """Python代码生成器"""
    
    def __init__(self):
        self.function_mapping = {
            'MA': 'talib.SMA',
            'EMA': 'talib.EMA', 
            'MACD': 'talib.MACD',
            'ATR': 'talib.ATR',
            'STD': 'talib.STDDEV',
            'HHV': 'talib.MAX',
            'LLV': 'talib.MIN',
            'REF': 'self.ref',
            'BARSLAST': 'self.bars_last',
            'COUNT': 'self.count',
            'MAX': 'max',
            'MIN': 'min',
            'ABS': 'abs',
            'MOD': 'lambda x, y: x % y'
        }
    
    def generate_strategy_class(self, xtrd_file: XTRDFile) -> str:
        """生成Python策略类"""
        class_name = self._generate_class_name(xtrd_file.filename)
        
        template = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从麦语言转换的策略: {xtrd_file.filename}
原作者: {xtrd_file.author}
转换时间: {xtrd_file.edit_time}
版本: {xtrd_file.version}
"""

import numpy as np
import talib
from vnpy_ctastrategy import CtaTemplate, StopOrder
from vnpy.trader.object import BarData, TickData, OrderData, TradeData
from vnpy.trader.constant import Interval, Direction, Status

class {class_name}(CtaTemplate):
    """
    {xtrd_file.filename} 策略
    """
    
    author = "{xtrd_file.author}"
    
    # 策略参数
    parameters = []
    
    # 策略变量
    variables = []
    
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # 初始化数据缓存
        self.bars = []
        self.max_window = 200  # 最大窗口大小
        
        # 导入的外部策略引用
{self._generate_imports(xtrd_file.imports)}
        
        # 策略变量初始化
{self._generate_variable_init(xtrd_file.variables)}
    
    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        self.load_bar(10)  # 加载历史数据
    
    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")
    
    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")
    
    def on_bar(self, bar: BarData):
        """K线数据更新"""
        # 更新数据缓存
        self.bars.append(bar)
        if len(self.bars) > self.max_window:
            self.bars.pop(0)
        
        if len(self.bars) < 20:  # 确保有足够数据
            return
        
        # 计算技术指标
        self.calculate_indicators()
        
        # 执行策略逻辑
        self.execute_strategy_logic()
        
        # 更新GUI显示
        self.put_event()
    
    def calculate_indicators(self):
        """计算技术指标"""
        if len(self.bars) < 20:
            return
        
        # 提取价格数据
        closes = np.array([bar.close_price for bar in self.bars])
        highs = np.array([bar.high_price for bar in self.bars])
        lows = np.array([bar.low_price for bar in self.bars])
        volumes = np.array([bar.volume for bar in self.bars])
        
        # 计算基础指标
        try:
{self._generate_indicator_calculations(xtrd_file.variables)}
        except Exception as e:
            self.write_log(f"指标计算错误: {{e}}")
    
    def execute_strategy_logic(self):
        """执行策略逻辑"""
        # 这里需要根据具体的麦语言逻辑进行转换
        # 由于麦语言逻辑复杂，建议手动调整
        pass
    
    # 辅助函数
    def ref(self, data, n):
        """引用n周期前的数据"""
        if isinstance(data, (list, np.ndarray)) and len(data) > n:
            return data[-n-1] if n < len(data) else data[0]
        return 0
    
    def bars_last(self, condition_array):
        """返回条件最后一次为真到现在的周期数"""
        if not isinstance(condition_array, (list, np.ndarray)):
            return 0
        
        for i in range(len(condition_array)-1, -1, -1):
            if condition_array[i]:
                return len(condition_array) - 1 - i
        return len(condition_array)
    
    def count(self, condition_array, n):
        """统计n周期内条件为真的次数"""
        if not isinstance(condition_array, (list, np.ndarray)) or len(condition_array) < n:
            return 0
        
        recent_data = condition_array[-n:]
        return sum(1 for x in recent_data if x)
'''
        
        return template
    
    def _generate_class_name(self, filename: str) -> str:
        """生成类名"""
        # 移除文件扩展名和特殊字符
        name = re.sub(r'[^\w\u4e00-\u9fff]', '_', filename.replace('.XTRD', ''))
        # 转换为驼峰命名
        parts = name.split('_')
        class_name = ''.join(word.capitalize() for word in parts if word)
        return f"{class_name}Strategy"
    
    def _generate_imports(self, imports: List[Tuple[str, str, str, str]]) -> str:
        """生成导入语句"""
        if not imports:
            return "        # 无外部依赖"
        
        lines = []
        for period_type, period_num, model_name, alias in imports:
            lines.append(f"        # self.{alias.lower()} = None  # {model_name} ({period_type}, {period_num})")
        
        return '\n'.join(lines)
    
    def _generate_variable_init(self, variables: List[str]) -> str:
        """生成变量初始化"""
        if not variables:
            return "        # 无策略变量"
        
        lines = []
        for var in variables[:10]:  # 只显示前10个变量作为示例
            var_name = var.split(':=')[0].strip() if ':=' in var else var
            lines.append(f"        self.{var_name.lower()} = 0")
        
        if len(variables) > 10:
            lines.append(f"        # ... 还有 {len(variables) - 10} 个变量")
        
        return '\n'.join(lines)
    
    def _generate_indicator_calculations(self, variables: List[str]) -> str:
        """生成指标计算代码"""
        lines = []
        
        for var in variables:
            var_name, var_expr = var.split(' := ', 1) if ' := ' in var else (var, '')
            var_name = var_name.strip()
            var_expr = var_expr.strip()
            
            # 转换常见的技术指标
            python_expr = self._convert_mai_expression(var_expr)
            
            if python_expr:
                lines.append(f"            # {var_name} = {var_expr}")
                lines.append(f"            self.{var_name.lower()} = {python_expr}")
                lines.append("")
        
        if not lines:
            lines.append("            # 根据变量定义添加指标计算")
            lines.append("            pass")
        
        return '\n'.join(lines)
    
    def _convert_mai_expression(self, expr: str) -> str:
        """转换麦语言表达式为Python表达式"""
        if not expr:
            return "0"
        
        # 移除多余空格
        expr = re.sub(r'\s+', ' ', expr.strip())
        
        # 处理简单数值
        if re.match(r'^-?\d+(\.\d+)?$', expr):
            return expr
        
        # 处理简单的数学运算
        if re.match(r'^-?\d+(\.\d+)?\s*[+\-*/]\s*-?\d+(\.\d+)?$', expr):
            return expr
        
        # 常见函数转换
        conversions = {
            r'MA\s*\(\s*CLOSE\s*,\s*(\d+)\s*\)': r'talib.SMA(closes, \1)',
            r'EMA\s*\(\s*CLOSE\s*,\s*(\d+)\s*\)': r'talib.EMA(closes, \1)',
            r'MA\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'talib.SMA(\1, \2)',
            r'EMA\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'talib.EMA(\1, \2)',
            r'HHV\s*\(\s*HIGH\s*,\s*(\d+)\s*\)': r'talib.MAX(highs, \1)',
            r'LLV\s*\(\s*LOW\s*,\s*(\d+)\s*\)': r'talib.MIN(lows, \1)',
            r'HHV\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'np.max(\1[-\2:]) if len(\1) >= \2 else np.max(\1)',
            r'LLV\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'np.min(\1[-\2:]) if len(\1) >= \2 else np.min(\1)',
            r'REF\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'self.ref(\1, \2)',
            r'BARSLAST\s*\(\s*([^)]+)\s*\)': r'self.bars_last(\1)',
            r'COUNT\s*\(\s*([^,]+)\s*,\s*(\d+)\s*\)': r'self.count(\1, \2)',
            r'STD\s*\(\s*CLOSE\s*,\s*(\d+)\s*\)': r'talib.STDDEV(closes, \1)',
            r'ATR\s*\(\s*(\d+)\s*\)': r'talib.ATR(highs, lows, closes, \1)',
            r'ABS\s*\(\s*([^)]+)\s*\)': r'abs(\1)',
            r'MAX\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': r'max(\1, \2)',
            r'MIN\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': r'min(\1, \2)',
            r'\bCLOSE\b': 'closes[-1]',
            r'\bOPEN\b': 'self.bars[-1].open_price',
            r'\bHIGH\b': 'highs[-1]',
            r'\bLOW\b': 'lows[-1]',
            r'\bVOL\b': 'volumes[-1]',
        }
        
        result = expr
        for pattern, replacement in conversions.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # 如果没有转换成功，但是是简单表达式，直接返回
        if result == expr:
            # 检查是否是简单的变量引用或数学表达式
            if re.match(r'^[a-zA-Z_]\w*$', expr):  # 简单变量名
                return f"self.{expr.lower()}"
            elif re.match(r'^[a-zA-Z_]\w*\s*[+\-*/]\s*[a-zA-Z_]\w*$', expr):  # 简单运算
                return expr.lower()
            else:
                return f"0  # TODO: 转换表达式 {expr}"
        
        return result

class BatchXTRDConverter:
    """批量XTRD转换器"""
    
    def __init__(self, output_dir: str = "converted_strategies"):
        self.parser = XTRDParser()
        self.resolver = DependencyResolver()
        self.generator = PythonCodeGenerator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def convert_zip_file(self, zip_path: str) -> Dict[str, str]:
        """转换ZIP文件中的所有XTRD文件"""
        logger.info(f"开始处理ZIP文件: {zip_path}")
        
        # 提取XTRD文件
        xtrd_files = self._extract_xtrd_files(zip_path)
        logger.info(f"找到 {len(xtrd_files)} 个XTRD文件")
        
        # 解析文件内容
        parsed_files = []
        for filename, content in xtrd_files.items():
            try:
                parsed_file = self.parser.parse_xtrd_content(content, filename)
                parsed_files.append(parsed_file)
                logger.info(f"成功解析: {filename}")
            except Exception as e:
                logger.error(f"解析失败 {filename}: {e}")
        
        # 解析依赖关系
        self.resolver.build_dependency_graph(parsed_files)
        conversion_order = self.resolver.topological_sort()
        
        # 按依赖顺序转换
        converted_files = {}
        for filename in conversion_order:
            xtrd_file = next(f for f in parsed_files if f.filename == filename)
            try:
                python_code = self.generator.generate_strategy_class(xtrd_file)
                output_filename = f"{self.generator._generate_class_name(filename)}.py"
                output_path = self.output_dir / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(python_code)
                
                converted_files[filename] = str(output_path)
                logger.info(f"转换完成: {filename} -> {output_filename}")
                
            except Exception as e:
                logger.error(f"转换失败 {filename}: {e}")
        
        return converted_files
    
    def convert_directory(self, dir_path: str) -> Dict[str, str]:
        """转换目录中的所有XTRD文件"""
        logger.info(f"开始处理目录: {dir_path}")
        
        xtrd_files = {}
        dir_path = Path(dir_path)
        
        for file_path in dir_path.glob("*.XTRD"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                xtrd_files[file_path.name] = content
                logger.info(f"读取文件: {file_path.name}")
            except Exception as e:
                logger.error(f"读取文件失败 {file_path}: {e}")
        
        if not xtrd_files:
            logger.warning("未找到XTRD文件")
            return {}
        
        # 使用相同的转换逻辑
        return self._convert_xtrd_dict(xtrd_files)
    
    def _extract_xtrd_files(self, zip_path: str) -> Dict[str, str]:
        """从ZIP文件中提取XTRD文件"""
        xtrd_files = {}
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                logger.info(f"ZIP文件包含 {len(zip_file.filelist)} 个文件")
                
                for file_info in zip_file.filelist:
                    logger.info(f"检查文件: {file_info.filename}")
                    
                    if file_info.filename.endswith('.XTRD') or file_info.filename.endswith('.xtrd'):
                        try:
                            # 尝试多种编码
                            raw_content = zip_file.read(file_info.filename)
                            content = None
                            
                            # 尝试编码列表
                            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']
                            
                            for encoding in encodings:
                                try:
                                    content = raw_content.decode(encoding)
                                    logger.info(f"成功使用 {encoding} 编码解析: {file_info.filename}")
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if content:
                                xtrd_files[file_info.filename] = content
                                logger.info(f"提取文件: {file_info.filename} ({len(content)} 字符)")
                            else:
                                logger.error(f"无法解码文件: {file_info.filename}")
                                
                        except Exception as e:
                            logger.error(f"读取文件 {file_info.filename} 失败: {e}")
        
        except Exception as e:
            logger.error(f"提取ZIP文件失败: {e}")
            raise
        
        logger.info(f"成功提取 {len(xtrd_files)} 个XTRD文件")
        return xtrd_files
    
    def _convert_xtrd_dict(self, xtrd_files: Dict[str, str]) -> Dict[str, str]:
        """转换XTRD文件字典"""
        # 解析文件内容
        parsed_files = []
        for filename, content in xtrd_files.items():
            try:
                parsed_file = self.parser.parse_xtrd_content(content, filename)
                parsed_files.append(parsed_file)
                logger.info(f"成功解析: {filename}")
            except Exception as e:
                logger.error(f"解析失败 {filename}: {e}")
        
        # 解析依赖关系并转换
        if parsed_files:
            self.resolver.build_dependency_graph(parsed_files)
            conversion_order = self.resolver.topological_sort()
            
            converted_files = {}
            for filename in conversion_order:
                xtrd_file = next(f for f in parsed_files if f.filename == filename)
                try:
                    python_code = self.generator.generate_strategy_class(xtrd_file)
                    output_filename = f"{self.generator._generate_class_name(filename)}.py"
                    output_path = self.output_dir / output_filename
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(python_code)
                    
                    converted_files[filename] = str(output_path)
                    logger.info(f"转换完成: {filename} -> {output_filename}")
                    
                except Exception as e:
                    logger.error(f"转换失败 {filename}: {e}")
            
            return converted_files
        
        return {}

def main():
    """主函数 - 使用示例"""
    converter = BatchXTRDConverter()
    
    print("=== 批量XTRD转换工具 ===")
    print("1. 转换ZIP文件")
    print("2. 转换目录")
    print("3. 退出")
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == '1':
        zip_path = input("请输入ZIP文件路径: ").strip()
        if os.path.exists(zip_path):
            try:
                results = converter.convert_zip_file(zip_path)
                print(f"\n转换完成! 共转换 {len(results)} 个文件:")
                for original, converted in results.items():
                    print(f"  {original} -> {converted}")
            except Exception as e:
                print(f"转换失败: {e}")
        else:
            print("文件不存在!")
    
    elif choice == '2':
        dir_path = input("请输入目录路径: ").strip()
        if os.path.exists(dir_path):
            try:
                results = converter.convert_directory(dir_path)
                print(f"\n转换完成! 共转换 {len(results)} 个文件:")
                for original, converted in results.items():
                    print(f"  {original} -> {converted}")
            except Exception as e:
                print(f"转换失败: {e}")
        else:
            print("目录不存在!")
    
    elif choice == '3':
        print("退出程序")
    
    else:
        print("无效选择!")

if __name__ == "__main__":
    main()
