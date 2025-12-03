"""
多周期K线叠加显示示例入口

真正的多周期绘制逻辑封装在 `multi_timeframe_widget.MultiTimeframeWidget`，
本文件只负责创建应用和展示该 widget，便于后续其他 chart 复用。
"""

from datetime import datetime

from vnpy.trader.ui import create_qapp
from vnpy.trader.constant import Exchange

try:
    from .multi_timeframe_widget import MultiTimeframeWidget
except ImportError:
    # 如果相对导入失败（直接运行脚本时），使用绝对导入
    from multi_timeframe_widget import MultiTimeframeWidget


def main() -> None:
    """多周期K线叠加显示示例入口函数"""
    app = create_qapp()

    start = datetime(2025, 11, 9)
    end = datetime(2025, 12, 3)

    widget = MultiTimeframeWidget(
        vt_symbol="MHImain",
        exchange=Exchange.HKFE,
        start=start,
        end=end,
    )
    widget.setWindowTitle("多周期K线叠加示例（1m + 5m + 1H + 4H）")
    widget.resize(1400, 800)
    widget.show()

    app.exec()


if __name__ == "__main__":
    main()

