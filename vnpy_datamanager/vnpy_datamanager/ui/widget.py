from functools import partial
from datetime import datetime, timedelta

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.database import DB_TZ
from vnpy.trader.utility import available_timezones

from ..engine import APP_NAME, ManagerEngine, BarOverview


INTERVAL_NAME_MAP = {
    Interval.MINUTE: "分钟线",
    Interval.MINUTE_5: "5分钟线",
    Interval.HOUR: "小时线",
    Interval.HOUR_4: "4小时线",
    Interval.DAILY: "日线",
}


class ManagerWidget(QtWidgets.QWidget):
    """"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.engine: ManagerEngine = main_engine.get_engine(APP_NAME)
        self.event_engine: EventEngine = event_engine
        
        # 自动更新相关
        self.auto_update_timer: QtCore.QTimer | None = None
        self.auto_update_enabled: bool = False
        self.auto_update_interval: int = 60  # 默认60分钟
        self.is_updating: bool = False  # 标记是否正在更新，避免重复更新

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle("数据管理")

        self.init_tree()
        self.init_table()

        refresh_button: QtWidgets.QPushButton = QtWidgets.QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_tree)

        import_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导入数据")
        import_button.clicked.connect(self.import_data)

        update_button: QtWidgets.QPushButton = QtWidgets.QPushButton("更新数据")
        update_button.clicked.connect(self.update_data)

        download_button: QtWidgets.QPushButton = QtWidgets.QPushButton("下载数据")
        download_button.clicked.connect(self.download_data)
        
        # 自动更新相关控件
        # 创建一个分组框来包含自动更新相关控件
        auto_update_group = QtWidgets.QGroupBox("自动更新")
        auto_update_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #555;
                border-radius: 3px;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        auto_update_layout = QtWidgets.QHBoxLayout()
        auto_update_layout.setContentsMargins(10, 5, 10, 5)
        auto_update_layout.setSpacing(10)
        
        self.auto_update_checkbox: QtWidgets.QCheckBox = QtWidgets.QCheckBox("启用")
        self.auto_update_checkbox.setChecked(False)
        self.auto_update_checkbox.setToolTip("启用后，系统将按设定间隔自动更新数据")
        self.auto_update_checkbox.stateChanged.connect(self.on_auto_update_changed)
        
        self.auto_update_interval_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.auto_update_interval_spin.setMinimum(5)
        self.auto_update_interval_spin.setMaximum(1440)
        self.auto_update_interval_spin.setValue(60)
        self.auto_update_interval_spin.setSuffix(" 分钟")
        self.auto_update_interval_spin.setEnabled(False)
        self.auto_update_interval_spin.setToolTip("设置自动更新的时间间隔（5-1440分钟）")
        self.auto_update_interval_spin.valueChanged.connect(self.on_auto_update_interval_changed)
        
        # 下次更新时间标签
        self.next_update_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.next_update_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 5px;")
        self.next_update_label.setEnabled(False)
        self.next_update_label.setToolTip("显示下次自动更新的时间")
        
        auto_update_layout.addWidget(self.auto_update_checkbox)
        auto_update_layout.addWidget(QtWidgets.QLabel("间隔:"))
        auto_update_layout.addWidget(self.auto_update_interval_spin)
        auto_update_layout.addWidget(self.next_update_label)
        auto_update_layout.addStretch()
        auto_update_group.setLayout(auto_update_layout)

        hbox1: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox1.addWidget(refresh_button)
        hbox1.addStretch()
        hbox1.addWidget(import_button)
        hbox1.addWidget(update_button)
        hbox1.addWidget(download_button)
        hbox1.addWidget(auto_update_group)

        hbox2: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox2.addWidget(self.tree)
        hbox2.addWidget(self.table)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)

        self.setLayout(vbox)

    def init_tree(self) -> None:
        """"""
        labels: list = [
            "数据",
            "本地代码",
            "代码",
            "交易所",
            "数据量",
            "开始时间",
            "结束时间",
            "",
            "",
            ""
        ]

        self.tree: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(len(labels))
        self.tree.setHeaderLabels(labels)

    def init_table(self) -> None:
        """"""
        labels: list = [
            "时间",
            "开盘价",
            "最高价",
            "最低价",
            "收盘价",
            "成交量",
            "成交额",
            "持仓量"
        ]

        self.table: QtWidgets.QTableWidget = QtWidgets.QTableWidget()
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

    def refresh_tree(self) -> None:
        """"""
        self.tree.clear()

        # 初始化节点缓存字典
        interval_childs: dict[Interval, QtWidgets.QTreeWidgetItem] = {}
        exchange_childs: dict[tuple[Interval, Exchange], QtWidgets.QTreeWidgetItem] = {}

        # 查询数据汇总，并基于合约代码进行排序
        overviews: list[BarOverview] = self.engine.get_bar_overview()
        overviews.sort(key=lambda x: x.symbol)

        # 添加数据周期节点
        for interval in [Interval.MINUTE, Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4, Interval.DAILY]:
            interval_child = QtWidgets.QTreeWidgetItem()
            interval_childs[interval] = interval_child

            interval_name: str = INTERVAL_NAME_MAP.get(interval, interval.value)
            interval_child.setText(0, interval_name)

        # 遍历添加数据节点
        for overview in overviews:
            # 跳过无效的interval或exchange
            if overview.interval is None or overview.exchange is None:
                continue
            
            # 确保interval是Interval枚举类型
            interval = overview.interval
            if isinstance(interval, str):
                try:
                    interval = Interval(interval)
                except (ValueError, TypeError):
                    continue
            elif not isinstance(interval, Interval):
                # 如果不是Interval枚举，尝试转换
                try:
                    # 尝试通过value属性获取值
                    if hasattr(interval, 'value'):
                        interval = Interval(interval.value)
                    else:
                        interval = Interval(str(interval))
                except (ValueError, TypeError, AttributeError):
                    continue
            
            # 通过value匹配interval（因为枚举实例可能不同但value相同）
            matched_interval = None
            for key_interval in interval_childs.keys():
                if key_interval.value == interval.value:
                    matched_interval = key_interval
                    break
            
            if matched_interval is None:
                continue
            
            interval = matched_interval
            
            # 获取交易所节点
            key: tuple = (interval, overview.exchange)
            exchange_child: QtWidgets.QTreeWidgetItem = exchange_childs.get(key, None)

            if not exchange_child:
                interval_child = interval_childs[interval]

                exchange_child = QtWidgets.QTreeWidgetItem(interval_child)
                exchange_child.setText(0, overview.exchange.value)

                exchange_childs[key] = exchange_child

            #  创建数据节点
            item = QtWidgets.QTreeWidgetItem(exchange_child)

            item.setText(1, f"{overview.symbol}.{overview.exchange.value}")
            item.setText(2, overview.symbol)
            item.setText(3, overview.exchange.value)
            item.setText(4, str(overview.count))
            item.setText(5, overview.start.strftime("%Y-%m-%d %H:%M:%S"))
            item.setText(6, overview.end.strftime("%Y-%m-%d %H:%M:%S"))

            output_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导出")
            output_func = partial(
                self.output_data,
                overview.symbol,
                overview.exchange,
                interval,
                overview.start,
                overview.end
            )
            output_button.clicked.connect(output_func)

            show_button: QtWidgets.QPushButton = QtWidgets.QPushButton("查看")
            show_func = partial(
                self.show_data,
                overview.symbol,
                overview.exchange,
                interval,
                overview.start,
                overview.end
            )
            show_button.clicked.connect(show_func)

            delete_button: QtWidgets.QPushButton = QtWidgets.QPushButton("删除")
            delete_func = partial(
                self.delete_data,
                overview.symbol,
                overview.exchange,
                interval
            )
            delete_button.clicked.connect(delete_func)

            self.tree.setItemWidget(item, 7, show_button)
            self.tree.setItemWidget(item, 8, output_button)
            self.tree.setItemWidget(item, 9, delete_button)

        # 展开顶层节点
        self.tree.addTopLevelItems(list(interval_childs.values()))

        # 展开所有节点（包括周期节点、交易所节点）
        for interval_child in interval_childs.values():
            interval_child.setExpanded(True)
            # 展开交易所节点
            for i in range(interval_child.childCount()):
                exchange_child = interval_child.child(i)
                if exchange_child:
                    exchange_child.setExpanded(True)

    def import_data(self) -> None:
        """"""
        dialog: ImportDialog = ImportDialog()
        n: int = dialog.exec_()
        if n != dialog.DialogCode.Accepted:
            return

        file_path: str = dialog.file_edit.text()
        symbol: str = dialog.symbol_edit.text()
        exchange = dialog.exchange_combo.currentData()
        interval = dialog.interval_combo.currentData()
        tz_name: str = dialog.tz_combo.currentText()
        datetime_head: str = dialog.datetime_edit.text()
        open_head: str = dialog.open_edit.text()
        low_head: str = dialog.low_edit.text()
        high_head: str = dialog.high_edit.text()
        close_head: str = dialog.close_edit.text()
        volume_head: str = dialog.volume_edit.text()
        turnover_head: str = dialog.turnover_edit.text()
        open_interest_head: str = dialog.open_interest_edit.text()
        datetime_format: str = dialog.format_edit.text()

        start, end, count = self.engine.import_data_from_csv(
            file_path,
            symbol,
            exchange,
            interval,
            tz_name,
            datetime_head,
            open_head,
            high_head,
            low_head,
            close_head,
            volume_head,
            turnover_head,
            open_interest_head,
            datetime_format
        )

        msg: str = f"\
        CSV载入成功\n\
        代码：{symbol}\n\
        交易所：{exchange.value}\n\
        周期：{interval.value}\n\
        起始：{start}\n\
        结束：{end}\n\
        总数量：{count}\n\
        "
        QtWidgets.QMessageBox.information(self, "载入成功！", msg)

    def output_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> None:
        """"""
        # Get output date range
        dialog: DateRangeDialog = DateRangeDialog(start, end)
        n: int = dialog.exec_()
        if n != dialog.DialogCode.Accepted:
            return
        start, end = dialog.get_date_range()

        # Get output file path
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出数据",
            "",
            "CSV(*.csv)"
        )
        if not path:
            return

        result: bool = self.engine.output_data_to_csv(
            path,
            symbol,
            exchange,
            interval,
            start,
            end
        )

        if not result:
            QtWidgets.QMessageBox.warning(
                self,
                "导出失败！",
                "该文件已在其他程序中打开，请关闭相关程序后再尝试导出数据。"
            )

    def show_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> None:
        """"""
        # Get output date range
        dialog: DateRangeDialog = DateRangeDialog(start, end)
        n: int = dialog.exec_()
        if n != dialog.DialogCode.Accepted:
            return
        start, end = dialog.get_date_range()

        bars: list[BarData] = self.engine.load_bar_data(
            symbol,
            exchange,
            interval,
            start,
            end
        )

        self.table.setRowCount(0)
        self.table.setRowCount(len(bars))

        for row, bar in enumerate(bars):
            self.table.setItem(row, 0, DataCell(bar.datetime.strftime("%Y-%m-%d %H:%M:%S")))
            self.table.setItem(row, 1, DataCell(str(bar.open_price)))
            self.table.setItem(row, 2, DataCell(str(bar.high_price)))
            self.table.setItem(row, 3, DataCell(str(bar.low_price)))
            self.table.setItem(row, 4, DataCell(str(bar.close_price)))
            self.table.setItem(row, 5, DataCell(str(bar.volume)))
            self.table.setItem(row, 6, DataCell(str(bar.turnover)))
            self.table.setItem(row, 7, DataCell(str(bar.open_interest)))

    def delete_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> None:
        """"""
        n = QtWidgets.QMessageBox.warning(
            self,
            "删除确认",
            f"请确认是否要删除{symbol} {exchange.value} {interval.value}的全部数据",
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Cancel
        )

        if n == QtWidgets.QMessageBox.Cancel:
            return

        count: int = self.engine.delete_bar_data(
            symbol,
            exchange,
            interval
        )

        QtWidgets.QMessageBox.information(
            self,
            "删除成功",
            f"已删除{symbol} {exchange.value} {interval.value}共计{count}条数据",
            QtWidgets.QMessageBox.Ok
        )

    def update_data(self) -> None:
        """"""
        self.engine.main_engine.write_log("[数据更新] 开始执行数据更新任务...")

        overviews: list[BarOverview] = self.engine.get_bar_overview()
        total: int = len(overviews)
        count: int = 0
        total_bars: int = 0  # 累计下载的K线数量

        if total == 0:
            QtWidgets.QMessageBox.information(
                self,
                "更新数据",
                "没有找到需要更新的合约数据"
            )
            return

        self.engine.main_engine.write_log(f"[数据更新] 发现 {total} 个合约需要更新")

        # 创建统一的进度对话框
        dialog: UpdateProgressDialog = UpdateProgressDialog(self)
        dialog.set_total_tasks(total)
        dialog.show()
        QtWidgets.QApplication.processEvents()  # 处理事件，确保对话框显示
        
        # 创建自定义的output回调，将消息追加到进度对话框
        def output_callback(msg: str) -> None:
            """将消息追加到进度对话框，而不是弹出新弹窗"""
            dialog.append_message(msg)
            QtWidgets.QApplication.processEvents()

        # 收集需要合成4小时数据的合约（有1小时或1分钟数据但没有4小时数据的）
        symbols_to_aggregate: set[tuple[str, Exchange]] = set()
        
        for overview in overviews:
            # 更新进度
            dialog.update_progress(count, total, f"{overview.symbol}.{overview.exchange.value}")
            dialog.append_message(f"开始更新: {overview.symbol}.{overview.exchange.value} ({overview.interval.value})")
            QtWidgets.QApplication.processEvents()

            bar_count = self.engine.download_bar_data(
                overview.symbol,
                overview.exchange,
                overview.interval,
                overview.end,
                output_callback
            )
            total_bars += bar_count  # 累加每次下载的数据量
            count += 1
            dialog.append_message(f"完成: {overview.symbol}.{overview.exchange.value}，本次下载 {bar_count} 条")
            dialog.update_progress(count, total)
            QtWidgets.QApplication.processEvents()
            
            self.engine.main_engine.write_log(
                f"[数据更新] 合约 {count}/{total}: {overview.symbol}.{overview.exchange.value} 更新完成，下载 {bar_count} 条数据"
            )
            
            # 如果是有1分钟数据的合约，标记为需要合成5分钟和4小时数据
            if overview.interval == Interval.MINUTE:
                symbols_to_aggregate.add((overview.symbol, overview.exchange))
            
            # 如果是有1小时数据的合约，标记为需要合成4小时数据
            if overview.interval == Interval.HOUR:
                symbols_to_aggregate.add((overview.symbol, overview.exchange))

        # 自动合成5分钟数据（从1分钟数据）
        symbols_5m: set[tuple[str, Exchange]] = set()
        for overview in overviews:
            if overview.interval == Interval.MINUTE:
                symbols_5m.add((overview.symbol, overview.exchange))
        
        if symbols_5m:
            dialog.append_message(f"开始为 {len(symbols_5m)} 个合约合成5分钟数据...")
            QtWidgets.QApplication.processEvents()
            self.engine.main_engine.write_log(
                f"[数据更新] 开始为 {len(symbols_5m)} 个合约合成5分钟K线数据..."
            )
            
            aggregate_5m_count = 0
            for symbol, exchange in symbols_5m:
                dialog.append_message(f"正在合成5分钟数据: {symbol}.{exchange.value}")
                QtWidgets.QApplication.processEvents()
                
                try:
                    count_5m = self.engine.aggregate_5minute_bars(symbol, exchange)
                    if count_5m > 0:
                        aggregate_5m_count += count_5m
                        self.engine.main_engine.write_log(
                            f"[数据更新] {symbol}.{exchange.value} 合成5分钟K线数据: {count_5m} 条"
                        )
                except Exception as e:
                    self.engine.main_engine.write_log(
                        f"[数据更新] 合成5分钟数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                    )
                    import traceback
                    self.engine.main_engine.write_log(f"[数据更新] 错误详情:\n{traceback.format_exc()}")
            
            if aggregate_5m_count > 0:
                total_bars += aggregate_5m_count
                self.engine.main_engine.write_log(
                    f"[数据更新] 5分钟K线数据合成完成，共 {aggregate_5m_count} 条"
                )

        # 自动合成1小时数据（从1分钟数据）
        if symbols_5m:  # 使用相同的合约集合（有1分钟数据的合约）
            dialog.append_message(f"开始为 {len(symbols_5m)} 个合约合成1小时数据...")
            QtWidgets.QApplication.processEvents()
            self.engine.main_engine.write_log(
                f"[数据更新] 开始为 {len(symbols_5m)} 个合约合成1小时K线数据..."
            )
            
            aggregate_1h_count = 0
            for symbol, exchange in symbols_5m:
                dialog.append_message(f"正在合成1小时数据: {symbol}.{exchange.value}")
                QtWidgets.QApplication.processEvents()
                
                try:
                    count_1h = self.engine.aggregate_hour_bars(symbol, exchange)
                    if count_1h > 0:
                        aggregate_1h_count += count_1h
                        self.engine.main_engine.write_log(
                            f"[数据更新] {symbol}.{exchange.value} 合成1小时K线数据: {count_1h} 条"
                        )
                except Exception as e:
                    self.engine.main_engine.write_log(
                        f"[数据更新] 合成1小时数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                    )
                    import traceback
                    self.engine.main_engine.write_log(f"[数据更新] 错误详情:\n{traceback.format_exc()}")
            
            if aggregate_1h_count > 0:
                total_bars += aggregate_1h_count
                self.engine.main_engine.write_log(
                    f"[数据更新] 1小时K线数据合成完成，共 {aggregate_1h_count} 条"
                )

        # 自动合成4小时数据
        if symbols_to_aggregate:
            dialog.append_message(f"开始为 {len(symbols_to_aggregate)} 个合约合成4小时数据...")
            QtWidgets.QApplication.processEvents()
            self.engine.main_engine.write_log(
                f"[数据更新] 开始为 {len(symbols_to_aggregate)} 个合约合成4小时K线数据..."
            )
            
            aggregate_count = 0
            for symbol, exchange in symbols_to_aggregate:
                dialog.append_message(f"正在合成4小时数据: {symbol}.{exchange.value}")
                QtWidgets.QApplication.processEvents()
                
                try:
                    count_4h = self.engine.aggregate_4hour_bars(symbol, exchange)
                    if count_4h > 0:
                        aggregate_count += count_4h
                        self.engine.main_engine.write_log(
                            f"[数据更新] {symbol}.{exchange.value} 合成4小时K线数据: {count_4h} 条"
                        )
                except Exception as e:
                    self.engine.main_engine.write_log(
                        f"[数据更新] 合成4小时数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                    )
                    import traceback
                    self.engine.main_engine.write_log(f"[数据更新] 错误详情:\n{traceback.format_exc()}")
            
            if aggregate_count > 0:
                total_bars += aggregate_count
                self.engine.main_engine.write_log(
                    f"[数据更新] 4小时K线数据合成完成，共 {aggregate_count} 条"
                )

        # 更新对话框为完成状态
        dialog.set_completed(total_bars, count, total)
        
        # 输出完成日志
        self.engine.main_engine.write_log(
            f"[数据更新] 数据更新任务完成！共处理 {count}/{total} 个合约，总数据量: {total_bars:,} 条"
        )
        
        # 等待用户关闭对话框
        dialog.exec_()

    def download_data(self) -> None:
        """"""
        dialog: DownloadDialog = DownloadDialog(self.engine, self)
        dialog.exec_()

    def show(self) -> None:
        """"""
        self.showMaximized()
    
    def closeEvent(self, event) -> None:
        """窗口关闭时停止自动更新"""
        self.stop_auto_update()
        event.accept()

    def output(self, msg: str) -> None:
        """输出下载过程中的日志（保留兼容性，但不再弹出弹窗）"""
        # 不再弹出弹窗，只打印日志
        print(f"[数据下载] {msg}")
    
    def on_auto_update_changed(self, state: int) -> None:
        """自动更新复选框状态改变"""
        self.auto_update_enabled = (state == QtCore.Qt.CheckState.Checked.value)
        self.auto_update_interval_spin.setEnabled(self.auto_update_enabled)
        self.next_update_label.setEnabled(self.auto_update_enabled)
        
        # 更新复选框文本和样式
        if self.auto_update_enabled:
            self.auto_update_checkbox.setText("启用 ✓")
            self.auto_update_checkbox.setStyleSheet("QCheckBox { color: #00ff00; font-weight: bold; }")
            self.start_auto_update()
        else:
            self.auto_update_checkbox.setText("启用")
            self.auto_update_checkbox.setStyleSheet("")
            self.stop_auto_update()
    
    def on_auto_update_interval_changed(self, value: int) -> None:
        """自动更新间隔改变"""
        old_interval = self.auto_update_interval
        self.auto_update_interval = value
        if self.auto_update_enabled:
            # 重新启动定时器（静默停止，只输出重启日志）
            if self.auto_update_timer is not None:
                self.auto_update_timer.stop()
            self._restart_auto_update_timer(silent=True)
    
    def start_auto_update(self) -> None:
        """启动自动更新定时器"""
        self._restart_auto_update_timer(silent=False)
    
    def _restart_auto_update_timer(self, silent: bool = False) -> None:
        """重启自动更新定时器（内部方法）"""
        if self.auto_update_timer is None:
            self.auto_update_timer = QtCore.QTimer()
            self.auto_update_timer.timeout.connect(self.auto_update_data)
        
        # 设置定时器间隔（毫秒）
        interval_ms = self.auto_update_interval * 60 * 1000
        self.auto_update_timer.start(interval_ms)
        
        # 更新下次更新时间显示
        self.update_next_update_time()
        
        # 输出日志
        if not silent:
            self.engine.main_engine.write_log(
                f"[自动更新] 已启动，更新间隔: {self.auto_update_interval} 分钟"
            )
        else:
            self.engine.main_engine.write_log(
                f"[自动更新] 已更新间隔设置: {self.auto_update_interval} 分钟"
            )
    
    def stop_auto_update(self) -> None:
        """停止自动更新定时器"""
        if self.auto_update_timer is not None:
            self.auto_update_timer.stop()
        self.next_update_label.setText("")
        self.engine.main_engine.write_log("[自动更新] 已停止")
    
    def update_next_update_time(self) -> None:
        """更新下次更新时间显示"""
        if self.auto_update_enabled and self.auto_update_timer is not None:
            next_update = datetime.now() + timedelta(minutes=self.auto_update_interval)
            next_update_str = next_update.strftime("%H:%M")
            self.next_update_label.setText(f"下次更新: {next_update_str}")
            self.next_update_label.setStyleSheet("color: #00aa00; font-size: 10px; padding: 2px 5px; font-weight: bold;")
        else:
            self.next_update_label.setText("")
            self.next_update_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 5px;")
    
    def auto_update_data(self) -> None:
        """自动更新数据（异步执行）"""
        if self.is_updating:
            self.engine.main_engine.write_log("[自动更新] 上次更新尚未完成，跳过本次更新")
            return
        
        self.engine.main_engine.write_log("[自动更新] 开始执行自动更新任务...")
        self.is_updating = True
        
        # 使用QTimer.singleShot在后台线程执行更新，避免阻塞UI
        QtCore.QTimer.singleShot(0, self._execute_auto_update)
    
    def _execute_auto_update(self) -> None:
        """执行自动更新（在后台线程中）"""
        try:
            # 调用更新数据方法，但不显示进度对话框（静默更新）
            overviews: list[BarOverview] = self.engine.get_bar_overview()
            total: int = len(overviews)
            
            if total == 0:
                self.engine.main_engine.write_log("[自动更新] 未找到需要更新的合约数据")
                return
            
            self.engine.main_engine.write_log(f"[自动更新] 发现 {total} 个合约需要更新，开始处理...")
            
            total_bars: int = 0
            count: int = 0
            
            # 静默更新：不显示进度对话框，只输出日志
            def silent_output(msg: str) -> None:
                """静默输出，只输出到日志"""
                # 过滤掉一些冗余信息，只保留关键信息
                if any(keyword in msg for keyword in ["开始", "完成", "失败", "错误"]):
                    self.engine.main_engine.write_log(f"[自动更新] {msg}")
            
            # 更新每个合约的数据
            for overview in overviews:
                self.engine.main_engine.write_log(
                    f"[自动更新] 正在更新合约: {overview.symbol}.{overview.exchange.value} ({overview.interval.value})"
                )
                
                bar_count = self.engine.download_bar_data(
                    overview.symbol,
                    overview.exchange,
                    overview.interval,
                    overview.end,
                    silent_output
                )
                total_bars += bar_count
                count += 1
                self.engine.main_engine.write_log(
                    f"[自动更新] 合约 {count}/{total}: {overview.symbol}.{overview.exchange.value} 更新完成，下载 {bar_count} 条数据"
                )
            
            # 自动合成数据（静默执行）
            symbols_5m: set[tuple[str, Exchange]] = set()
            for overview in overviews:
                if overview.interval == Interval.MINUTE:
                    symbols_5m.add((overview.symbol, overview.exchange))
            
            # 合成5分钟数据
            if symbols_5m:
                self.engine.main_engine.write_log(
                    f"[自动更新] 开始为 {len(symbols_5m)} 个合约合成5分钟K线数据..."
                )
                aggregate_5m_count = 0
                for symbol, exchange in symbols_5m:
                    try:
                        count_5m = self.engine.aggregate_5minute_bars(symbol, exchange)
                        if count_5m > 0:
                            total_bars += count_5m
                            aggregate_5m_count += count_5m
                    except Exception as e:
                        self.engine.main_engine.write_log(
                            f"[自动更新] 合成5分钟数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                        )
                if aggregate_5m_count > 0:
                    self.engine.main_engine.write_log(
                        f"[自动更新] 5分钟K线数据合成完成，共 {aggregate_5m_count} 条"
                    )
            
            # 合成1小时数据
            if symbols_5m:
                self.engine.main_engine.write_log(
                    f"[自动更新] 开始为 {len(symbols_5m)} 个合约合成1小时K线数据..."
                )
                aggregate_1h_count = 0
                for symbol, exchange in symbols_5m:
                    try:
                        count_1h = self.engine.aggregate_hour_bars(symbol, exchange)
                        if count_1h > 0:
                            total_bars += count_1h
                            aggregate_1h_count += count_1h
                    except Exception as e:
                        self.engine.main_engine.write_log(
                            f"[自动更新] 合成1小时数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                        )
                if aggregate_1h_count > 0:
                    self.engine.main_engine.write_log(
                        f"[自动更新] 1小时K线数据合成完成，共 {aggregate_1h_count} 条"
                    )
            
            # 合成4小时数据
            symbols_to_aggregate: set[tuple[str, Exchange]] = set()
            for overview in overviews:
                if overview.interval == Interval.MINUTE:
                    symbols_to_aggregate.add((overview.symbol, overview.exchange))
                if overview.interval == Interval.HOUR:
                    symbols_to_aggregate.add((overview.symbol, overview.exchange))
            
            if symbols_to_aggregate:
                self.engine.main_engine.write_log(
                    f"[自动更新] 开始为 {len(symbols_to_aggregate)} 个合约合成4小时K线数据..."
                )
                aggregate_4h_count = 0
                for symbol, exchange in symbols_to_aggregate:
                    try:
                        count_4h = self.engine.aggregate_4hour_bars(symbol, exchange)
                        if count_4h > 0:
                            total_bars += count_4h
                            aggregate_4h_count += count_4h
                    except Exception as e:
                        self.engine.main_engine.write_log(
                            f"[自动更新] 合成4小时数据失败: {symbol}.{exchange.value}, 错误: {str(e)}"
                        )
                if aggregate_4h_count > 0:
                    self.engine.main_engine.write_log(
                        f"[自动更新] 4小时K线数据合成完成，共 {aggregate_4h_count} 条"
                    )
            
            # 输出完成总结
            self.engine.main_engine.write_log(
                f"[自动更新] 自动更新任务完成！共处理 {count}/{total} 个合约，总数据量: {total_bars:,} 条"
            )
            
        except Exception as e:
            self.engine.main_engine.write_log(
                f"[自动更新] 更新过程中发生错误: {str(e)}"
            )
            import traceback
            self.engine.main_engine.write_log(f"[自动更新] 错误详情:\n{traceback.format_exc()}")
        finally:
            self.is_updating = False
            # 更新下次更新时间
            self.update_next_update_time()
            self.engine.main_engine.write_log(
                f"[自动更新] 下次自动更新将在 {self.auto_update_interval} 分钟后执行"
            )


class UpdateProgressDialog(QtWidgets.QDialog):
    """统一的更新进度对话框，显示所有更新信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更新进度")
        self.setFixedSize(600, 500)
        self.setWindowModality(QtCore.Qt.WindowModal)
        
        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        # 当前任务标签
        self.current_task_label = QtWidgets.QLabel("准备更新...")
        self.current_task_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        # 消息列表（显示所有更新信息）
        self.message_list = QtWidgets.QTextEdit()
        self.message_list.setReadOnly(True)
        self.message_list.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 10px;")
        
        # 统计信息标签
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        
        # 关闭按钮（初始禁用）
        self.close_button = QtWidgets.QPushButton("关闭")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        
        # 布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.current_task_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QtWidgets.QLabel("更新信息:"))
        layout.addWidget(self.message_list)
        layout.addWidget(self.stats_label)
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.total_tasks = 0
        self.completed_tasks = 0
        self.total_bars = 0
    
    def set_total_tasks(self, total: int):
        """设置总任务数"""
        self.total_tasks = total
        self.append_message(f"找到 {total} 个合约需要更新")
    
    def update_progress(self, current: int, total: int, task_name: str = ""):
        """更新进度"""
        self.completed_tasks = current
        progress = int(round(current / total * 100, 0)) if total > 0 else 0
        self.progress_bar.setValue(progress)
        
        if task_name:
            self.current_task_label.setText(f"正在处理: {task_name} ({current}/{total})")
    
    def append_message(self, msg: str):
        """追加消息到消息列表"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_list.append(f"[{timestamp}] {msg}")
        # 自动滚动到底部
        scrollbar = self.message_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def set_completed(self, total_bars: int, completed: int, total: int):
        """设置为完成状态"""
        self.total_bars = total_bars
        self.completed_tasks = completed
        self.progress_bar.setValue(100)
        self.current_task_label.setText("更新完成！")
        self.stats_label.setText(f"共完成 {completed}/{total} 个合约，总数据量: {total_bars:,} 条")
        self.append_message(f"更新完成！共处理 {completed}/{total} 个合约，总数据量: {total_bars:,} 条")
        self.close_button.setEnabled(True)
        self.close_button.setFocus()


class DataCell(QtWidgets.QTableWidgetItem):
    """"""

    def __init__(self, text: str = "") -> None:
        super().__init__(text)

        self.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class DateRangeDialog(QtWidgets.QDialog):
    """"""

    def __init__(self, start: datetime, end: datetime, parent: QtWidgets.QWidget | None = None) -> None:
        """"""
        super().__init__(parent)

        self.setWindowTitle("选择数据区间")

        self.start_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                start.year,
                start.month,
                start.day + 1
            )
        )
        self.end_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                end.year,
                end.month,
                end.day + 1
            )
        )

        button: QtWidgets.QPushButton = QtWidgets.QPushButton("确定")
        button.clicked.connect(self.accept)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("开始时间", self.start_edit)
        form.addRow("结束时间", self.end_edit)
        form.addRow(button)

        self.setLayout(form)

    def get_date_range(self) -> tuple[datetime, datetime]:
        """"""
        start = self.start_edit.dateTime().toPython()
        end = self.end_edit.dateTime().toPython() + timedelta(days=1)
        return start, end


class ImportDialog(QtWidgets.QDialog):
    """"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """"""
        super().__init__()

        self.setWindowTitle("从CSV文件导入数据")
        self.setFixedWidth(300)

        self.setWindowFlags(
            (self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
            & ~QtCore.Qt.WindowMaximizeButtonHint)

        file_button: QtWidgets.QPushButton = QtWidgets.QPushButton("选择文件")
        file_button.clicked.connect(self.select_file)

        load_button: QtWidgets.QPushButton = QtWidgets.QPushButton("确定")
        load_button.clicked.connect(self.accept)

        self.file_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.symbol_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.exchange_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Exchange:
            self.exchange_combo.addItem(str(i.name), i)

        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Interval:
            if i != Interval.TICK:
                self.interval_combo.addItem(str(i.name), i)

        self.tz_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.tz_combo.addItems(available_timezones())
        self.tz_combo.setCurrentIndex(self.tz_combo.findText("Asia/Shanghai"))

        self.datetime_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("datetime")
        self.open_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("open")
        self.high_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("high")
        self.low_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("low")
        self.close_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("close")
        self.volume_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("volume")
        self.turnover_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("turnover")
        self.open_interest_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("open_interest")

        self.format_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit("%Y-%m-%d %H:%M:%S")

        info_label: QtWidgets.QLabel = QtWidgets.QLabel("合约信息")
        info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        head_label: QtWidgets.QLabel = QtWidgets.QLabel("表头信息")
        head_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        format_label: QtWidgets.QLabel = QtWidgets.QLabel("格式信息")
        format_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow(file_button, self.file_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(info_label)
        form.addRow("代码", self.symbol_edit)
        form.addRow("交易所", self.exchange_combo)
        form.addRow("周期", self.interval_combo)
        form.addRow("时区", self.tz_combo)
        form.addRow(QtWidgets.QLabel())
        form.addRow(head_label)
        form.addRow("时间戳", self.datetime_edit)
        form.addRow("开盘价", self.open_edit)
        form.addRow("最高价", self.high_edit)
        form.addRow("最低价", self.low_edit)
        form.addRow("收盘价", self.close_edit)
        form.addRow("成交量", self.volume_edit)
        form.addRow("成交额", self.turnover_edit)
        form.addRow("持仓量", self.open_interest_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(format_label)
        form.addRow("时间格式", self.format_edit)
        form.addRow(QtWidgets.QLabel())
        form.addRow(load_button)

        self.setLayout(form)

    def select_file(self) -> None:
        """"""
        result: str = QtWidgets.QFileDialog.getOpenFileName(
            self, filter="CSV (*.csv)")
        filename: str = result[0]
        if filename:
            self.file_edit.setText(filename)


class DownloadWorker(QtCore.QThread):
    """下载数据的工作线程"""
    
    # 信号定义
    progress_updated = QtCore.Signal(str, int, int)  # 阶段描述, 当前值, 最大值
    download_finished = QtCore.Signal(int, str)  # 下载数量, 结果消息
    error_occurred = QtCore.Signal(str)  # 错误消息
    
    def __init__(
        self,
        engine,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start_dt: datetime,
        parent=None
    ):
        super().__init__(parent)
        self.engine = engine
        self.symbol = symbol
        self.exchange = exchange
        self.interval = interval
        self.start_dt = start_dt  # 避免与 QThread.start() 方法冲突
        self._is_cancelled = False
    
    def cancel(self):
        """取消下载"""
        self._is_cancelled = True
    
    def run(self):
        """执行下载任务"""
        try:
            if self.interval == Interval.TICK:
                count = self.engine.download_tick_data(
                    self.symbol, self.exchange, self.start_dt, self.output_callback
                )
                self.download_finished.emit(count, "tick")
            else:
                count = self.engine.download_bar_data(
                    self.symbol, self.exchange, self.interval, self.start_dt, self.output_callback
                )
                if self.interval == Interval.MINUTE_5:
                    self.download_finished.emit(count, "5min")
                elif self.interval == Interval.HOUR:
                    self.download_finished.emit(count, "hour")
                elif self.interval == Interval.HOUR_4:
                    self.download_finished.emit(count, "4hour")
                else:
                    self.download_finished.emit(count, "bar")
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def output_callback(self, msg: str):
        """处理下载过程中的输出消息"""
        import re
        
        # 解析进度信息
        if "第" in msg and "页获取成功" in msg:
            # 解析页码和数据量（富途分页下载）
            try:
                match = re.search(r"累计 (\d+) 条", msg)
                if match:
                    current = int(match.group(1))
                    self.progress_updated.emit(f"正在下载K线数据...", current, 0)
            except:
                pass
        elif "K线数据获取完成" in msg or "数据获取完成" in msg:
            try:
                match = re.search(r"共 (\d+) 条", msg)
                if match:
                    total = int(match.group(1))
                    self.progress_updated.emit(f"K线数据获取完成，共 {total:,} 条", total, total)
            except:
                self.progress_updated.emit(msg, 0, 0)
        elif "正在转换为BarData" in msg or "正在转换" in msg:
            self.progress_updated.emit("正在转换数据格式...", 0, 0)
        elif "开始保存" in msg:
            try:
                match = re.search(r"保存 (\d+) 条", msg)
                if match:
                    total = int(match.group(1))
                    self.progress_updated.emit(f"正在保存 {total:,} 条数据到数据库...", 0, 0)
            except:
                self.progress_updated.emit("正在保存数据到数据库...", 0, 0)
        elif "数据保存完成" in msg:
            try:
                match = re.search(r"共 (\d+) 条", msg)
                if match:
                    total = int(match.group(1))
                    self.progress_updated.emit(f"数据保存完成！共 {total:,} 条", total, total)
                else:
                    self.progress_updated.emit("数据保存完成！", 100, 100)
            except:
                self.progress_updated.emit("数据保存完成！", 100, 100)
        elif "正在从网关" in msg or "正在从数据源" in msg:
            self.progress_updated.emit(msg, 0, 0)
        elif "开始合成" in msg:
            self.progress_updated.emit(msg, 0, 0)
        elif "合成完成" in msg:
            try:
                match = re.search(r"共 (\d+) 条", msg)
                if match:
                    total = int(match.group(1))
                    self.progress_updated.emit(f"合成完成，共 {total:,} 条K线", total, total)
                else:
                    self.progress_updated.emit(msg, 100, 100)
            except:
                self.progress_updated.emit(msg, 100, 100)
        elif "没有查询到数据" in msg:
            self.progress_updated.emit("没有查询到数据", 0, 0)
        else:
            # 其他消息直接显示
            self.progress_updated.emit(msg, 0, 0)


class DownloadProgressDialog(QtWidgets.QDialog):
    """统一的下载进度对话框，显示所有下载信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载进度")
        self.setFixedSize(600, 500)
        self.setWindowModality(QtCore.Qt.WindowModal)
        
        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        # 当前任务标签
        self.current_task_label = QtWidgets.QLabel("准备下载...")
        self.current_task_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        # 消息列表（显示所有下载信息）
        self.message_list = QtWidgets.QTextEdit()
        self.message_list.setReadOnly(True)
        self.message_list.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 10px;")
        
        # 统计信息标签
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        
        # 关闭按钮（初始禁用）
        self.close_button = QtWidgets.QPushButton("关闭")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        
        # 布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.current_task_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QtWidgets.QLabel("下载信息:"))
        layout.addWidget(self.message_list)
        layout.addWidget(self.stats_label)
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.total_data = 0
        self.current_data = 0
    
    def append_message(self, msg: str):
        """追加消息到消息列表"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_list.append(f"[{timestamp}] {msg}")
        # 自动滚动到底部
        scrollbar = self.message_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_progress(self, stage: str, current: int, maximum: int):
        """更新进度"""
        self.current_task_label.setText(stage)
        
        if maximum > 0:
            self.progress_bar.setRange(0, maximum)
            self.progress_bar.setValue(current)
            self.progress_bar.setFormat(f"%v / {maximum:,} 条")
            progress = int(round(current / maximum * 100, 0)) if maximum > 0 else 0
            self.stats_label.setText(f"已下载: {current:,} / {maximum:,} 条 ({progress}%)")
        else:
            if current > 0:
                self.progress_bar.setRange(0, 0)  # 不确定模式
                self.progress_bar.setFormat("下载中...")
                self.stats_label.setText(f"已获取 {current:,} 条数据")
            else:
                self.progress_bar.setRange(0, 0)
                self.progress_bar.setFormat("准备中...")
                self.stats_label.setText("")
        
        # 追加消息到消息列表
        if stage:
            self.append_message(stage)
    
    def set_completed(self, total: int):
        """设置为完成状态"""
        self.total_data = total
        self.current_data = total
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("完成")
        self.current_task_label.setText("下载完成！")
        self.stats_label.setText(f"共下载 {total:,} 条数据")
        self.append_message(f"下载完成！共 {total:,} 条数据")
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
    
    def set_error(self, error_msg: str):
        """设置为错误状态"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("失败")
        self.current_task_label.setText("下载失败")
        self.stats_label.setText("")
        self.stats_label.setStyleSheet("color: red; font-size: 11px;")
        self.append_message(f"下载失败: {error_msg}")
        self.close_button.setEnabled(True)
        self.close_button.setFocus()
    
    def enable_return(self):
        """启用返回按钮（下载完成后调用，保持兼容性）"""
        self.close_button.setEnabled(True)
        self.close_button.setFocus()


