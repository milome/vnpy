"""
Price line persistence storage module.

Provides storage and retrieval of price lines for chart widgets.
"""

import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from vnpy.trader.constant import Exchange

from .price_line import PriceLineType


class PriceLineData:
    """Data class for price line storage."""

    def __init__(
        self,
        line_id: str,
        price: float,
        line_type: PriceLineType,
        direction: str,
        vt_symbol: str,
        vt_orderid: Optional[str] = None,
        created_at: Optional[datetime] = None,
        entry_line_id: Optional[str] = None  # ✅ 添加 entry_line_id 字段
    ) -> None:
        """
        Initialize price line data.

        Args:
            line_id: Unique line ID
            price: Price value
            line_type: Type of price line
            direction: Trading direction ("long" or "short")
            vt_symbol: VT symbol for the chart
            vt_orderid: Optional VT order ID if linked to an order
            created_at: Creation timestamp
            entry_line_id: Optional entry line ID (for stop loss/take profit lines)
        """
        self.line_id = line_id
        self.price = price
        self.line_type = line_type
        self.direction = direction
        self.vt_symbol = vt_symbol
        self.vt_orderid = vt_orderid
        self.entry_line_id = entry_line_id  # ✅ 保存 entry_line_id
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "line_id": self.line_id,
            "price": self.price,
            "line_type": self.line_type.value,
            "direction": self.direction,
            "vt_symbol": self.vt_symbol,
            "vt_orderid": self.vt_orderid,
            "created_at": self.created_at.isoformat(),
            "entry_line_id": self.entry_line_id  # ✅ 保存 entry_line_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceLineData":
        """Create from dictionary."""
        return cls(
            line_id=data["line_id"],
            price=data["price"],
            line_type=PriceLineType(data["line_type"]),
            direction=data["direction"],
            vt_symbol=data["vt_symbol"],
            vt_orderid=data.get("vt_orderid"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            entry_line_id=data.get("entry_line_id")  # ✅ 加载 entry_line_id
        )


class PriceLineStorage:
    """
    Storage manager for price lines.
    
    Provides save/load functionality for price lines.
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """
        Initialize price line storage.

        Args:
            storage_path: Path to storage file. If None, use default path.
        """
        if storage_path is None:
            # Default to user data directory
            from vnpy.trader.setting import SETTINGS
            data_path = Path(SETTINGS.get("data.path", "."))
            storage_path = str(data_path / "price_lines.json")

        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_lines(
        self,
        lines: List[PriceLineData],
        vt_symbol: Optional[str] = None
    ) -> bool:
        """
        Save price lines to storage.

        Args:
            lines: List of price line data
            vt_symbol: Optional VT symbol to filter by

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing data
            all_data = self._load_all()

            # Filter by vt_symbol if provided
            if vt_symbol:
                # Remove existing lines for this symbol
                all_data = [d for d in all_data if d.get("vt_symbol") != vt_symbol]
            
            # Add new lines
            for line in lines:
                line_dict = line.to_dict()
                if vt_symbol:
                    line_dict["vt_symbol"] = vt_symbol
                all_data.append(line_dict)

            # Save to file
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving price lines: {e}")
            return False

    def load_lines(self, vt_symbol: Optional[str] = None) -> List[PriceLineData]:
        """
        Load price lines from storage.

        Args:
            vt_symbol: Optional VT symbol to filter by

        Returns:
            List of price line data
        """
        try:
            all_data = self._load_all()

            # Filter by vt_symbol if provided
            if vt_symbol:
                all_data = [d for d in all_data if d.get("vt_symbol") == vt_symbol]

            # Convert to PriceLineData objects
            lines = []
            for data in all_data:
                try:
                    line = PriceLineData.from_dict(data)
                    lines.append(line)
                except Exception as e:
                    print(f"Error loading price line: {e}")
                    continue

            return lines
        except Exception as e:
            print(f"Error loading price lines: {e}")
            return []

    def delete_lines(self, vt_symbol: Optional[str] = None) -> bool:
        """
        Delete price lines from storage.

        Args:
            vt_symbol: VT symbol to delete lines for. If None, delete all.

        Returns:
            True if successful, False otherwise
        """
        try:
            if vt_symbol is None:
                # Delete all
                if self._storage_path.exists():
                    self._storage_path.unlink()
                return True

            # Load existing data
            all_data = self._load_all()

            # Filter out lines for this symbol
            filtered_data = [d for d in all_data if d.get("vt_symbol") != vt_symbol]

            # Save back
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(filtered_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error deleting price lines: {e}")
            return False

    def _load_all(self) -> List[dict]:
        """Load all data from storage file."""
        if not self._storage_path.exists():
            return []

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def get_lines_by_order(self, vt_orderid: str) -> List[PriceLineData]:
        """
        Get price lines linked to a specific order.

        Args:
            vt_orderid: VT order ID

        Returns:
            List of price line data
        """
        all_lines = self.load_lines()
        return [line for line in all_lines if line.vt_orderid == vt_orderid]

