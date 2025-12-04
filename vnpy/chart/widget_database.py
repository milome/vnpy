"""ChartWidget 数据库模块 Mixin

处理价格线的保存和加载功能。
"""

from typing import TYPE_CHECKING

from .widget_mixin_base import ChartWidgetMixinBase

if TYPE_CHECKING:
    pass


class ChartWidgetDatabaseMixin(ChartWidgetMixinBase):
    """数据库操作相关功能 Mixin"""
    
    def _load_line_relations(self) -> None:
        """从数据库加载价格线关联关系。"""
        if not self._price_line_database or not self._vt_symbol:
            return
        
        manager = self.get_price_line_manager()
        if not manager:
            return
        
        # 加载所有关联关系
        all_relations = self._price_line_database.load_relations()
        
        # 统计加载的关联关系
        loaded_count = 0
        activated_count = 0
        
        # 按入场线ID分组
        for relation in all_relations:
            entry_line_id = relation["entry_line_id"]
            related_line_id = relation["related_line_id"]
            relation_type = relation["relation_type"]
            
            # 验证关联的价格线是否存在
            entry_line = manager.get_line(entry_line_id)
            related_line = manager.get_line(related_line_id)
            
            # 只加载存在的价格线的关联关系
            if entry_line and related_line:
                if entry_line_id not in self._entry_line_relations:
                    self._entry_line_relations[entry_line_id] = {}
                self._entry_line_relations[entry_line_id][relation_type] = related_line_id
                loaded_count += 1
                
                # ✅ 关键修复：恢复止损止盈线的关联状态
                # 设置 associated_entry_line_id（这样止损止盈线才知道它们关联到哪个入场线）
                if hasattr(related_line, 'set_associated_entry_line_id'):
                    related_line.set_associated_entry_line_id(entry_line_id)
                
                # ✅ 关键修复：激活止损止盈线
                # 入场线关联的止损止盈线应该是激活状态，否则会被识别为挂单止损止盈
                if hasattr(related_line, 'set_creation_time'):
                    from time import time
                    related_line.set_creation_time(time())
                    activated_count += 1
        
        # 记录加载结果
        if hasattr(self, '_main_engine') and self._main_engine and loaded_count > 0:
            self._main_engine.write_log(
                f"[ChartWidget] 从数据库加载了 {loaded_count} 条价格线关联关系，激活了 {activated_count} 条止损/止盈线",
                "ChartWidget"
            )
    
    def save_price_lines(self) -> bool:
        """
        Save all price lines to storage.

        Returns:
            True if successful, False otherwise
        """
        if not self._vt_symbol:
            return False
        
        try:
            all_lines = self._price_line_manager.get_all_lines()
            line_data_list = []
            
            for line_id, line in all_lines.items():
                # Get order ID if linked
                vt_orderid = None
                if self._drawing_order_controller:
                    vt_orderid = self._drawing_order_controller.get_order_id_for_line(line_id)
                
                # ✅ Get entry_line_id (for stop loss/take profit lines)
                entry_line_id = None
                if hasattr(line, 'entry_line_id'):
                    entry_line_id = line.entry_line_id
                
                line_data = PriceLineData(
                    line_id=line_id,
                    price=line.get_price(),
                    line_type=line.get_line_type(),
                    direction=line.get_direction(),
                    vt_symbol=self._vt_symbol,
                    vt_orderid=vt_orderid,
                    entry_line_id=entry_line_id  # ✅ 保存 entry_line_id
                )
                line_data_list.append(line_data)
            
            return self._price_line_storage.save_lines(line_data_list, self._vt_symbol)
        except Exception as e:
            print(f"Error saving price lines: {e}")
            return False
    
    def load_price_lines(self) -> bool:
        """
        Load price lines from storage.

        Returns:
            True if successful, False otherwise
        """
        if not self._vt_symbol:
            return False
        
        try:
            line_data_list = self._price_line_storage.load_lines(self._vt_symbol)
            
            for line_data in line_data_list:
                # Create price line
                line_id = self.add_price_line(
                    price=line_data.price,
                    line_type=line_data.line_type.value,
                    direction=line_data.direction,
                    line_id=line_data.line_id,
                    movable=(line_data.line_type == PriceLineType.PENDING)
                )
                
                # ✅ Restore entry_line_id (for stop loss/take profit lines)
                if line_data.entry_line_id:
                    line = self.get_price_line_manager().get_line(line_id)
                    if line and hasattr(line, 'entry_line_id'):
                        line.entry_line_id = line_data.entry_line_id
                
                # Link to order if exists
                if line_data.vt_orderid and self._drawing_order_controller:
                    self._drawing_order_controller.link_line_to_order(line_id, line_data.vt_orderid)
                
                # Register for breakthrough monitoring if pending
                if line_data.line_type == PriceLineType.PENDING and self._breakthrough_monitor:
                    line = self.get_price_line_manager().get_line(line_id)
                    if line:
                        # Register with a default callback (can be customized)
                        self._breakthrough_monitor.register_line(
                            line_id, line, self._on_price_breakthrough
                        )
            
            return True
        except Exception as e:
            print(f"Error loading price lines: {e}")
            return False