class DownloadDialog(QtWidgets.QDialog):
    """"""

    def __init__(self, engine: ManagerEngine, parent: QtWidgets.QWidget | None = None) -> None:
        """"""
        super().__init__(parent)

        self.engine: ManagerEngine = engine
        self.parent_widget: QtWidgets.QWidget | None = parent  # 保存父窗口引用
        self.worker: DownloadWorker | None = None
        self.progress_dialog: DownloadProgressDialog | None = None

        self.setWindowTitle("下载历史数据")
        self.setFixedWidth(300)

        self.symbol_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.exchange_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Exchange:
            self.exchange_combo.addItem(str(i.name), i)

        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for i in Interval:
            item_text = str(i.name)
            # 如果是5分钟、1小时或4小时，添加提示说明需要从已有数据合成
            if i == Interval.MINUTE_5:
                item_text += " (需从1分钟数据合成)"
            elif i == Interval.HOUR:
                item_text += " (需从1分钟数据合成)"
            elif i == Interval.HOUR_4:
                item_text += " (需从已有数据合成)"
            self.interval_combo.addItem(item_text, i)

        end_dt: datetime = datetime.now()
        start_dt: datetime = end_dt - timedelta(days=3 * 365)

        self.start_date_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                start_dt.year,
                start_dt.month,
                start_dt.day
            )
        )

        button: QtWidgets.QPushButton = QtWidgets.QPushButton("下载")
        button.clicked.connect(self.download)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("代码", self.symbol_edit)
        form.addRow("交易所", self.exchange_combo)
        form.addRow("周期", self.interval_combo)
        form.addRow("开始日期", self.start_date_edit)
        form.addRow(button)

        self.setLayout(form)

    def download(self) -> None:
        """"""
        symbol: str = self.symbol_edit.text()
        if not symbol:
            QtWidgets.QMessageBox.warning(self, "提示", "请输入合约代码")
            return
            
        exchange: Exchange = Exchange(self.exchange_combo.currentData())
        interval: Interval = Interval(self.interval_combo.currentData())

        start_date = self.start_date_edit.date()
        start: datetime = datetime(start_date.year(), start_date.month(), start_date.day())
        start = start.replace(tzinfo=DB_TZ)

        # 如果是5分钟、1小时或4小时数据，提示用户这是从已有数据合成
        if interval == Interval.MINUTE_5:
            reply = QtWidgets.QMessageBox.question(
                self,
                "5分钟数据合成",
                "5分钟数据将从已有的1分钟数据合成，而不是从数据源下载。\n\n是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return
        elif interval == Interval.HOUR:
            reply = QtWidgets.QMessageBox.question(
                self,
                "1小时数据合成",
                "1小时数据将从已有的1分钟数据合成，而不是从数据源下载。\n\n是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return
        elif interval == Interval.HOUR_4:
            reply = QtWidgets.QMessageBox.question(
                self,
                "4小时数据合成",
                "4小时数据将从已有的1分钟数据合成，而不是从数据源下载。\n\n是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # 保存父窗口引用（在关闭窗口前）
        parent_widget = self.parent_widget
        
        # 关闭下载数据窗口
        self.accept()
        
        # 创建进度对话框（使用父窗口）
        self.progress_dialog = DownloadProgressDialog(parent_widget)
        self.progress_dialog.append_message(f"开始下载: {symbol}.{exchange.value} ({interval.value})")
        
        # 创建工作线程
        self.worker = DownloadWorker(
            self.engine, symbol, exchange, interval, start, self
        )
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.download_finished.connect(self.on_download_finished)
        self.worker.error_occurred.connect(self.on_error_occurred)
        
        # 启动下载
        self.worker.start()
        
        # 显示进度对话框（阻塞等待）
        self.progress_dialog.exec_()
    
    def on_progress_updated(self, stage: str, current: int, maximum: int):
        """进度更新回调"""
        if self.progress_dialog:
            self.progress_dialog.update_progress(stage, current, maximum)
    
    def on_download_finished(self, count: int, result_type: str):
        """下载完成回调"""
        if self.progress_dialog:
            # 根据类型追加完成消息
            if result_type == "5min":
                self.progress_dialog.append_message(f"合成完成！共 {count:,} 条5分钟K线")
            elif result_type == "hour":
                self.progress_dialog.append_message(f"合成完成！共 {count:,} 条1小时K线")
            elif result_type == "4hour":
                self.progress_dialog.append_message(f"合成完成！共 {count:,} 条4小时K线")
            elif result_type == "tick":
                self.progress_dialog.append_message(f"下载完成！共 {count:,} 条Tick数据")
            else:
                self.progress_dialog.append_message(f"下载完成！共 {count:,} 条K线数据")
            
            # 更新进度对话框为完成状态
            self.progress_dialog.set_completed(count)
    
    def on_error_occurred(self, error_msg: str):
        """错误处理回调"""
        if self.progress_dialog:
            self.progress_dialog.set_error(error_msg)

    def output(self, msg: str) -> None:
        """输出下载过程中的日志（保留兼容性）"""
        print(f"[下载日志] {msg}")
