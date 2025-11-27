#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型文件加载器
用于加载和解析 mflang/mmodels/ 目录下的模型文件
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
import re


class ModelLoader:
    """模型文件加载器"""
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        初始化模型加载器
        
        参数:
            models_dir: 模型文件目录，默认为 mflang/mmodels/
        """
        if models_dir is None:
            # 获取当前文件所在目录的父目录，然后找到mmodels目录
            current_file = Path(__file__).resolve()
            mflang_dir = current_file.parent
            models_dir = mflang_dir / "mmodels"
        else:
            models_dir = Path(models_dir)
        
        self.models_dir = models_dir
        self._cache: Dict[str, Dict[str, str]] = {}  # 缓存已加载的模型
    
    def load_model(self, formula_name: str) -> Dict[str, str]:
        """
        加载模型文件
        
        参数:
            formula_name: 模型文件名（FORMULA参数）
            
        返回:
            字典，键为变量名，值为变量定义表达式
            例如: {"CC": "REF(C,1)"}
            
        异常:
            FileNotFoundError: 模型文件不存在
            ValueError: 模型文件格式错误
        """
        # 检查缓存
        if formula_name in self._cache:
            return self._cache[formula_name]
        
        # 构建模型文件路径
        model_file = self.models_dir / formula_name
        
        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")
        
        # 读取模型文件内容
        try:
            with open(model_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"无法读取模型文件 {model_file}: {e}")
        
        # 解析模型文件，提取变量定义
        # 格式: VARIABLE_NAME:EXPRESSION; 或 VARIABLE_NAME:=EXPRESSION;
        # 例如: CC:REF(C,1); 或 CC:=REF(C,1);
        variables = {}
        
        # 移除注释（// 开头的行或行内注释）
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # 先去除行首尾空白
            line_stripped = line.strip()
            # 如果整行以 // 开头，跳过这一行（整行注释）
            if line_stripped.startswith('//'):
                continue
            # 移除行内注释
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line.strip())
        
        content = '\n'.join(cleaned_lines)
        
        # 匹配变量定义: VARIABLE_NAME:EXPRESSION; 或 VARIABLE_NAME:=EXPRESSION;
        # 变量名可以是字母、汉字、数字的组合，但不能以数字开头
        pattern = r'([A-Za-z\u4e00-\u9fa5_][A-Za-z0-9\u4e00-\u9fa5_]*)\s*[:=]\s*([^;]+);'
        
        matches = re.finditer(pattern, content)
        
        for match in matches:
            var_name = match.group(1).strip()
            var_expr = match.group(2).strip()
            
            # 跳过保留关键字（如保存指标、命名为等）
            if var_name.lower() in ['保存指标', '命名为', 'save', 'as']:
                continue
            
            variables[var_name] = var_expr
        
        if not variables:
            raise ValueError(f"模型文件 {model_file} 中没有找到有效的变量定义")
        
        # 缓存结果
        self._cache[formula_name] = variables
        
        return variables
    
    def get_variable(self, formula_name: str, variable_name: str) -> Optional[str]:
        """
        获取模型中的变量定义
        
        参数:
            formula_name: 模型文件名
            variable_name: 变量名
            
        返回:
            变量定义表达式，如果不存在返回None
        """
        try:
            model = self.load_model(formula_name)
            return model.get(variable_name)
        except Exception:
            return None
    
    def list_models(self) -> List[str]:
        """
        列出所有可用的模型文件
        
        返回:
            模型文件名列表
        """
        if not self.models_dir.exists():
            return []
        
        models = []
        for file in self.models_dir.iterdir():
            if file.is_file() and not file.name.startswith('.'):
                models.append(file.name)
        
        return sorted(models)
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()


# 全局模型加载器实例
_default_loader: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    """获取默认的模型加载器实例"""
    global _default_loader
    if _default_loader is None:
        _default_loader = ModelLoader()
    return _default_loader


def load_model(formula_name: str) -> Dict[str, str]:
    """
    加载模型文件（便捷函数）
    
    参数:
        formula_name: 模型文件名
        
    返回:
        变量定义字典
    """
    return get_model_loader().load_model(formula_name)


def get_variable(formula_name: str, variable_name: str) -> Optional[str]:
    """
    获取模型中的变量定义（便捷函数）
    
    参数:
        formula_name: 模型文件名
        variable_name: 变量名
        
    返回:
        变量定义表达式
    """
    return get_model_loader().get_variable(formula_name, variable_name)

