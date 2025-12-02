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
        self._init_failed: bool = False  # 标记初始化是否失败过
        self._error_shown: bool = False  # 标记是否已显示过错误弹窗
        self._last_connection_check: float = 0  # 最后一次连接检查时间
        self._disconnected_notified: bool = False  # 是否已通知断开连接
        
        # 注册程序退出时的清理函数
        atexit.register(self._cleanup)
    
    def get_datafeed(self, write_log=None, show_error_dialog=False) -> Optional[BaseDatafeed]:
        """
        获取全局 Datafeed 实例
        
        Args:
            write_log: 日志输出函数（可选）
            show_error_dialog: 是否显示错误对话框（仅首次失败时显示一次）
            
        Returns:
            Datafeed 实例，如果创建/初始化失败则返回 None
        """
        with self._access_lock:
            # 如果已经失败过，直接返回 None（不重复尝试或弹窗）
            if self._init_failed:
                return None
            
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
                    error_msg = "[DatafeedManager] ❌ 未配置 Datafeed 服务"
                    if write_log:
                        write_log(error_msg)
                    
                    self._init_failed = True
                    
                    # 首次失败时显示错误对话框
                    if show_error_dialog and not self._error_shown:
                        self._show_error_dialog("未配置 Datafeed 服务", 
                            "系统未配置数据服务。\n\n"
                            "请在设置中配置 Datafeed（如富途 Futu、米筐 RQData 等）")
                        self._error_shown = True
                    
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
                        error_msg = "[DatafeedManager] ❌ Datafeed 初始化失败"
                        if write_log:
                            write_log(error_msg)
                        
                        self._datafeed = None
                        self._init_failed = True
                        
                        # 首次失败时显示错误对话框
                        if show_error_dialog and not self._error_shown:
                            self._show_error_dialog("Datafeed 初始化失败", 
                                "Datafeed 服务初始化失败。\n\n"
                                "可能原因：\n"
                                "• 富途牛牛未启动\n"
                                "• OpenD 服务未开启\n"
                                "• 网络连接问题\n\n"
                                "请检查数据服务连接。")
                            self._error_shown = True
                        
                        return None
                else:
                    # 没有 init 方法，直接使用
                    if write_log:
                        write_log("[DatafeedManager] ✓ 创建全局单例 Datafeed 连接（无需初始化）")
                    return self._datafeed
                    
            except Exception as e:
                error_msg = f"[DatafeedManager] ❌ 创建 Datafeed 失败: {e}"
                if write_log:
                    write_log(error_msg)
                
                self._datafeed = None
                self._init_failed = True
                
                # 首次失败时显示错误对话框
                if show_error_dialog and not self._error_shown:
                    self._show_error_dialog("Datafeed 创建失败", 
                        f"创建 Datafeed 服务失败。\n\n"
                        f"错误信息：{str(e)}\n\n"
                        f"请检查系统配置和日志。")
                    self._error_shown = True
                
                return None
    
    def _show_error_dialog(self, title: str, message: str) -> None:
        """显示错误对话框（需要 Qt 环境）"""
        try:
            from vnpy.trader.ui import QtWidgets
            QtWidgets.QMessageBox.critical(None, title, message)
        except Exception:
            # 如果 Qt 环境不可用，只打印到控制台
            print(f"[DatafeedManager] 错误: {title} - {message}")
    
    def is_connected(self) -> bool:
        """
        检查 Datafeed 是否已连接
        
        Returns:
            True 如果已连接，否则 False
        """
        with self._access_lock:
            if self._datafeed is None:
                return False
            
            # 检查连接是否仍然有效（如果有 inited 属性）
            if hasattr(self._datafeed, 'inited'):
                return self._datafeed.inited
            
            return True
    
    def check_connection_health(self, write_log=None, show_error_dialog=False) -> bool:
        """
        检查 Datafeed 连接健康状态
        
        如果发现连接已断开，提示用户并尝试重连一次。
        
        Args:
            write_log: 日志输出函数
            show_error_dialog: 是否显示错误对话框
            
        Returns:
            True 如果连接正常或重连成功，False 如果连接断开且重连失败
        """
        import time
        
        with self._access_lock:
            # 节流：避免频繁检查（最多每5秒检查一次）
            current_time = time.time()
            if current_time - self._last_connection_check < 5.0:
                return self._datafeed is not None
            
            self._last_connection_check = current_time
            
            # 如果从未创建过，不需要检查
            if self._datafeed is None:
                return False
            
            # 检查连接是否仍然有效
            is_alive = True
            if hasattr(self._datafeed, 'inited'):
                is_alive = self._datafeed.inited
            
            if hasattr(self._datafeed, 'quote_ctx') and self._datafeed.quote_ctx:
                # 对于 Futu Datafeed，检查 quote_ctx 是否仍然有效
                # 可以尝试一个轻量级查询来验证连接
                pass  # TODO: 可以添加更细粒度的连接检查
            
            # 如果连接断开
            if not is_alive:
                if write_log:
                    write_log("[DatafeedManager] ⚠️ 检测到 Datafeed 连接已断开！")
                
                # 首次断开时通知用户
                if show_error_dialog and not self._disconnected_notified:
                    error_msg = (
                        "Datafeed 连接已断开！\n\n"
                        "可能原因：\n"
                        "• 富途牛牛程序异常退出\n"
                        "• OpenD 服务停止\n"
                        "• 网络连接中断\n\n"
                        "系统将尝试自动重连一次。\n"
                        "如果重连失败，请检查富途牛牛并手动重启应用。"
                    )
                    self._show_error_dialog("Datafeed 连接断开", error_msg)
                    self._disconnected_notified = True
                
                # 尝试重连一次
                if write_log:
                    write_log("[DatafeedManager] 尝试自动重连...")
                
                reconnect_result = self.force_reconnect(write_log)
                
                if reconnect_result:
                    if write_log:
                        write_log("[DatafeedManager] ✓ 自动重连成功")
                    self._disconnected_notified = False  # 重置通知标记
                    return True
                else:
                    if write_log:
                        write_log("[DatafeedManager] ✗ 自动重连失败")
                    return False
            
            return True
    
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


def get_global_datafeed(write_log=None, show_error_dialog=False) -> Optional[BaseDatafeed]:
    """
    获取全局单例 Datafeed 实例（便捷函数）
    
    Args:
        write_log: 日志输出函数（可选）
        show_error_dialog: 是否显示错误对话框（仅首次失败时显示一次）
        
    Returns:
        Datafeed 实例，如果创建/初始化失败则返回 None
    """
    return _datafeed_manager.get_datafeed(write_log, show_error_dialog)


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

