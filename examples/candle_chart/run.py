"""
原始单周期示例改造为多周期示例入口：

直接运行本文件，将调用 run_multi_timeframe 中的逻辑，
叠加显示1分钟K线和4小时K线（4小时为跨索引绘制）。
"""

from run_multi_timeframe import main  # type: ignore


if __name__ == "__main__":
    main()
