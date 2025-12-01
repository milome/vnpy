"""ChartWidget Mixin 基类

提供所有 Mixin 类共用的辅助方法。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnpy.trader.engine import MainEngine


class ChartWidgetMixinBase:
    """Mixin 基类，提供通用辅助方法
    
    所有 ChartWidget 的 Mixin 类都应该继承这个基类，
    以获得通用的辅助方法。
    """
    
    def _get_main_engine(self) -> "MainEngine | None":
        """获取 main_engine（如果存在）
        
        Returns:
            MainEngine 实例，如果不存在则返回 None
        """
        return getattr(self, "_main_engine", None)
    
    def _get_vt_symbol(self) -> str | None:
        """获取 vt_symbol（如果存在）
        
        Returns:
            vt_symbol 字符串，如果不存在则返回 None
        """
        return getattr(self, "_vt_symbol", None)
    
    def _log(self, message: str, source: str = "ChartWidget") -> None:
        """统一的日志记录方法
        
        Args:
            message: 日志消息
            source: 日志来源标识，默认为 "ChartWidget"
        """
        main_engine = self._get_main_engine()
        if main_engine:
            main_engine.write_log(f"[{source}] {message}", source)

