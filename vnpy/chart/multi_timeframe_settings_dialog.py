"""
多周期K线显示设置对话框

可复用的设置对话框，用于集中管理多周期K线的显示属性。
设计考虑可整合到其他ChartWindow中。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vnpy.trader.ui import QtCore, QtWidgets


@dataclass
class MultiTimeframeSettings:
    """
    多周期K线显示设置数据类

    用于在对话框和widget之间传递设置数据
    """
    # 4小时K线设置
    opacity_4h: float = 0.05
    visible_4h: bool = True

    # 1小时K线设置
    opacity_1h: float = 0.10
    visible_1h: bool = True

    # 5分钟K线设置
    opacity_5m: float = 0.10
    visible_5m: bool = True


class MultiTimeframeSettingsDialog(QtWidgets.QDialog):
    """
    多周期K线显示设置对话框

    可复用的设置对话框，集中管理所有显示属性。
    """

    def __init__(
        self,
        settings: MultiTimeframeSettings | None = None,
        parent: QtWidgets.QWidget | None = None,
        on_preview: Callable[[MultiTimeframeSettings], None] | None = None
    ) -> None:
        """
        初始化设置对话框

        Args:
            settings: 当前设置（如果为None则使用默认值）
            parent: 父窗口
            on_preview: 实时预览回调函数（设置变化时立即调用）
        """
        super().__init__(parent)

        self._settings = settings or MultiTimeframeSettings()
        self._original_settings = MultiTimeframeSettings(
            opacity_4h=self._settings.opacity_4h,
            opacity_1h=self._settings.opacity_1h,
            opacity_5m=self._settings.opacity_5m,
            visible_4h=self._settings.visible_4h,
            visible_1h=self._settings.visible_1h,
            visible_5m=self._settings.visible_5m,
        )

        self._on_preview: Callable[[MultiTimeframeSettings], None] | None = on_preview

        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("多周期K线显示设置")
        self.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 创建滚动区域（如果将来设置项增多）
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # 4小时K线设置组
        group_4h = self._create_timeframe_group(
            "4小时K线 (4H)",
            self._settings.opacity_4h,
            self._settings.visible_4h
        )
        self._group_4h = group_4h
        content_layout.addWidget(group_4h)

        # 1小时K线设置组
        group_1h = self._create_timeframe_group(
            "1小时K线 (1H)",
            self._settings.opacity_1h,
            self._settings.visible_1h
        )
        self._group_1h = group_1h
        content_layout.addWidget(group_1h)

        # 5分钟K线设置组
        group_5m = self._create_timeframe_group(
            "5分钟K线 (5m)",
            self._settings.opacity_5m,
            self._settings.visible_5m
        )
        self._group_5m = group_5m
        content_layout.addWidget(group_5m)

        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        # 重置按钮
        reset_btn = QtWidgets.QPushButton("重置")
        reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_btn)

        # 确定和取消按钮
        ok_btn = QtWidgets.QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _on_cancel(self) -> None:
        """取消按钮处理：恢复原始设置"""
        if self._on_preview:
            # 恢复到原始设置
            self._on_preview(self._original_settings)
        self.reject()

    def _create_timeframe_group(
        self,
        title: str,
        init_opacity: float,
        init_visible: bool
    ) -> QtWidgets.QGroupBox:
        """
        创建单个周期的设置组

        Args:
            title: 组标题
            init_opacity: 初始透明度（0.0-1.0）
            init_visible: 初始显示状态

        Returns:
            QGroupBox对象
        """
        group = QtWidgets.QGroupBox(title)
        group_layout = QtWidgets.QVBoxLayout(group)
        group_layout.setSpacing(10)

        # 显示开关
        visible_checkbox = QtWidgets.QCheckBox("显示该周期")
        visible_checkbox.setChecked(init_visible)
        group_layout.addWidget(visible_checkbox)

        # 透明度设置
        opacity_layout = QtWidgets.QHBoxLayout()

        opacity_label = QtWidgets.QLabel("填充透明度:")
        opacity_label.setMinimumWidth(100)
        opacity_layout.addWidget(opacity_label)

        opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(int(init_opacity * 100))
        opacity_slider.setTickInterval(5)
        opacity_slider.setSingleStep(1)
        opacity_layout.addWidget(opacity_slider, stretch=1)

        opacity_value_label = QtWidgets.QLabel(f"{int(init_opacity * 100)}%")
        opacity_value_label.setMinimumWidth(50)
        opacity_value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        opacity_layout.addWidget(opacity_value_label)

        # 连接滑块和标签
        def update_label(value: int) -> None:
            opacity_value_label.setText(f"{value}%")

        opacity_slider.valueChanged.connect(update_label)

        group_layout.addLayout(opacity_layout)

        # 保存控件引用
        group.visible_checkbox = visible_checkbox
        group.opacity_slider = opacity_slider
        group.opacity_value_label = opacity_value_label

        # 连接实时预览信号
        if self._on_preview:
            opacity_slider.valueChanged.connect(self._on_setting_changed)
            visible_checkbox.toggled.connect(self._on_setting_changed)

        return group

    def _on_setting_changed(self) -> None:
        """设置变化时的回调（实时预览）"""
        if self._on_preview:
            settings = self.get_settings()
            self._on_preview(settings)

    def _on_reset(self) -> None:
        """重置到原始设置"""
        # 暂时断开信号，避免触发预览
        if self._on_preview:
            self._group_4h.opacity_slider.blockSignals(True)
            self._group_4h.visible_checkbox.blockSignals(True)
            self._group_1h.opacity_slider.blockSignals(True)
            self._group_1h.visible_checkbox.blockSignals(True)
            self._group_5m.opacity_slider.blockSignals(True)
            self._group_5m.visible_checkbox.blockSignals(True)

        # 重置4H
        self._group_4h.visible_checkbox.setChecked(self._original_settings.visible_4h)
        self._group_4h.opacity_slider.setValue(int(self._original_settings.opacity_4h * 100))

        # 重置1H
        self._group_1h.visible_checkbox.setChecked(self._original_settings.visible_1h)
        self._group_1h.opacity_slider.setValue(int(self._original_settings.opacity_1h * 100))

        # 重置5m
        self._group_5m.visible_checkbox.setChecked(self._original_settings.visible_5m)
        self._group_5m.opacity_slider.setValue(int(self._original_settings.opacity_5m * 100))

        # 恢复信号连接
        if self._on_preview:
            self._group_4h.opacity_slider.blockSignals(False)
            self._group_4h.visible_checkbox.blockSignals(False)
            self._group_1h.opacity_slider.blockSignals(False)
            self._group_1h.visible_checkbox.blockSignals(False)
            self._group_5m.opacity_slider.blockSignals(False)
            self._group_5m.visible_checkbox.blockSignals(False)
            # 触发一次预览
            self._on_setting_changed()

    def get_settings(self) -> MultiTimeframeSettings:
        """
        获取当前设置

        Returns:
            MultiTimeframeSettings对象
        """
        return MultiTimeframeSettings(
            opacity_4h=self._group_4h.opacity_slider.value() / 100.0,
            visible_4h=self._group_4h.visible_checkbox.isChecked(),
            opacity_1h=self._group_1h.opacity_slider.value() / 100.0,
            visible_1h=self._group_1h.visible_checkbox.isChecked(),
            opacity_5m=self._group_5m.opacity_slider.value() / 100.0,
            visible_5m=self._group_5m.visible_checkbox.isChecked(),
        )


def show_settings_dialog(
    current_settings: MultiTimeframeSettings | None = None,
    parent: QtWidgets.QWidget | None = None,
    on_apply: Callable[[MultiTimeframeSettings], None] | None = None,
    on_preview: Callable[[MultiTimeframeSettings], None] | None = None
) -> MultiTimeframeSettings | None:
    """
    显示设置对话框（便捷函数）

    Args:
        current_settings: 当前设置
        parent: 父窗口
        on_apply: 应用设置的回调函数（如果提供，会在确定时调用）
        on_preview: 实时预览回调函数（设置变化时立即调用，用于实时预览效果）

    Returns:
        如果用户点击确定，返回新的设置；如果取消，返回None
    """
    dialog = MultiTimeframeSettingsDialog(
        current_settings,
        parent,
        on_preview=on_preview
    )

    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        new_settings = dialog.get_settings()
        if on_apply:
            on_apply(new_settings)
        return new_settings

    return None

