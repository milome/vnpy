"""
Price line management module for vnpy chart.

This module provides price line functionality for drawing order trading,
including price line display, drag interaction, and order management.
"""

from enum import Enum
from typing import Optional

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtGui, QtCore

from .base import UP_COLOR, DOWN_COLOR, PEN_WIDTH, NORMAL_FONT


class PriceLineType(Enum):
    """Price line type enumeration."""

    ENTRY = "entry"           # 入场线（已成交）
    PENDING = "pending"       # 挂单线（未成交）
    STOP_LOSS = "stop_loss"   # 止损线
    TAKE_PROFIT = "take_profit"  # 止盈线
    PREVIEW = "preview"       # 预览线（临时显示）


class PriceLineItem(pg.InfiniteLine):
    """
    Price line item based on pyqtgraph InfiniteLine.
    
    Supports horizontal price line display with customizable style.
    """

    def __init__(
        self,
        price: float,
        line_type: PriceLineType,
        direction: str = "long",
        movable: bool = False,
        parent: Optional[pg.GraphicsObject] = None
    ) -> None:
        """
        Initialize price line item.

        Args:
            price: Price value for the line
            line_type: Type of price line (ENTRY, PENDING, etc.)
            direction: Trading direction ("long" or "short")
            movable: Whether the line can be dragged
            parent: Parent graphics object
        """
        # Create pen based on line type and direction
        pen = self._create_pen(line_type, direction)
        
        # Create label text (默认整数显示，MHImain)
        label = self._create_label(price, line_type, price_precision=0, direction=direction)
        
        # Initialize InfiniteLine (angle=0 for horizontal line)
        # Note: labelOpts doesn't support 'font' parameter directly
        # Font can be set after creation if needed
        # span参数设置为(0, 1)表示从0%到100%，确保左右无限延伸
        # 对于入场线，使用较小的position值（0.90），确保label（包括盈亏信息）完整显示
        # 对于其他类型，使用默认值（0.95），与止损/止盈线保持一致
        label_position = 0.90 if line_type == PriceLineType.ENTRY else 0.95
        super().__init__(
            angle=0,
            pos=price,
            pen=pen,
            movable=movable,
            label=label,
            labelOpts={
                "position": label_position,
                "color": pen.color()
            },
            span=(0, 1)  # 确保左右无限延伸，与止损/止盈线一致
        )
        
        # Set font for label after creation
        # 所有价格线使用相同的字体设置，与止损/止盈线保持一致
        if self.label is not None:
            self.label.setFont(NORMAL_FONT)
            # 不设置ItemIgnoresTransformations，与止损/止盈线原有设置保持一致
        
        self._price: float = price
        self._line_type: PriceLineType = line_type
        self._direction: str = direction
        self._original_price: float = price
        self._pnl: float = 0.0  # 浮动盈亏
        self._volume: float = 0.0  # 持仓手数（用于入场线）
        self._vt_orderid: Optional[str] = None  # 关联的订单ID
        self._order_volume: Optional[float] = None  # 挂单线的订单手数（仅PENDING类型）
        self._order_offset: Optional[str] = None  # 挂单线的开平类型（"OPEN"/"CLOSE"，仅PENDING类型）
        self._creation_time: Optional[float] = None  # 创建时间（秒，用于防止创建后立即触发）
        self.entry_line_id: Optional[str] = None  # ✅ 关联的入场线ID（用于止损/止盈线）

    def _create_pen(
        self,
        line_type: PriceLineType,
        direction: str
    ) -> QtGui.QPen:
        """
        Create pen for price line based on type and direction.

        Args:
            line_type: Type of price line
            direction: Trading direction

        Returns:
            QPen object with appropriate style
        """
        # Determine color based on direction (红涨青跌，中国惯例)
        if direction == "long":
            base_color = UP_COLOR  # Red for long
        else:
            base_color = DOWN_COLOR  # Cyan for short

        # Determine line style and color based on type
        if line_type == PriceLineType.ENTRY:
            # Entry line: white dashed, same style as stop loss/take profit
            # 使用DashLine样式，宽度和止损/止盈线一致
            style = QtCore.Qt.PenStyle.DashLine
            width = PEN_WIDTH  # 与止损/止盈线相同的宽度
            color = (255, 255, 255)  # White color for entry line
        elif line_type == PriceLineType.PENDING:
            # Pending order line: dotted
            style = QtCore.Qt.PenStyle.DotLine
            width = PEN_WIDTH
            color = base_color
        elif line_type == PriceLineType.STOP_LOSS:
            # Stop loss: dashed, orange color (警告色)
            style = QtCore.Qt.PenStyle.DashLine
            width = PEN_WIDTH
            color = (255, 165, 0)  # Orange color for stop loss
        elif line_type == PriceLineType.TAKE_PROFIT:
            # Take profit: dashed, green color (盈利色)
            style = QtCore.Qt.PenStyle.DashLine
            width = PEN_WIDTH
            color = (0, 255, 0)  # Green color for take profit
        elif line_type == PriceLineType.PREVIEW:
            # Preview line: dotted, semi-transparent
            style = QtCore.Qt.PenStyle.DotLine
            width = PEN_WIDTH
            # Make preview line semi-transparent
            color = (*base_color[:3], 128)  # Add alpha channel
            return pg.mkPen(color=color, width=width, style=style)
        else:
            style = QtCore.Qt.PenStyle.SolidLine
            width = PEN_WIDTH
            color = base_color

        return pg.mkPen(color=color, width=width, style=style)

    def _create_label(
        self,
        price: float,
        line_type: PriceLineType,
        price_precision: int = 0,
        direction: str = "long"
    ) -> str:
        """
        Create label text for price line.

        Args:
            price: Price value
            line_type: Type of price line
            price_precision: Number of decimal places (0 for integer, default 0 for MHImain)
            direction: Trading direction ("long" or "short"), used for entry line

        Returns:
            Label text string
        """
        type_names = {
            PriceLineType.ENTRY: "入场",
            PriceLineType.PENDING: "挂单",
            PriceLineType.STOP_LOSS: "止损",
            PriceLineType.TAKE_PROFIT: "止盈",
            PriceLineType.PREVIEW: "预览"
        }
        
        type_name = type_names.get(line_type, "")
        
        # 对于入场线，显示方向（多仓/空仓）、持仓手数和浮动盈亏
        # 格式：价格在前，方向在后，与止损/止盈线格式一致（"止损 25971"）
        if line_type == PriceLineType.ENTRY:
            direction_text = "多仓" if direction == "long" else "空仓"
            # 获取浮动盈亏和持仓手数（从实例属性获取）
            # 注意：这里必须从实例属性获取，因为 _create_label 是实例方法
            pnl = getattr(self, '_pnl', 0.0)
            volume = getattr(self, '_volume', 0.0)
            if price_precision == 0:
                price_str = str(int(price))
            else:
                price_str = f"{price:.{price_precision}f}"
            
            # 构建标签文本：价格 方向 手数 (盈亏: 数值)
            # 如果有持仓手数，显示手数信息
            if volume > 0:
                volume_str = f"{int(volume)}手" if volume == int(volume) else f"{volume:.1f}手"
                if pnl != 0.0:
                    pnl_str = f"{pnl:+.0f}" if price_precision == 0 else f"{pnl:+.2f}"
                    return f"{price_str} {direction_text} {volume_str} (盈亏: {pnl_str})"
                else:
                    return f"{price_str} {direction_text} {volume_str}"
            else:
                # 没有持仓手数时，只显示方向和盈亏
                if pnl != 0.0:
                    pnl_str = f"{pnl:+.0f}" if price_precision == 0 else f"{pnl:+.2f}"
                    return f"{price_str} {direction_text} (盈亏: {pnl_str})"
                else:
                    return f"{price_str} {direction_text}"
        
        # 对于止损线和止盈线，如果设置了手数，也显示手数
        if line_type == PriceLineType.STOP_LOSS or line_type == PriceLineType.TAKE_PROFIT:
            volume = getattr(self, '_volume', 0.0)
            # ✅ 检查创建时间，判断是否是挂单线的止损/止盈线
            creation_time = getattr(self, '_creation_time', None)
            is_pending_line = (creation_time is None)  # 创建时间为None表示关联挂单线（未激活）
            
            if price_precision == 0:
                price_str = str(int(price))
            else:
                price_str = f"{price:.{price_precision}f}"
            
            # 如果有手数，显示手数信息
            if volume > 0:
                volume_str = f"{int(volume)}手" if volume == int(volume) else f"{volume:.1f}手"
                # 区分挂单线的止损/止盈线和持仓的止损/止盈线
                if is_pending_line:
                    return f"挂单{type_name} {price_str} {volume_str}"
                else:
                    return f"{type_name} {price_str} {volume_str}"
            else:
                # 区分挂单线的止损/止盈线和持仓的止损/止盈线
                if is_pending_line:
                    return f"挂单{type_name} {price_str}"
                else:
                    return f"{type_name} {price_str}"
        
        # 对于挂单线，显示方向（多单/空单）和手数
        if line_type == PriceLineType.PENDING:
            direction_text = "多单" if direction == "long" else "空单"
            # 获取挂单线的订单手数（从实例属性获取）
            order_volume = getattr(self, '_order_volume', None)
            
            if price_precision == 0:
                price_str = str(int(price))
            else:
                price_str = f"{price:.{price_precision}f}"
            
            # 如果有手数，显示手数信息
            if order_volume is not None and order_volume > 0:
                volume_str = f"{int(order_volume)}手" if order_volume == int(order_volume) else f"{order_volume:.1f}手"
                return f"{direction_text} {price_str} {volume_str}"
            else:
                return f"{direction_text} {price_str}"
        
        # 其他类型的价格线，正常显示
        # 根据精度格式化价格（0表示整数，MHImain默认显示整数）
        if price_precision == 0:
            return f"{type_name} {int(price)}"
        else:
            return f"{type_name} {price:.{price_precision}f}"

    def get_price(self) -> float:
        """Get current price of the line."""
        return self._price

    def set_price(self, price: float, price_precision: int = 0) -> None:
        """
        Update price of the line.

        Args:
            price: New price value
            price_precision: Number of decimal places (0 for integer, default 0 for MHImain)
        """
        self._price = price
        self.setPos(price)
        # Update label
        if self.label is not None:
            label_text = self._create_label(price, self._line_type, price_precision, self._direction)
            self.label.setText(label_text)
    
    def set_price_precision(self, precision: int) -> None:
        """Set price precision and update label."""
        if self.label is not None:
            label_text = self._create_label(self._price, self._line_type, precision, self._direction)
            self.label.setText(label_text)

    def get_line_type(self) -> PriceLineType:
        """Get line type."""
        return self._line_type

    def get_direction(self) -> str:
        """Get trading direction."""
        return self._direction
    
    def set_direction(self, direction: str, price_precision: int = 0) -> None:
        """
        设置交易方向并更新标签（主要用于挂单线显示方向）。
        
        Args:
            direction: 交易方向 ("long" 或 "short")
            price_precision: 价格精度（用于更新标签）
        """
        self._direction = direction
        # 更新标签显示（挂单线需要显示方向）
        if self._line_type == PriceLineType.PENDING:
            label_text = self._create_label(self._price, self._line_type, price_precision, self._direction)
            if self.label is not None:
                self.label.setText(label_text)
            # 更新画笔颜色以反映方向变化
            pen = self._create_pen(self._line_type, direction)
            self.setPen(pen)
            if self.label is not None:
                self.label.setColor(pen.color())

    def get_original_price(self) -> float:
        """Get original price (before drag)."""
        return self._original_price

    def set_original_price(self, price: float) -> None:
        """Set original price (for drag cancel)."""
        self._original_price = price
    
    def set_pnl(self, pnl: float) -> None:
        """设置浮动盈亏并更新标签"""
        self._pnl = pnl
        # 更新标签显示
        if self._line_type == PriceLineType.ENTRY:
            price_precision = 0  # 默认整数显示
            label_text = self._create_label(self._price, self._line_type, price_precision, self._direction)
            if self.label is not None:
                self.label.setText(label_text)
    
    def get_pnl(self) -> float:
        """获取浮动盈亏"""
        return getattr(self, '_pnl', 0.0)
    
    def set_volume(self, volume: float) -> None:
        """设置持仓手数并更新标签"""
        self._volume = volume
        # 更新标签显示（入场线、止损线、止盈线都需要更新）
        if self._line_type in (PriceLineType.ENTRY, PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
            price_precision = 0  # 默认整数显示
            label_text = self._create_label(self._price, self._line_type, price_precision, self._direction)
            if self.label is not None:
                self.label.setText(label_text)
    
    def get_volume(self) -> float:
        """获取持仓手数（用于入场线）"""
        return getattr(self, '_volume', 0.0)
    
    def get_order_volume(self) -> Optional[float]:
        """获取挂单线的订单手数（仅PENDING类型）"""
        return getattr(self, '_order_volume', None)
    
    def set_order_volume(self, volume: float) -> None:
        """设置挂单线的订单手数（仅PENDING类型）并更新标签"""
        self._order_volume = volume
        # 更新标签显示（挂单线需要显示手数）
        if self._line_type == PriceLineType.PENDING:
            price_precision = 0  # 默认整数显示
            label_text = self._create_label(self._price, self._line_type, price_precision, self._direction)
            if self.label is not None:
                self.label.setText(label_text)
    
    def get_order_offset(self) -> Optional[str]:
        """获取挂单线的开平类型（仅PENDING类型，返回"OPEN"或"CLOSE"）"""
        return getattr(self, '_order_offset', None)
    
    def set_order_offset(self, offset: str) -> None:
        """设置挂单线的开平类型（仅PENDING类型，应为"OPEN"或"CLOSE"）"""
        self._order_offset = offset
    
    def get_creation_time(self) -> Optional[float]:
        """获取创建时间（秒，用于防止创建后立即触发）"""
        return getattr(self, '_creation_time', None)
    
    def set_creation_time(self, creation_time: Optional[float] = None) -> None:
        """
        设置创建时间（秒，用于防止创建后立即触发）
        
        Args:
            creation_time: 创建时间（秒），如果为None则设置为当前时间。
                          如果需要显式设置为None（表示未激活），使用 set_creation_time_explicit(None)
        """
        if creation_time is None:
            from time import time
            creation_time = time()
        self._creation_time = creation_time
    
    def set_creation_time_explicit(self, creation_time: Optional[float]) -> None:
        """
        显式设置创建时间（允许设置为None）
        
        Args:
            creation_time: 创建时间（秒），可以为None（表示未激活）
        """
        self._creation_time = creation_time
    
    def set_associated_entry_line_id(self, entry_line_id: Optional[str]) -> None:
        """
        设置关联的入场线ID（用于止损/止盈线）
        
        Args:
            entry_line_id: 入场线ID
        """
        self.entry_line_id = entry_line_id
    
    def set_pnl_and_volume(self, pnl: float, volume: float) -> None:
        """同时设置浮动盈亏和持仓手数并更新标签"""
        self._pnl = pnl
        self._volume = volume
        # 更新标签显示
        if self._line_type == PriceLineType.ENTRY:
            price_precision = 0  # 默认整数显示
            label_text = self._create_label(self._price, self._line_type, price_precision, self._direction)
            if self.label is not None:
                self.label.setText(label_text)
                # 强制更新标签显示
                if hasattr(self.label, 'update'):
                    self.label.update()
    
    def set_vt_orderid(self, vt_orderid: str) -> None:
        """设置关联的订单ID"""
        self._vt_orderid = vt_orderid
    
    def get_vt_orderid(self) -> Optional[str]:
        """获取关联的订单ID"""
        return getattr(self, '_vt_orderid', None)


class PriceLineManager:
    """
    Manager for all price lines in the chart.
    
    Handles creation, update, and deletion of price lines.
    Supports optional database persistence.
    """

    def __init__(self, database=None, vt_symbol: Optional[str] = None, use_uuid: bool = True) -> None:
        """
        Initialize price line manager.
        
        Args:
            database: Optional PriceLineDatabase instance for persistence
            vt_symbol: VT symbol for this chart (used for filtering saved lines)
            use_uuid: If True, use UUID for line IDs. If False, use counter-based IDs.
        """
        # Map: line_id -> PriceLineItem
        self._lines: dict[str, PriceLineItem] = {}
        
        # Counter for generating unique line IDs (only used if use_uuid=False)
        self._line_id_counter: int = 0
        
        # Database for persistence (optional)
        self._database = database
        self._vt_symbol = vt_symbol
        
        # ID generation strategy
        self._use_uuid = use_uuid

    def create_line(
        self,
        price: float,
        line_type: PriceLineType,
        direction: str = "long",
        movable: bool = False,
        line_id: Optional[str] = None,
        price_precision: Optional[int] = None,
        vt_orderid: Optional[str] = None
    ) -> str:
        """
        Create a new price line.

        Args:
            price: Price value
            line_type: Type of price line
            direction: Trading direction ("long" or "short")
            movable: Whether the line can be dragged
            line_id: Optional custom line ID. If None, auto-generate.
            price_precision: Price precision (number of decimal places)
            vt_orderid: Optional VT order ID if linked to an order

        Returns:
            Line ID string
        """
        if line_id is None:
            # 根据价格线类型生成不同的前缀，便于区分和调试
            prefix_map = {
                PriceLineType.ENTRY: "entry",
                PriceLineType.PENDING: "pending",
                PriceLineType.STOP_LOSS: "stop",
                PriceLineType.TAKE_PROFIT: "profit",
                PriceLineType.PREVIEW: "preview",
            }
            prefix = prefix_map.get(line_type, "line")  # 默认使用 "line" 作为前缀
            
            if self._use_uuid:
                # 使用 UUID 生成唯一ID
                import uuid
                line_id = f"{prefix}_{uuid.uuid4().hex[:12]}"  # 使用UUID的前12位，保持可读性
            else:
                # 使用计数器生成ID（需要从数据库初始化计数器）
                line_id = f"{prefix}_{self._line_id_counter}"
                self._line_id_counter += 1

        if line_id in self._lines:
            raise ValueError(f"Line ID {line_id} already exists")

        line = PriceLineItem(
            price=price,
            line_type=line_type,
            direction=direction,
            movable=movable
        )
        
        # 设置价格精度（如果提供了，否则使用默认值0）
        if price_precision is not None:
            line.set_price_precision(price_precision)
        else:
            line.set_price_precision(0)  # 默认整数显示
        
        # 设置订单ID（如果提供）
        if vt_orderid:
            line.set_vt_orderid(vt_orderid)
        
        # 对于止损/止盈线，设置创建时间（用于防止创建后立即触发）
        # 注意：挂单线关联的止损/止盈线会在创建后立即将创建时间设置为None（表示未激活），
        # 只有在挂单成交后才激活（重新设置创建时间）
        if line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
            line.set_creation_time()

        self._lines[line_id] = line
        
        # 保存到数据库（如果启用）
        if self._database and self._vt_symbol:
            self._database.save_line(
                line_id=line_id,
                price=price,
                line_type=line_type,
                direction=direction,
                vt_symbol=self._vt_symbol,
                movable=movable,
                price_precision=price_precision or 0,
                vt_orderid=vt_orderid
            )
        
        return line_id

    def get_line(self, line_id: str) -> Optional[PriceLineItem]:
        """
        Get price line by ID.

        Args:
            line_id: Line ID

        Returns:
            PriceLineItem or None if not found
        """
        return self._lines.get(line_id)

    def update_line_price(self, line_id: str, price: float) -> bool:
        """
        Update price of a line.

        Args:
            line_id: Line ID
            price: New price value

        Returns:
            True if successful, False if line not found
        """
        line = self._lines.get(line_id)
        if line is None:
            return False

        line.set_price(price)
        
        # 更新数据库（如果启用）
        if self._database and self._vt_symbol:
            # 获取挂单参数（如果是PENDING类型）
            order_volume = None
            order_offset = None
            if line.get_line_type() == PriceLineType.PENDING:
                order_volume = line.get_order_volume()
                order_offset = line.get_order_offset()
            
            # 获取价格精度（从价格线对象获取，如果不可用则使用默认值0）
            price_precision = 0
            if hasattr(line, '_price_precision'):
                price_precision = getattr(line, '_price_precision', 0)
            
            self._database.save_line(
                line_id=line_id,
                price=price,
                line_type=line.get_line_type(),
                direction=line.get_direction(),
                vt_symbol=self._vt_symbol,
                movable=line.movable,
                price_precision=price_precision,
                vt_orderid=line.get_vt_orderid(),
                order_volume=order_volume,
                order_offset=order_offset
            )
        
        return True

    def delete_line(self, line_id: str) -> bool:
        """
        Delete a price line.

        Args:
            line_id: Line ID

        Returns:
            True if successful, False if line not found
        """
        line = self._lines.pop(line_id, None)
        if line is None:
            return False

        # Remove from plot/scene if it has a parent
        # Try multiple methods to ensure the line is removed from the UI
        if line.scene() is not None:
            # Method 1: Try to get parent PlotItem and remove
            # In pyqtgraph, InfiniteLine is added to PlotItem, so parent should be PlotItem or ViewBox
            parent = line.parentItem()
            if parent is not None:
                try:
                    # If parent is PlotItem, use removeItem
                    if hasattr(parent, 'removeItem'):
                        parent.removeItem(line)
                    # If parent is ViewBox, also try removeItem
                    elif hasattr(parent, 'removeItem'):
                        parent.removeItem(line)
                except Exception:
                    pass
            
            # Method 2: Try to get ViewBox and remove
            try:
                viewbox = line.getViewBox()
                if viewbox is not None:
                    viewbox.removeItem(line)
            except Exception:
                pass
            
            # Method 3: Traverse up the parent chain to find PlotItem
            try:
                item = line
                while item is not None:
                    parent = item.parentItem()
                    if parent is not None:
                        # Check if parent is a PlotItem (has addItem method)
                        if hasattr(parent, 'addItem') and hasattr(parent, 'removeItem'):
                            try:
                                parent.removeItem(line)
                                break
                            except Exception:
                                pass
                    item = parent
            except Exception:
                pass
            
            # Method 4: Remove from scene directly (last resort)
            try:
                scene = line.scene()
                if scene is not None:
                    scene.removeItem(line)
            except Exception:
                pass
        
        # 从数据库删除（如果启用）
        if self._database:
            self._database.delete_line(line_id)

        return True

    def get_all_lines(self) -> dict[str, PriceLineItem]:
        """
        Get all price lines.

        Returns:
            Dictionary mapping line_id to PriceLineItem
        """
        return self._lines.copy()

    def get_lines_by_type(self, line_type: PriceLineType) -> list[PriceLineItem]:
        """
        Get all lines of a specific type.

        Args:
            line_type: Type of price line

        Returns:
            List of PriceLineItem objects
        """
        return [
            line for line in self._lines.values()
            if line.get_line_type() == line_type
        ]

    def clear_all(self) -> None:
        """Clear all price lines."""
        # Remove all lines from their plots
        for line in list(self._lines.values()):
            if line.scene() is not None:
                plot = line.getViewBox()
                if plot is not None:
                    plot.removeItem(line)

        self._lines.clear()
    
    def clear_preview_lines(self, plot: Optional[object] = None) -> int:
        """
        清理所有预览线。
        
        Args:
            plot: PlotItem对象，用于从plot中移除预览线（可选）
            
        Returns:
            清理的预览线数量
        """
        preview_lines = self.get_lines_by_type(PriceLineType.PREVIEW)
        count = 0
        
        for line in preview_lines:
            # 找到对应的line_id
            line_id = None
            for lid, l in self._lines.items():
                if l == line:
                    line_id = lid
                    break
            
            if line_id:
                # 从plot中移除
                if plot and line.scene() is not None:
                    try:
                        plot.removeItem(line)
                    except Exception:
                        pass
                
                # 从管理器中删除
                self._lines.pop(line_id, None)
                
                # 从数据库删除（如果启用）
                if self._database:
                    self._database.delete_line(line_id)
                
                count += 1
        
        return count
    
    def set_database(self, database, vt_symbol: Optional[str] = None) -> None:
        """
        设置数据库和VT符号。
        
        Args:
            database: PriceLineDatabase 实例
            vt_symbol: VT符号
        """
        self._database = database
        self._vt_symbol = vt_symbol
    
    def load_from_database(self, plot: Optional[object] = None) -> int:
        """
        从数据库加载价格线。
        
        Args:
            plot: Optional PlotItem to add lines to
            
        Returns:
            加载的价格线数量
        """
        if not self._database or not self._vt_symbol:
            return 0
        
        lines_data = self._database.load_lines(vt_symbol=self._vt_symbol)
        
        # 调试日志：记录加载的价格线数量
        import sys
        if 'vnpy.trader.engine' in sys.modules:
            from vnpy.trader.engine import MainEngine
            # 尝试获取 main_engine 来记录日志
            # 这里我们暂时不记录，因为可能没有 main_engine
        
        count = 0
        max_counter = 0
        
        for line_data in lines_data:
            line_id = line_data["line_id"]
            
            # 如果已存在，跳过
            if line_id in self._lines:
                continue
            
            # 如果使用计数器模式，尝试从line_id中提取最大计数器值
            if not self._use_uuid and line_id.startswith("line_"):
                try:
                    # 尝试提取数字部分
                    counter_str = line_id[5:]  # 跳过 "line_"
                    if counter_str.isdigit():
                        counter_val = int(counter_str)
                        max_counter = max(max_counter, counter_val)
                except (ValueError, IndexError):
                    pass
            
            # 创建价格线
            line = PriceLineItem(
                price=line_data["price"],
                line_type=line_data["line_type"],
                direction=line_data["direction"],
                movable=line_data["movable"]
            )
            
            line.set_price_precision(line_data["price_precision"])
            if line_data["vt_orderid"]:
                line.set_vt_orderid(line_data["vt_orderid"])
            
            # 加载挂单参数（如果存在，仅PENDING类型）
            if line_data["line_type"] == PriceLineType.PENDING:
                # line_data 是字典，使用 .get() 方法安全获取
                order_volume = line_data.get("order_volume")
                order_offset = line_data.get("order_offset")
                if order_volume is not None:
                    line.set_order_volume(order_volume)
                if order_offset is not None:
                    line.set_order_offset(order_offset)
            
            self._lines[line_id] = line
            
            # 添加到 plot（如果提供）
            if plot and hasattr(plot, 'addItem'):
                plot.addItem(line)
            
            count += 1
        
        # 如果使用计数器模式，初始化计数器为最大ID+1，避免ID冲突
        if not self._use_uuid:
            self._line_id_counter = max_counter + 1
        
        return count

    def get_count(self) -> int:
        """Get total number of price lines."""
        return len(self._lines)

