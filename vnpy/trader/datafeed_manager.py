"""
全局 Datafeed 单例管理器

用于管理全局唯一的 Datafeed 连接，避免多个 ChartWindow 创建重复连接。
确保 Datafeed 连接在程序生命周期内保持，只在程序退出时关闭。
"""

import atexit
from threading import RLock
from typing import Optional

from vnpy.trader.datafeed import BaseDatafeed


class DatafeedManager:
    """
    Datafeed 单例管理器
    
    特点:
    1. 全局单例，确保整个程序只有一个 Datafeed 实例
    2. 线程安全，支持多个 ChartWindow 并发访问
    3. 自动初始化，首次访问时创建连接
    4. 程序退出时自动关闭连接
    """
    
    _instance: Optional['DatafeedManager'] = None
    _lock: RLock = RLock()
    
    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化管理器（只执行一次）"""
        if self._initialized:
            return
            
        self._initialized = True
        self._datafeed: Optional[BaseDatafeed] = None
        self._access_lock: RLock = RLock()
        self._init_count: int = 0  # 跟踪初始化次数
        
        # 注册程序退出时的清理函数
        atexit.register(self._cleanup)
    
    def get_datafeed(self, write_log=None) -> Optional[BaseDatafeed]:
        """
        获取全局 Datafeed 实例
        
        Args:
            write_log: 日志输出函数（可选）
            
        Returns:
            Datafeed 实例，如果创建/初始化失败则返回 None
        """
        with self._access_lock:
            # 如果已有实例，直接返回
            if self._datafeed is not None:
                if write_log:
                    write_log("[DatafeedManager] 使用全局单例 Datafeed 连接")
                return self._datafeed
            
            # 首次访问，创建并初始化 Datafeed
            try:
                from vnpy.trader.datafeed import get_datafeed
                
                self._datafeed = get_datafeed()
                
                if self._datafeed is None:
                    if write_log:
                        write_log("[DatafeedManager] 未配置 Datafeed，无法创建实例")
                    return None
                
                # 初始化 Datafeed
                if hasattr(self._datafeed, 'init'):
                    if self._datafeed.init(output=write_log):
                        self._init_count += 1
                        if write_log:
                            write_log(
                                f"[DatafeedManager] ✓ 创建全局单例 Datafeed 连接 "
                                f"(初始化次数: {self._init_count})"
                            )
                        return self._datafeed
                    else:
                        if write_log:
                            write_log("[DatafeedManager] Datafeed 初始化失败")
                        self._datafeed = None
                        return None
                else:
                    # 没有 init 方法，直接使用
                    if write_log:
                        write_log("[DatafeedManager] ✓ 创建全局单例 Datafeed 连接（无需初始化）")
                    return self._datafeed
                    
            except Exception as e:
                if write_log:
                    write_log(f"[DatafeedManager] 创建 Datafeed 失败: {e}")
                self._datafeed = None
                return None
    
    def is_connected(self) -> bool:
        """
        检查 Datafeed 是否已连接
        
        Returns:
            True 如果已连接，否则 False
        """
        with self._access_lock:
            return self._datafeed is not None
    
    def force_reconnect(self, write_log=None) -> Optional[BaseDatafeed]:
        """
        强制重新连接（用于连接断开后的恢复）
        
        Args:
            write_log: 日志输出函数（可选）
            
        Returns:
            新的 Datafeed 实例，如果失败则返回 None
        """
        with self._access_lock:
            # 先关闭旧连接
            if self._datafeed is not None:
                try:
                    if hasattr(self._datafeed, 'close'):
                        self._datafeed.close()
                        if write_log:
                            write_log("[DatafeedManager] 已关闭旧的 Datafeed 连接")
                except Exception as e:
                    if write_log:
                        write_log(f"[DatafeedManager] 关闭旧连接失败: {e}")
                finally:
                    self._datafeed = None
            
            # 重新创建连接
            return self.get_datafeed(write_log)
    
    def _cleanup(self):
        """程序退出时清理资源（由 atexit 自动调用）"""
        with self._access_lock:
            if self._datafeed is not None:
                try:
                    if hasattr(self._datafeed, 'close'):
                        self._datafeed.close()
                        print("[DatafeedManager] 程序退出：已关闭全局 Datafeed 连接")
                except Exception as e:
                    print(f"[DatafeedManager] 程序退出：关闭连接失败: {e}")
                finally:
                    self._datafeed = None


# 创建全局单例实例
_datafeed_manager = DatafeedManager()


def get_global_datafeed(write_log=None) -> Optional[BaseDatafeed]:
    """
    获取全局单例 Datafeed 实例（便捷函数）
    
    Args:
        write_log: 日志输出函数（可选）
        
    Returns:
        Datafeed 实例，如果创建/初始化失败则返回 None
    """
    return _datafeed_manager.get_datafeed(write_log)


def is_datafeed_connected() -> bool:
    """
    检查全局 Datafeed 是否已连接（便捷函数）
    
    Returns:
        True 如果已连接，否则 False
    """
    return _datafeed_manager.is_connected()


def force_datafeed_reconnect(write_log=None) -> Optional[BaseDatafeed]:
    """
    强制重新连接全局 Datafeed（便捷函数）
    
    Args:
        write_log: 日志输出函数（可选）
        
    Returns:
        新的 Datafeed 实例，如果失败则返回 None
    """
    return _datafeed_manager.force_reconnect(write_log)

