"""
Order dialog for drawing order mode.

Provides a dialog for confirming order details before submitting.
"""

from typing import Optional

from vnpy.trader.ui import QtWidgets, QtCore, QtGui
from vnpy.trader.constant import Direction, Offset, OrderType
from vnpy.trader.locale import _


class OrderDialog(QtWidgets.QDialog):
    """
    Dialog for confirming order details in drawing order mode.
    """

    def __init__(
        self,
        price: float,
        direction: str = "long",
        pricetick: float = 1.0,
        size: float = 1.0,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        """
        Initialize order dialog.

        Args:
            price: Order price
            direction: Trading direction ("long" or "short")
            pricetick: Minimum price tick (最小变动单位)
            size: Contract size (合约乘数，一跳的价格数)
            parent: Parent widget
        """
        super().__init__(parent)

        self._price: float = price
        self._direction: str = direction
        self._pricetick: float = pricetick
        self._size: float = size  # 合约乘数（一跳的价格数）
        self._confirmed: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.setWindowTitle(_("确认下单"))
        self.setMinimumWidth(300)

        # Price display (read-only)
        price_label = QtWidgets.QLabel(_("价格:"))
        self._price_line = QtWidgets.QLineEdit()
        # MHImain价格显示为整数，默认精度为0
        self._price_precision = 0  # 默认整数显示
        self._price_line.setText(f"{int(self._price)}")
        self._price_line.setReadOnly(True)

        # Direction
        direction_label = QtWidgets.QLabel(_("方向:"))
        self._direction_combo = QtWidgets.QComboBox()
        self._direction_combo.addItems([_("多"), _("空")])
        if self._direction == "long":
            self._direction_combo.setCurrentIndex(0)
        else:
            self._direction_combo.setCurrentIndex(1)
        
        # Connect direction change to update stop loss/take profit defaults
        self._direction_combo.currentTextChanged.connect(self._update_stop_loss_default)
        self._direction_combo.currentTextChanged.connect(self._update_take_profit_default)

        # Offset
        offset_label = QtWidgets.QLabel(_("开平:"))
        self._offset_combo = QtWidgets.QComboBox()
        self._offset_combo.addItems([
            _("开"), _("平"), _("平今"), _("平昨")
        ])
        self._offset_combo.setCurrentIndex(0)  # Default to OPEN

        # Volume
        volume_label = QtWidgets.QLabel(_("数量:"))
        self._volume_spin = QtWidgets.QSpinBox()
        self._volume_spin.setMinimum(1)
        self._volume_spin.setMaximum(10000)
        self._volume_spin.setValue(1)

        # Stop Loss (按点数设置)
        self._stop_loss_check = QtWidgets.QCheckBox(_("设置止损"))
        self._stop_loss_points = QtWidgets.QSpinBox()
        self._stop_loss_points.setMinimum(1)
        self._stop_loss_points.setMaximum(10000)
        # 默认止损：50个点
        self._stop_loss_points.setValue(50)
        self._stop_loss_points.setEnabled(False)
        self._stop_loss_check.toggled.connect(self._stop_loss_points.setEnabled)
        
        # 显示止损价格（只读）
        self._stop_loss_price_label = QtWidgets.QLabel()
        self._stop_loss_price_label.setStyleSheet("color: gray;")
        self._update_stop_loss_price_display()
        self._stop_loss_points.valueChanged.connect(self._update_stop_loss_price_display)
        self._stop_loss_check.toggled.connect(self._update_stop_loss_price_display)

        # Take Profit (按点数设置)
        self._take_profit_check = QtWidgets.QCheckBox(_("设置止盈"))
        self._take_profit_points = QtWidgets.QSpinBox()
        self._take_profit_points.setMinimum(1)
        self._take_profit_points.setMaximum(10000)
        # 默认止盈：50个点
        self._take_profit_points.setValue(50)
        self._take_profit_points.setEnabled(False)
        self._take_profit_check.toggled.connect(self._take_profit_points.setEnabled)
        
        # 显示止盈价格（只读）
        self._take_profit_price_label = QtWidgets.QLabel()
        self._take_profit_price_label.setStyleSheet("color: gray;")
        self._update_take_profit_price_display()
        self._take_profit_points.valueChanged.connect(self._update_take_profit_price_display)
        self._take_profit_check.toggled.connect(self._update_take_profit_price_display)

        # Buttons
        confirm_button = QtWidgets.QPushButton(_("确认"))
        confirm_button.clicked.connect(self._on_confirm)
        cancel_button = QtWidgets.QPushButton(_("取消"))
        cancel_button.clicked.connect(self.reject)

        # Layout
        layout = QtWidgets.QFormLayout()
        layout.addRow(price_label, self._price_line)
        layout.addRow(direction_label, self._direction_combo)
        layout.addRow(offset_label, self._offset_combo)
        layout.addRow(volume_label, self._volume_spin)
        
        # Stop Loss row
        stop_loss_row = QtWidgets.QHBoxLayout()
        stop_loss_row.addWidget(self._stop_loss_check)
        stop_loss_row.addWidget(QtWidgets.QLabel(_("点数:")))
        stop_loss_row.addWidget(self._stop_loss_points)
        stop_loss_row.addWidget(self._stop_loss_price_label)
        stop_loss_row.addStretch()
        layout.addRow(QtWidgets.QLabel(""), stop_loss_row)
        
        # Take Profit row
        take_profit_row = QtWidgets.QHBoxLayout()
        take_profit_row.addWidget(self._take_profit_check)
        take_profit_row.addWidget(QtWidgets.QLabel(_("点数:")))
        take_profit_row.addWidget(self._take_profit_points)
        take_profit_row.addWidget(self._take_profit_price_label)
        take_profit_row.addStretch()
        layout.addRow(QtWidgets.QLabel(""), take_profit_row)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _on_confirm(self) -> None:
        """Handle confirm button click."""
        self._confirmed = True
        self.accept()

    def get_order_params(self) -> dict:
        """
        Get order parameters from dialog.

        Returns:
            Dictionary with order parameters:
            - price: float
            - direction: Direction
            - offset: Offset
            - order_type: OrderType
            - volume: int
        """
        # Direction
        direction_text = self._direction_combo.currentText()
        if direction_text == _("多"):
            direction = Direction.LONG
        else:
            direction = Direction.SHORT

        # Offset
        offset_text = self._offset_combo.currentText()
        offset_map = {
            _("开"): Offset.OPEN,
            _("平"): Offset.CLOSE,
            _("平今"): Offset.CLOSETODAY,
            _("平昨"): Offset.CLOSEYESTERDAY
        }
        offset = offset_map.get(offset_text, Offset.OPEN)

        result = {
            "price": self._price,
            "direction": direction,
            "offset": offset,
            "order_type": OrderType.LIMIT,  # 画线下单默认使用限价单
            "volume": self._volume_spin.value()
        }
        
        # Add stop loss and take profit if enabled (按点数计算价格)
        # 使用当前选择的方向，而不是初始方向
        direction_text = self._direction_combo.currentText()
        is_long = (direction_text == _("多"))
        
        if self._stop_loss_check.isChecked():
            points = self._stop_loss_points.value()
            # 确保 pricetick 至少为 1.0（MHImain 的最小变动单位是 1 个点）
            pricetick = max(self._pricetick, 1.0) if self._pricetick > 0 else 1.0
            pricetick_int = int(pricetick)  # 使用整数pricetick
            # 使用整数订单价格进行计算
            price_int = int(self._price)
            if is_long:
                # 做多：止损价格 = 订单价格 - 点数 * pricetick（整数计算）
                stop_loss_price = price_int - points * pricetick_int
            else:
                # 做空：止损价格 = 订单价格 + 点数 * pricetick（整数计算）
                stop_loss_price = price_int + points * pricetick_int
            result["stop_loss"] = float(stop_loss_price)  # 转换为float以保持兼容性
            result["stop_loss_points"] = points
            # 调试日志
            print(f"[OrderDialog] 止损计算: 方向={'多' if is_long else '空'}, 订单价格={price_int}, 点数={points}, pricetick={pricetick_int}, 止损价格={stop_loss_price}")
        else:
            result["stop_loss"] = None
            result["stop_loss_points"] = None
            
        if self._take_profit_check.isChecked():
            points = self._take_profit_points.value()
            # 确保 pricetick 至少为 1.0（MHImain 的最小变动单位是 1 个点）
            pricetick = max(self._pricetick, 1.0) if self._pricetick > 0 else 1.0
            pricetick_int = int(pricetick)  # 使用整数pricetick
            # 使用整数订单价格进行计算
            price_int = int(self._price)
            if is_long:
                # 做多：止盈价格 = 订单价格 + 点数 * pricetick（整数计算）
                take_profit_price = price_int + points * pricetick_int
            else:
                # 做空：止盈价格 = 订单价格 - 点数 * pricetick（整数计算）
                take_profit_price = price_int - points * pricetick_int
            result["take_profit"] = float(take_profit_price)  # 转换为float以保持兼容性
            result["take_profit_points"] = points
            # 调试日志
            print(f"[OrderDialog] 止盈计算: 方向={'多' if is_long else '空'}, 订单价格={price_int}, 点数={points}, pricetick={pricetick_int}, 止盈价格={take_profit_price}")
        else:
            result["take_profit"] = None
            result["take_profit_points"] = None
        
        # 添加价格精度
        result["price_precision"] = getattr(self, '_price_precision', 0)
        
        return result

    def was_confirmed(self) -> bool:
        """Check if dialog was confirmed."""
        return self._confirmed
    
    def _update_stop_loss_default(self) -> None:
        """Update stop loss default value when direction changes."""
        self._update_stop_loss_price_display()
    
    def _update_take_profit_default(self) -> None:
        """Update take profit default value when direction changes."""
        self._update_take_profit_price_display()
    
    def _update_stop_loss_price_display(self) -> None:
        """Update stop loss price display label."""
        if self._stop_loss_check.isChecked():
            points = self._stop_loss_points.value()
            direction_text = self._direction_combo.currentText()
            # 确保 pricetick 至少为 1.0
            pricetick = max(self._pricetick, 1.0) if self._pricetick > 0 else 1.0
            pricetick_int = int(pricetick)  # 使用整数pricetick
            # 使用整数订单价格进行计算
            price_int = int(self._price)
            # 根据当前选择的方向计算止损价格（整数计算）
            # 止损价格 = 订单价格 ± 点数 * pricetick
            if direction_text == _("多"):
                # 做多：止损价格 = 订单价格 - 点数 * pricetick
                price = price_int - points * pricetick_int
            else:
                # 做空：止损价格 = 订单价格 + 点数 * pricetick
                price = price_int + points * pricetick_int
            # 根据价格精度显示（MHImain默认整数）
            if self._price_precision == 0:
                self._stop_loss_price_label.setText(f"({price})")
            else:
                self._stop_loss_price_label.setText(f"({price:.{self._price_precision}f})")
        else:
            self._stop_loss_price_label.setText("")
    
    def _update_take_profit_price_display(self) -> None:
        """Update take profit price display label."""
        if self._take_profit_check.isChecked():
            points = self._take_profit_points.value()
            direction_text = self._direction_combo.currentText()
            # 确保 pricetick 至少为 1.0
            pricetick = max(self._pricetick, 1.0) if self._pricetick > 0 else 1.0
            pricetick_int = int(pricetick)  # 使用整数pricetick
            # 使用整数订单价格进行计算
            price_int = int(self._price)
            # 根据当前选择的方向计算止盈价格（整数计算）
            # 止盈价格 = 订单价格 ± 点数 * pricetick
            if direction_text == _("多"):
                # 做多：止盈价格 = 订单价格 + 点数 * pricetick
                price = price_int + points * pricetick_int
            else:
                # 做空：止盈价格 = 订单价格 - 点数 * pricetick
                price = price_int - points * pricetick_int
            # 根据价格精度显示（MHImain默认整数）
            if self._price_precision == 0:
                self._take_profit_price_label.setText(f"({price})")
            else:
                self._take_profit_price_label.setText(f"({price:.{self._price_precision}f})")
        else:
            self._take_profit_price_label.setText("")

