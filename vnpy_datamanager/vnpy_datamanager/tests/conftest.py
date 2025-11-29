"""
pytest配置文件和共享fixtures
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.database import BaseDatabase, BarOverview, DB_TZ

from ..engine import ManagerEngine


@pytest.fixture
def mock_main_engine():
    """创建模拟的MainEngine"""
    engine = Mock(spec=MainEngine)
    engine.write_log = Mock()
    return engine


@pytest.fixture
def mock_event_engine():
    """创建模拟的EventEngine"""
    engine = Mock(spec=EventEngine)
    engine.register = Mock()
    return engine


@pytest.fixture
def mock_database():
    """创建模拟的数据库"""
    db = Mock(spec=BaseDatabase)
    db.save_bar_data = Mock()
    db.load_bar_data = Mock(return_value=[])
    db.delete_bar_data = Mock(return_value=0)
    db.get_bar_overview = Mock(return_value=[])
    return db


@pytest.fixture
def mock_datafeed():
    """创建模拟的数据源"""
    datafeed = Mock()
    datafeed.query_bar_history = Mock(return_value=[])
    return datafeed


@pytest.fixture
def manager_engine(mock_main_engine, mock_event_engine, mock_database, mock_datafeed):
    """创建ManagerEngine实例"""
    with patch('vnpy_datamanager.engine.get_database', return_value=mock_database), \
         patch('vnpy_datamanager.engine.get_datafeed', return_value=mock_datafeed):
        engine = ManagerEngine(mock_main_engine, mock_event_engine)
        return engine


@pytest.fixture
def sample_bar_overview():
    """创建示例BarOverview数据"""
    return BarOverview(
        symbol="rb2401",
        exchange=Exchange.SHFE,
        interval=Interval.MINUTE,
        count=1000,
        start=datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
        end=datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
    )


@pytest.fixture
def sample_bars():
    """创建示例BarData列表"""
    bars = []
    base_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ)
    for i in range(10):
        bar = BarData(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            datetime=base_time.replace(minute=i),
            interval=Interval.MINUTE,
            open_price=100.0 + i,
            high_price=101.0 + i,
            low_price=99.0 + i,
            close_price=100.5 + i,
            volume=1000 + i * 100,
            turnover=100000 + i * 10000,
            open_interest=10000 + i * 100,
            gateway_name="DB"
        )
        bars.append(bar)
    return bars

