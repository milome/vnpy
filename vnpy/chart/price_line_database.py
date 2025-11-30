"""
价格线数据库持久化模块。

使用 SQLite 数据库存储价格线数据，包括：
- 价格线基本信息
- 入场线与止损/止盈线的关联关系
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

from vnpy.trader.setting import SETTINGS
from vnpy.trader.database import get_database, DB_TZ

from .price_line import PriceLineType


class PriceLineDatabase:
    """
    价格线数据库操作类。
    
    使用 SQLite 数据库存储价格线数据。
    """
    
    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        初始化数据库连接。
        
        Args:
            db_path: 数据库文件路径。如果为 None，使用默认路径。
        """
        if db_path is None:
            # 使用与主数据库相同的路径
            database_name = SETTINGS.get("database.database", "database.db")
            db_path = database_name
        
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库表
        self._init_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        # 启用WAL模式以提高并发性能
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    
    def debug_print_all_lines_and_relations(self, vt_symbol: Optional[str] = None) -> str:
        """
        打印数据库中所有价格线和关联关系（用于调试）。
        
        Args:
            vt_symbol: VT符号过滤（可选）
            
        Returns:
            格式化的调试信息字符串
        """
        lines = self.load_lines(vt_symbol=vt_symbol)
        all_relations = self.load_relations()
        
        # 构建关联关系映射：entry_line_id -> {relation_type: related_line_id}
        relations_map: Dict[str, Dict[str, str]] = {}
        for rel in all_relations:
            entry_id = rel["entry_line_id"]
            if entry_id not in relations_map:
                relations_map[entry_id] = {}
            relations_map[entry_id][rel["relation_type"]] = rel["related_line_id"]
        
        # 构建所有线的ID集合
        all_line_ids = {line["line_id"] for line in lines}
        
        # 找出孤儿线（在关联关系中但不在价格线表中的线）
        orphan_lines = set()
        for rel in all_relations:
            if rel["related_line_id"] not in all_line_ids:
                orphan_lines.add(rel["related_line_id"])
            if rel["entry_line_id"] not in all_line_ids:
                orphan_lines.add(rel["entry_line_id"])
        
        # 构建输出
        output_lines = []
        output_lines.append("=" * 80)
        output_lines.append(f"数据库价格线和关联关系调试信息 (vt_symbol={vt_symbol or 'ALL'})")
        output_lines.append("=" * 80)
        output_lines.append(f"\n价格线总数: {len(lines)}")
        output_lines.append(f"关联关系总数: {len(all_relations)}")
        if orphan_lines:
            output_lines.append(f"⚠️  发现孤儿线: {len(orphan_lines)} 条")
            for orphan_id in orphan_lines:
                output_lines.append(f"  - {orphan_id}")
        else:
            output_lines.append("✅ 未发现孤儿线")
        
        output_lines.append("\n价格线列表:")
        output_lines.append("-" * 80)
        for line in lines:
            line_id = line["line_id"]
            line_type = line["line_type"].value
            direction = line["direction"]
            price = line["price"]
            relations_info = ""
            if line_id in relations_map:
                rels = relations_map[line_id]
                rel_parts = []
                if "stop_loss" in rels:
                    rel_parts.append(f"止损={rels['stop_loss']}")
                if "take_profit" in rels:
                    rel_parts.append(f"止盈={rels['take_profit']}")
                if rel_parts:
                    relations_info = f" [关联: {', '.join(rel_parts)}]"
            output_lines.append(f"  {line_id}: {line_type} {direction} @{price}{relations_info}")
        
        output_lines.append("\n关联关系列表:")
        output_lines.append("-" * 80)
        for rel in all_relations:
            entry_id = rel["entry_line_id"]
            related_id = rel["related_line_id"]
            rel_type = rel["relation_type"]
            entry_exists = entry_id in all_line_ids
            related_exists = related_id in all_line_ids
            status = "✅" if (entry_exists and related_exists) else "⚠️"
            output_lines.append(
                f"  {status} {entry_id} --[{rel_type}]--> {related_id} "
                f"(入场线存在={entry_exists}, 关联线存在={related_exists})"
            )
        
        output_lines.append("=" * 80)
        return "\n".join(output_lines)
    
    def close(self) -> None:
        """
        关闭数据库连接，确保所有数据已写入。
        
        在程序退出时调用此方法，确保所有未提交的事务都已提交。
        """
        try:
            # 获取连接并执行检查点（WAL模式）
            conn = self._get_connection()
            try:
                # 执行WAL检查点，确保所有数据写入主数据库文件
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            # 忽略关闭时的错误（可能连接已关闭）
            pass
    
    def flush(self) -> None:
        """
        刷新数据库，确保所有数据已持久化。
        
        这是一个轻量级操作，可以在需要时调用。
        """
        try:
            conn = self._get_connection()
            try:
                conn.commit()  # 确保所有未提交的事务已提交
                # WAL模式：执行检查点，将WAL文件内容写入主数据库
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            finally:
                conn.close()
        except Exception as e:
            pass
    
    def _init_tables(self) -> None:
        """初始化数据库表。"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 创建价格线表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_lines (
                    line_id TEXT PRIMARY KEY,
                    price REAL NOT NULL,
                    line_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    vt_symbol TEXT NOT NULL,
                    vt_orderid TEXT,
                    movable INTEGER NOT NULL DEFAULT 0,
                    price_precision INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 创建关联关系表
            # 注意：SQLite 默认不启用外键约束，需要显式启用
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_line_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_line_id TEXT NOT NULL,
                    related_line_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (entry_line_id) REFERENCES price_lines(line_id) ON DELETE CASCADE,
                    FOREIGN KEY (related_line_id) REFERENCES price_lines(line_id) ON DELETE CASCADE,
                    UNIQUE(entry_line_id, related_line_id, relation_type)
                )
            """)
            
            # 创建持仓记录表（用于FIFO平仓）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS position_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vt_symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    line_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL NOT NULL,
                    vt_orderid TEXT,
                    trade_time TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (line_id) REFERENCES price_lines(line_id) ON DELETE CASCADE,
                    UNIQUE(vt_symbol, direction, line_id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_entries_vt_symbol_direction 
                ON position_entries(vt_symbol, direction)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_position_entries_trade_time 
                ON position_entries(trade_time)
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_lines_vt_symbol 
                ON price_lines(vt_symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_lines_line_type 
                ON price_lines(line_type)
            """)
            
            # 数据库迁移：添加挂单参数字段（如果不存在）
            # 使用PRAGMA table_info检查字段是否存在，如果不存在则添加
            cursor.execute("PRAGMA table_info(price_lines)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            if 'order_volume' not in existing_columns:
                try:
                    cursor.execute("ALTER TABLE price_lines ADD COLUMN order_volume REAL")
                except sqlite3.OperationalError:
                    # 字段可能已存在（并发情况），忽略错误
                    pass
            
            if 'order_offset' not in existing_columns:
                try:
                    cursor.execute("ALTER TABLE price_lines ADD COLUMN order_offset TEXT")
                except sqlite3.OperationalError:
                    # 字段可能已存在（并发情况），忽略错误
                    pass
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_line_relations_entry 
                ON price_line_relations(entry_line_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_line_relations_related 
                ON price_line_relations(related_line_id)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def save_line(
        self,
        line_id: str,
        price: float,
        line_type: PriceLineType,
        direction: str,
        vt_symbol: str,
        movable: bool = False,
        price_precision: int = 0,
        vt_orderid: Optional[str] = None,
        order_volume: Optional[float] = None,
        order_offset: Optional[str] = None
    ) -> bool:
        """
        保存价格线。
        
        Args:
            line_id: 价格线ID
            price: 价格
            line_type: 价格线类型
            direction: 方向 ("long" 或 "short")
            vt_symbol: VT符号
            movable: 是否可拖拽
            price_precision: 价格精度
            vt_orderid: 关联的订单ID（可选）
            order_volume: 挂单线的订单手数（仅PENDING类型，可选）
            order_offset: 挂单线的开平类型（仅PENDING类型，"OPEN"或"CLOSE"，可选）
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now(DB_TZ).isoformat()
            
            # 检查是否已存在
            cursor.execute("SELECT created_at FROM price_lines WHERE line_id = ?", (line_id,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新：保留原有 created_at
                created_at = existing["created_at"]
                cursor.execute("""
                    UPDATE price_lines 
                    SET price = ?, line_type = ?, direction = ?, vt_symbol = ?, 
                        vt_orderid = ?, movable = ?, price_precision = ?, 
                        order_volume = ?, order_offset = ?, updated_at = ?
                    WHERE line_id = ?
                """, (
                    price, line_type.value, direction, vt_symbol, vt_orderid,
                    int(movable), price_precision, order_volume, order_offset, now, line_id
                ))
            else:
                # 插入：使用新的 created_at
                cursor.execute("""
                    INSERT INTO price_lines 
                    (line_id, price, line_type, direction, vt_symbol, vt_orderid, 
                     movable, price_precision, order_volume, order_offset, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    line_id, price, line_type.value, direction, vt_symbol, vt_orderid,
                    int(movable), price_precision, order_volume, order_offset, now, now
                ))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error saving price line: {e}")
            return False
        finally:
            conn.close()
    
    def load_lines(
        self,
        vt_symbol: Optional[str] = None,
        line_type: Optional[PriceLineType] = None
    ) -> List[Dict]:
        """
        加载价格线。
        
        Args:
            vt_symbol: VT符号过滤（可选）
            line_type: 价格线类型过滤（可选）
            
        Returns:
            价格线数据列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM price_lines WHERE 1=1"
            params = []
            
            if vt_symbol:
                query += " AND vt_symbol = ?"
                params.append(vt_symbol)
            
            if line_type:
                query += " AND line_type = ?"
                params.append(line_type.value)
            
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                # 获取挂单参数（可能为NULL，对于旧数据或非PENDING类型）
                # sqlite3.Row 不支持 .get() 方法，使用字典访问方式
                # 如果字段不存在会抛出 KeyError，但我们已经通过数据库迁移确保字段存在
                order_volume = row["order_volume"] if row["order_volume"] is not None else None
                order_offset = row["order_offset"] if row["order_offset"] is not None else None
                
                result.append({
                    "line_id": row["line_id"],
                    "price": row["price"],
                    "line_type": PriceLineType(row["line_type"]),
                    "direction": row["direction"],
                    "vt_symbol": row["vt_symbol"],
                    "vt_orderid": row["vt_orderid"],
                    "movable": bool(row["movable"]),
                    "price_precision": row["price_precision"],
                    "order_volume": order_volume,  # 挂单线的订单手数（可能为NULL）
                    "order_offset": order_offset,  # 挂单线的开平类型（可能为NULL）
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return result
        except Exception as e:
            print(f"Error loading price lines: {e}")
            return []
        finally:
            conn.close()
    
    def delete_line(self, line_id: str) -> bool:
        """
        删除价格线。
        
        Args:
            line_id: 价格线ID
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_lines WHERE line_id = ?", (line_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting price line: {e}")
            return False
        finally:
            conn.close()
    
    def delete_lines_by_symbol(self, vt_symbol: str) -> bool:
        """
        删除指定合约的所有价格线。
        
        Args:
            vt_symbol: VT符号
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_lines WHERE vt_symbol = ?", (vt_symbol,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting price lines by symbol: {e}")
            return False
        finally:
            conn.close()
    
    def save_relation(
        self,
        entry_line_id: str,
        related_line_id: str,
        relation_type: str
    ) -> bool:
        """
        保存价格线关联关系。
        
        Args:
            entry_line_id: 入场线ID
            related_line_id: 关联的价格线ID（止损或止盈线）
            relation_type: 关联类型 ("stop_loss" 或 "take_profit")
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now(DB_TZ).isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO price_line_relations 
                (entry_line_id, related_line_id, relation_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (entry_line_id, related_line_id, relation_type, now))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error saving price line relation: {e}")
            return False
        finally:
            conn.close()
    
    def load_relations(
        self,
        entry_line_id: Optional[str] = None,
        related_line_id: Optional[str] = None
    ) -> List[Dict]:
        """
        加载价格线关联关系。
        
        Args:
            entry_line_id: 入场线ID过滤（可选）
            related_line_id: 关联线ID过滤（可选）
            
        Returns:
            关联关系列表
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM price_line_relations WHERE 1=1"
            params = []
            
            if entry_line_id:
                query += " AND entry_line_id = ?"
                params.append(entry_line_id)
            
            if related_line_id:
                query += " AND related_line_id = ?"
                params.append(related_line_id)
            
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "entry_line_id": row["entry_line_id"],
                    "related_line_id": row["related_line_id"],
                    "relation_type": row["relation_type"],
                    "created_at": row["created_at"]
                })
            
            return result
        except Exception as e:
            print(f"Error loading price line relations: {e}")
            return []
        finally:
            conn.close()
    
    def delete_relation(
        self,
        entry_line_id: str,
        relation_type: Optional[str] = None
    ) -> bool:
        """
        删除价格线关联关系。
        
        Args:
            entry_line_id: 入场线ID
            relation_type: 关联类型过滤（可选，如果提供则只删除该类型的关联）
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if relation_type:
                cursor.execute("""
                    DELETE FROM price_line_relations 
                    WHERE entry_line_id = ? AND relation_type = ?
                """, (entry_line_id, relation_type))
            else:
                cursor.execute("""
                    DELETE FROM price_line_relations 
                    WHERE entry_line_id = ?
                """, (entry_line_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting price line relation: {e}")
            return False
        finally:
            conn.close()
    
    def delete_all_relations(self, entry_line_id: str) -> bool:
        """
        删除指定入场线的所有关联关系。
        
        Args:
            entry_line_id: 入场线ID
            
        Returns:
            成功返回 True，失败返回 False
        """
        return self.delete_relation(entry_line_id, relation_type=None)
    
    def delete_relations_by_related_line_id(self, related_line_id: str) -> bool:
        """
        删除所有指向指定关联线的关联关系（用于删除止损/止盈线时清理关联关系）。
        
        Args:
            related_line_id: 关联线ID（止损或止盈线ID）
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM price_line_relations 
                WHERE related_line_id = ?
            """, (related_line_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting relations by related_line_id: {e}")
            return False
        finally:
            conn.close()
    
    def get_related_lines(self, entry_line_id: str) -> Dict[str, str]:
        """
        获取入场线关联的止损/止盈线ID。
        
        Args:
            entry_line_id: 入场线ID
            
        Returns:
            字典，key 为 "stop_loss" 或 "take_profit"，value 为关联线ID
        """
        relations = self.load_relations(entry_line_id=entry_line_id)
        result = {}
        for rel in relations:
            result[rel["relation_type"]] = rel["related_line_id"]
        return result
    
    def save_position_entry(
        self,
        vt_symbol: str,
        direction: str,
        line_id: str,
        price: float,
        volume: float,
        vt_orderid: Optional[str] = None,
        trade_time: Optional[datetime] = None
    ) -> bool:
        """
        保存持仓记录（用于FIFO平仓）。
        
        Args:
            vt_symbol: VT符号
            direction: 方向 ("long" 或 "short")
            line_id: 入场线ID
            price: 入场价格
            volume: 持仓手数
            vt_orderid: 关联的订单ID（可选）
            trade_time: 成交时间（可选）
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now(DB_TZ).isoformat()
            
            trade_time_str = trade_time.isoformat() if trade_time else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO position_entries 
                (vt_symbol, direction, line_id, price, volume, vt_orderid, trade_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vt_symbol, direction, line_id, price, volume, vt_orderid, trade_time_str, now
            ))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error saving position entry: {e}")
            return False
        finally:
            conn.close()
    
    def load_position_entries(
        self,
        vt_symbol: str,
        direction: Optional[str] = None
    ) -> List[Dict]:
        """
        加载持仓记录。
        
        Args:
            vt_symbol: VT符号
            direction: 方向过滤（可选）
            
        Returns:
            持仓记录列表，按成交时间排序（FIFO顺序）
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM position_entries WHERE vt_symbol = ?"
            params = [vt_symbol]
            
            if direction:
                query += " AND direction = ?"
                params.append(direction)
            
            query += " ORDER BY trade_time ASC, created_at ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                trade_time = None
                if row["trade_time"]:
                    try:
                        trade_time = datetime.fromisoformat(row["trade_time"])
                    except (ValueError, TypeError):
                        pass
                
                result.append({
                    "id": row["id"],
                    "vt_symbol": row["vt_symbol"],
                    "direction": row["direction"],
                    "line_id": row["line_id"],
                    "price": row["price"],
                    "volume": row["volume"],
                    "vt_orderid": row["vt_orderid"],
                    "trade_time": trade_time,
                    "created_at": row["created_at"]
                })
            
            return result
        except Exception as e:
            print(f"Error loading position entries: {e}")
            return []
        finally:
            conn.close()
    
    def update_position_entry_volume(
        self,
        vt_symbol: str,
        direction: str,
        line_id: str,
        new_volume: float
    ) -> bool:
        """
        更新持仓记录的手数（用于部分平仓）。
        
        Args:
            vt_symbol: VT符号
            direction: 方向
            line_id: 入场线ID
            new_volume: 新的持仓手数
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE position_entries 
                SET volume = ?
                WHERE vt_symbol = ? AND direction = ? AND line_id = ?
            """, (new_volume, vt_symbol, direction, line_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating position entry volume: {e}")
            return False
        finally:
            conn.close()
    
    def delete_position_entry(
        self,
        vt_symbol: str,
        direction: str,
        line_id: str
    ) -> bool:
        """
        删除持仓记录（用于完全平仓）。
        
        Args:
            vt_symbol: VT符号
            direction: 方向
            line_id: 入场线ID
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM position_entries 
                WHERE vt_symbol = ? AND direction = ? AND line_id = ?
            """, (vt_symbol, direction, line_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting position entry: {e}")
            return False
        finally:
            conn.close()
    
    def delete_position_entries_by_symbol(
        self,
        vt_symbol: str,
        direction: Optional[str] = None
    ) -> bool:
        """
        删除指定合约的所有持仓记录。
        
        Args:
            vt_symbol: VT符号
            direction: 方向过滤（可选）
            
        Returns:
            成功返回 True，失败返回 False
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            if direction:
                cursor.execute("""
                    DELETE FROM position_entries 
                    WHERE vt_symbol = ? AND direction = ?
                """, (vt_symbol, direction))
            else:
                cursor.execute("""
                    DELETE FROM position_entries 
                    WHERE vt_symbol = ?
                """, (vt_symbol,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting position entries: {e}")
            return False
        finally:
            conn.close()

