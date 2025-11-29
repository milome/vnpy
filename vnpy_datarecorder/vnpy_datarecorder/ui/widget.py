from datetime import datetime
from typing import List

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.event import EVENT_CONTRACT
from vnpy.trader.object import ContractData
from vnpy.trader.constant import Interval

from ..engine import (
    APP_NAME,
    EVENT_RECORDER_LOG,
    EVENT_RECORDER_UPDATE,
    RecorderEngine
)


class RecorderManager(QtWidgets.QWidget):
    """"""

    signal_log: QtCore.Signal = QtCore.Signal(Event)
    signal_update: QtCore.Signal = QtCore.Signal(Event)
    signal_contract: QtCore.Signal = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.recorder_engine: RecorderEngine = main_engine.get_engine(APP_NAME)

        self.init_ui()
        self.register_event()
        self.recorder_engine.put_event()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle("行情记录")
        self.resize(1000, 600)

        # Create widgets
        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.interval_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(60)
        self.interval_spin.setValue(self.recorder_engine.timer_interval)
        self.interval_spin.setSuffix("秒")
        self.interval_spin.valueChanged.connect(self.set_interval)

        contracts: list[ContractData] = self.main_engine.get_all_contracts()
        self.vt_symbols: list = [contract.vt_symbol for contract in contracts]

        self.symbol_completer: QtWidgets.QCompleter = QtWidgets.QCompleter(self.vt_symbols)
        self.symbol_completer.setFilterMode(QtCore.Qt.MatchContains)
        self.symbol_completer.setCompletionMode(self.symbol_completer.CompletionMode.PopupCompletion)
        self.symbol_line.setCompleter(self.symbol_completer)

        # 周期选择器（多选）- 放在最显眼的位置
        self.interval_checkboxes: dict[Interval, QtWidgets.QCheckBox] = {}
        interval_group = QtWidgets.QGroupBox("K线周期选择（可多选）")
        interval_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        interval_layout = QtWidgets.QHBoxLayout()
        interval_layout.setSpacing(20)
        interval_layout.setContentsMargins(15, 10, 15, 10)
        
        # 支持的周期
        supported_intervals = [
            (Interval.MINUTE, "1分钟"),
            (Interval.MINUTE_5, "5分钟"),
            (Interval.HOUR, "1小时"),
            (Interval.HOUR_4, "4小时"),
        ]
        
        for interval, label in supported_intervals:
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setStyleSheet("QCheckBox { font-size: 11px; }")
            if interval == Interval.MINUTE:
                checkbox.setChecked(True)  # 默认选中1分钟
            self.interval_checkboxes[interval] = checkbox
            interval_layout.addWidget(checkbox)
        
        interval_layout.addStretch()
        interval_group.setLayout(interval_layout)

        add_bar_button: QtWidgets.QPushButton = QtWidgets.QPushButton("添加")
        add_bar_button.clicked.connect(self.add_bar_recording)

        remove_bar_button: QtWidgets.QPushButton = QtWidgets.QPushButton("移除")
        remove_bar_button.clicked.connect(self.remove_bar_recording)

        add_tick_button: QtWidgets.QPushButton = QtWidgets.QPushButton("添加")
        add_tick_button.clicked.connect(self.add_tick_recording)

        remove_tick_button: QtWidgets.QPushButton = QtWidgets.QPushButton("移除")
        remove_tick_button.clicked.connect(self.remove_tick_recording)

        self.bar_recording_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.bar_recording_edit.setReadOnly(True)

        self.tick_recording_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.tick_recording_edit.setReadOnly(True)

        self.log_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        
        # 状态提示标签（显示操作结果）
        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: #00ff00;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 11px;
            }
        """)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Set layout
        grid: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("K线记录"), 0, 0)
        grid.addWidget(add_bar_button, 0, 1)
        grid.addWidget(remove_bar_button, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Tick记录"), 1, 0)
        grid.addWidget(add_tick_button, 1, 1)
        grid.addWidget(remove_tick_button, 1, 2)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("本地代码", self.symbol_line)
        form.addRow("写入间隔", self.interval_spin)

        hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox.addLayout(form)
        hbox.addWidget(QtWidgets.QLabel("     "))
        hbox.addLayout(grid)
        hbox.addStretch()

        grid2: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        grid2.addWidget(QtWidgets.QLabel("K线记录列表"), 0, 0)
        grid2.addWidget(QtWidgets.QLabel("Tick记录列表"), 0, 1)
        grid2.addWidget(self.bar_recording_edit, 1, 0)
        grid2.addWidget(self.tick_recording_edit, 1, 1)
        grid2.addWidget(self.log_edit, 2, 0, 1, 2)

        # 主布局：周期选择器在最顶部，然后是输入区域，最后是列表区域
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)
        vbox.addWidget(interval_group)  # 周期选择器放在最顶部
        vbox.addLayout(hbox)  # 输入和按钮区域
        vbox.addWidget(self.status_label)  # 状态提示
        vbox.addLayout(grid2)  # 列表区域
        self.setLayout(vbox)

    def register_event(self) -> None:
        """"""
        self.signal_log.connect(self.process_log_event)
        self.signal_contract.connect(self.process_contract_event)
        self.signal_update.connect(self.process_update_event)

        self.event_engine.register(EVENT_CONTRACT, self.signal_contract.emit)
        self.event_engine.register(EVENT_RECORDER_LOG, self.signal_log.emit)
        self.event_engine.register(EVENT_RECORDER_UPDATE, self.signal_update.emit)

    def process_log_event(self, event: Event) -> None:
        """"""
        timestamp: str = datetime.now().strftime("%H:%M:%S")
        msg: str = f"{timestamp}\t{event.data}"
        self.log_edit.append(msg)
        
        # 如果日志包含成功信息，更新状态提示
        log_data = str(event.data)
        if "添加K线记录成功" in log_data:
            # 格式：添加K线记录成功：{vt_symbol} (周期: {intervals})
            parts = log_data.split("：")
            if len(parts) > 1:
                info = parts[1].strip()
                self.show_status(f"✓ 已添加：{info}，配置已自动保存", is_success=True)
        elif "更新K线记录成功" in log_data:
            # 格式：更新K线记录成功：{vt_symbol} (原周期: ... → 新周期: ... | 新增: ... | 移除: ...)
            parts = log_data.split("：")
            if len(parts) > 1:
                info = parts[1].strip()
                self.show_status(f"✓ 已更新：{info}，配置已自动保存", is_success=True)
        elif "更新K线记录" in log_data and "无变化" in log_data:
            # 格式：更新K线记录：{vt_symbol} (周期: ..., 无变化)
            parts = log_data.split("：")
            if len(parts) > 1:
                info = parts[1].strip()
                self.show_status(f"ℹ {info}，配置已保存", is_success=True)
        elif "添加Tick记录成功" in log_data:
            parts = log_data.split("：")
            if len(parts) > 1:
                info = parts[1].strip()
                self.show_status(f"✓ 已添加Tick录制：{info}，配置已自动保存", is_success=True)
        elif "移除K线记录成功" in log_data or "移除Tick记录成功" in log_data:
            parts = log_data.split("：")
            if len(parts) > 1:
                info = parts[1].strip()
                self.show_status(f"✓ 已移除：{info}，配置已自动保存", is_success=True)

    def process_update_event(self, event: Event) -> None:
        """"""
        data: dict = event.data

        self.bar_recording_edit.clear()
        # 显示K线录制列表，包含周期信息
        bar_lines = []
        for vt_symbol in data["bar"]:
            # 获取该合约的录制周期
            if vt_symbol in self.recorder_engine.bar_recordings:
                intervals = self.recorder_engine.bar_recordings[vt_symbol].get("intervals", [Interval.MINUTE.value])
                
                # 确保intervals是列表格式
                if isinstance(intervals, str):
                    # 旧格式：单个字符串
                    intervals = [intervals]
                elif not isinstance(intervals, list):
                    # 其他格式，转换为列表
                    intervals = [intervals] if intervals else [Interval.MINUTE.value]
                elif len(intervals) == 0:
                    # 空列表，使用默认值
                    intervals = [Interval.MINUTE.value]
                
                # 将Interval.value转换为友好的中文显示
                interval_labels = []
                interval_map = {
                    Interval.MINUTE.value: "1分钟",
                    Interval.MINUTE_5.value: "5分钟",
                    Interval.HOUR.value: "1小时",
                    Interval.HOUR_4.value: "4小时",
                }
                for interval_value in intervals:
                    label = interval_map.get(interval_value, str(interval_value))
                    interval_labels.append(label)
                
                interval_str = ", ".join(interval_labels)
                bar_lines.append(f"{vt_symbol}\n  周期: {interval_str}")
            else:
                bar_lines.append(vt_symbol)
        bar_text: str = "\n".join(bar_lines)
        self.bar_recording_edit.setText(bar_text)

        self.tick_recording_edit.clear()
        tick_text: str = "\n".join(data["tick"])
        self.tick_recording_edit.setText(tick_text)

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract: ContractData = event.data
        self.vt_symbols.append(contract.vt_symbol)

        model: QtCore.QAbstractItemModel = self.symbol_completer.model()
        model.setStringList(self.vt_symbols)

    def add_bar_recording(self) -> None:
        """"""
        vt_symbol: str = self.symbol_line.text().strip()
        if not vt_symbol:
            self.show_status("错误：请输入合约代码", is_error=True)
            return
        
        # 获取选中的周期
        selected_intervals: List[Interval] = []
        for interval, checkbox in self.interval_checkboxes.items():
            if checkbox.isChecked():
                selected_intervals.append(interval)
        
        if not selected_intervals:
            # 如果没有选中任何周期，默认使用1分钟
            selected_intervals = [Interval.MINUTE]
        
        # 检查是否已存在该合约的录制
        is_existing = vt_symbol in self.recorder_engine.bar_recordings
        
        # 显示正在处理的状态
        interval_labels = {
            Interval.MINUTE: "1分钟",
            Interval.MINUTE_5: "5分钟",
            Interval.HOUR: "1小时",
            Interval.HOUR_4: "4小时",
        }
        interval_names = [interval_labels.get(i, i.value) for i in selected_intervals]
        
        if is_existing:
            # 获取原有周期
            existing_intervals = self.recorder_engine.bar_recordings[vt_symbol].get("intervals", [Interval.MINUTE.value])
            if isinstance(existing_intervals, list) and existing_intervals:
                if isinstance(existing_intervals[0], str):
                    existing_intervals_enum = [Interval(i) for i in existing_intervals]
                else:
                    existing_intervals_enum = existing_intervals
                existing_names = [interval_labels.get(i, i.value) for i in existing_intervals_enum]
                self.show_status(
                    f"正在更新录制：{vt_symbol}\n原周期: {', '.join(existing_names)} → 新周期: {', '.join(interval_names)}...",
                    is_processing=True
                )
            else:
                self.show_status(f"正在更新录制：{vt_symbol} (周期: {', '.join(interval_names)})...", is_processing=True)
        else:
            self.show_status(f"正在添加录制：{vt_symbol} (周期: {', '.join(interval_names)})...", is_processing=True)
        
        # 添加录制（会自动保存配置）
        self.recorder_engine.add_bar_recording(vt_symbol, selected_intervals)
        
        # 显示成功状态（会在日志事件中更新，这里先显示临时状态）
        if is_existing:
            self.show_status(f"✓ 已更新：{vt_symbol} (周期: {', '.join(interval_names)})，配置已保存", is_success=True)
        else:
            self.show_status(f"✓ 已添加：{vt_symbol} (周期: {', '.join(interval_names)})，配置已保存", is_success=True)

    def add_tick_recording(self) -> None:
        """"""
        vt_symbol: str = self.symbol_line.text().strip()
        if not vt_symbol:
            self.show_status("错误：请输入合约代码", is_error=True)
            return
        
        self.show_status(f"正在添加Tick录制：{vt_symbol}...", is_processing=True)
        self.recorder_engine.add_tick_recording(vt_symbol)
        self.show_status(f"✓ 已添加Tick录制：{vt_symbol}，配置已保存", is_success=True)

    def remove_bar_recording(self) -> None:
        """"""
        vt_symbol: str = self.symbol_line.text().strip()
        if not vt_symbol:
            self.show_status("错误：请输入合约代码", is_error=True)
            return
        
        self.show_status(f"正在移除K线录制：{vt_symbol}...", is_processing=True)
        self.recorder_engine.remove_bar_recording(vt_symbol)
        self.show_status(f"✓ 已移除K线录制：{vt_symbol}，配置已保存", is_success=True)

    def remove_tick_recording(self) -> None:
        """"""
        vt_symbol: str = self.symbol_line.text().strip()
        if not vt_symbol:
            self.show_status("错误：请输入合约代码", is_error=True)
            return
        
        self.show_status(f"正在移除Tick录制：{vt_symbol}...", is_processing=True)
        self.recorder_engine.remove_tick_recording(vt_symbol)
        self.show_status(f"✓ 已移除Tick录制：{vt_symbol}，配置已保存", is_success=True)

    def set_interval(self, interval: int) -> None:
        """"""
        self.recorder_engine.timer_interval = interval
        self.show_status(f"写入间隔已更新为 {interval} 秒", is_success=True)
    
    def show_status(self, message: str, is_success: bool = False, is_error: bool = False, is_processing: bool = False) -> None:
        """
        显示状态提示
        
        Args:
            message: 提示消息
            is_success: 是否成功状态（绿色）
            is_error: 是否错误状态（红色）
            is_processing: 是否处理中状态（黄色）
        """
        self.status_label.setText(message)
        
        if is_success:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #00ff00;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)
        elif is_error:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #ff4444;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)
        elif is_processing:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #ffaa00;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)
        else:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #2b2b2b;
                    color: #888888;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }
            """)
