#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
变量依赖分析器
分析变量之间的依赖关系，确定正确的计算顺序
"""

from typing import List, Dict, Set, Optional
from collections import defaultdict, deque
from .ast_visitor import (
    ASTNode, NodeType, VariableAssignNode, FunctionCallNode,
    BinaryOpNode, UnaryOpNode, CrossPeriodRefNode
)


class DependencyAnalyzer:
    """变量依赖分析器"""
    
    # K线数据标识符（这些不是变量，不需要依赖）
    KLINE_DATA_IDENTIFIERS = {
        'C', 'CLOSE', 'H', 'HIGH', 'L', 'LOW', 'O', 'OPEN',
        'V', 'VOL', 'VOLUME', 'TIME', 'KTIME'
    }
    
    # 特殊函数（这些不是变量）
    SPECIAL_FUNCTIONS = {'BARPOS'}
    
    def __init__(self):
        """初始化依赖分析器"""
        self.variables: Dict[str, VariableAssignNode] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # var_name -> {dependencies}
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)  # var_name -> {dependents}
    
    def analyze(self, variables: List[VariableAssignNode]) -> List[str]:
        """
        分析变量依赖关系并返回计算顺序
        
        参数:
            variables: 变量赋值节点列表
            
        返回:
            按依赖顺序排列的变量名列表（拓扑排序结果）
            
        抛出:
            ValueError: 如果检测到循环依赖
        """
        # 重置状态
        self.variables = {}
        self.dependencies = defaultdict(set)
        self.reverse_dependencies = defaultdict(set)
        
        # 收集所有变量
        for var in variables:
            self.variables[var.var_name] = var
        
        # 分析每个变量的依赖
        for var in variables:
            deps = self._extract_dependencies(var.expression)
            self.dependencies[var.var_name] = deps
            
            # 构建反向依赖图
            for dep in deps:
                self.reverse_dependencies[dep].add(var.var_name)
        
        # 拓扑排序
        return self._topological_sort()
    
    def _extract_dependencies(self, node: ASTNode) -> Set[str]:
        """
        从表达式中提取变量依赖
        
        参数:
            node: AST节点
            
        返回:
            依赖的变量名集合
        """
        dependencies = set()
        
        if node is None:
            return dependencies
        
        # 根据节点类型递归提取依赖
        if node.node_type == NodeType.IDENTIFIER:
            # 标识符：检查是否是变量
            identifier = node.value
            identifier_upper = identifier.upper()
            
            # 跳过K线数据和特殊函数
            if identifier_upper not in self.KLINE_DATA_IDENTIFIERS:
                if identifier_upper not in self.SPECIAL_FUNCTIONS:
                    # 检查是否是已定义的变量
                    if identifier in self.variables:
                        dependencies.add(identifier)
        
        elif node.node_type == NodeType.BINARY_OP:
            # 二元运算符：递归处理左右操作数
            if isinstance(node, BinaryOpNode):
                dependencies.update(self._extract_dependencies(node.left))
                dependencies.update(self._extract_dependencies(node.right))
        
        elif node.node_type == NodeType.UNARY_OP:
            # 一元运算符：递归处理操作数
            if isinstance(node, UnaryOpNode):
                dependencies.update(self._extract_dependencies(node.operand))
        
        elif node.node_type == NodeType.FUNCTION_CALL:
            # 函数调用：递归处理所有参数
            if isinstance(node, FunctionCallNode):
                for arg in node.arguments:
                    dependencies.update(self._extract_dependencies(arg))
        
        elif node.node_type == NodeType.CROSS_PERIOD_REF:
            # 跨周期引用：提取字段名（如果有变量名部分）
            if isinstance(node, CrossPeriodRefNode):
                # 跨周期引用格式：VARNAME.FIELDNAME
                # 这里只提取VARNAME部分（如果它是变量）
                var_name = node.var_name
                if var_name in self.variables:
                    dependencies.add(var_name)
        
        elif node.node_type == NodeType.EXPRESSION:
            # 表达式节点：递归处理子节点
            if node.children:
                for child in node.children:
                    dependencies.update(self._extract_dependencies(child))
        
        # 递归处理所有子节点
        if node.children:
            for child in node.children:
                dependencies.update(self._extract_dependencies(child))
        
        return dependencies
    
    def _topological_sort(self) -> List[str]:
        """
        使用拓扑排序确定变量计算顺序
        
        返回:
            按依赖顺序排列的变量名列表
            
        抛出:
            ValueError: 如果检测到循环依赖
        """
        # 计算每个变量的入度（依赖数量）
        in_degree = {}
        for var_name in self.variables:
            in_degree[var_name] = len(self.dependencies[var_name])
        
        # 使用Kahn算法进行拓扑排序
        queue = deque()
        result = []
        
        # 找到所有入度为0的节点（没有依赖的变量）
        for var_name, degree in in_degree.items():
            if degree == 0:
                queue.append(var_name)
        
        # 处理队列
        while queue:
            var_name = queue.popleft()
            result.append(var_name)
            
            # 更新依赖此变量的所有变量的入度
            for dependent in self.reverse_dependencies[var_name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否有循环依赖
        if len(result) != len(self.variables):
            # 找到未处理的变量（这些变量形成了循环）
            remaining = set(self.variables.keys()) - set(result)
            raise ValueError(
                f"检测到循环依赖: {remaining}. "
                f"请检查变量定义是否有循环引用。"
            )
        
        return result
    
    def get_dependencies(self, var_name: str) -> Set[str]:
        """获取指定变量的依赖集合"""
        return self.dependencies.get(var_name, set())
    
    def get_dependents(self, var_name: str) -> Set[str]:
        """获取依赖指定变量的所有变量"""
        return self.reverse_dependencies.get(var_name, set())
    
    def has_circular_dependency(self) -> bool:
        """检查是否存在循环依赖"""
        try:
            self._topological_sort()
            return False
        except ValueError:
            return True
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """获取完整的依赖图"""
        return dict(self.dependencies)

