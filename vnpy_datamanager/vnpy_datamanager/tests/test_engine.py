"""
测试ManagerEngine
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.database import BarOverview, DB_TZ

from ..engine import ManagerEngine
from .conftest import manager_engine, sample_bar_overview, sample_bars


class TestManagerEngine:
    """测试ManagerEngine类"""
    
    def test_get_bar_overview(self, manager_engine, mock_database):
        """测试获取K线数据概览"""
        overview = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=100,
            start=datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            end=datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        mock_database.get_bar_overview.return_value = [overview]
        
        result = manager_engine.get_bar_overview()
        assert len(result) == 1
        assert result[0].symbol == "rb2401"
        mock_database.get_bar_overview.assert_called_once()
    
    def test_download_bar_data_minute(self, manager_engine, mock_database, mock_datafeed, mock_main_engine, sample_bars):
        """测试下载1分钟K线数据"""
        # 模拟数据源返回数据
        bars = sample_bars
        mock_datafeed.query_bar_history.return_value = bars
        
        # 模拟数据库查询返回空（表示需要下载）
        mock_database.load_bar_data.return_value = []
        
        # 模拟get_contract方法
        from vnpy.trader.object import ContractData
        mock_contract = Mock(spec=ContractData)
        mock_contract.vt_symbol = "rb2401.SHFE"
        mock_contract.gateway_name = "TEST"
        mock_contract.history_data = False  # 不使用网关历史数据，使用数据源
        mock_main_engine.get_contract = Mock(return_value=mock_contract)
        
        output_callback = Mock()
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ)
        
        count = manager_engine.download_bar_data(
            "rb2401",
            Exchange.SHFE,
            Interval.MINUTE,
            start_time,
            output_callback
        )
        
        # 验证调用了数据源查询
        assert mock_datafeed.query_bar_history.called
        # 验证调用了数据库保存
        assert mock_database.save_bar_data.called
    
    def test_download_bar_data_5minute_aggregate(self, manager_engine, mock_database):
        """测试下载5分钟数据（从1分钟合成）"""
        output_callback = Mock()
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ)
        
        # 模拟aggregate_5minute_bars返回数据量
        with patch.object(manager_engine, 'aggregate_5minute_bars', return_value=100) as mock_agg:
            count = manager_engine.download_bar_data(
                "rb2401",
                Exchange.SHFE,
                Interval.MINUTE_5,
                start_time,
                output_callback
            )
            
            assert count == 100
            mock_agg.assert_called_once()
            # 验证调用了output回调
            assert output_callback.called
    
    def test_download_bar_data_hour_aggregate(self, manager_engine):
        """测试下载1小时数据（从1分钟合成）"""
        output_callback = Mock()
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ)
        
        # 模拟aggregate_hour_bars返回数据量
        with patch.object(manager_engine, 'aggregate_hour_bars', return_value=50) as mock_agg:
            count = manager_engine.download_bar_data(
                "rb2401",
                Exchange.SHFE,
                Interval.HOUR,
                start_time,
                output_callback
            )
            
            assert count == 50
            mock_agg.assert_called_once()
    
    def test_download_bar_data_4hour_aggregate(self, manager_engine):
        """测试下载4小时数据（从已有数据合成）"""
        output_callback = Mock()
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ)
        
        # 模拟aggregate_4hour_bars返回数据量
        with patch.object(manager_engine, 'aggregate_4hour_bars', return_value=20) as mock_agg:
            count = manager_engine.download_bar_data(
                "rb2401",
                Exchange.SHFE,
                Interval.HOUR_4,
                start_time,
                output_callback
            )
            
            assert count == 20
            mock_agg.assert_called_once()
    
    def test_load_bar_data(self, manager_engine, mock_database, sample_bars):
        """测试加载K线数据"""
        mock_database.load_bar_data.return_value = sample_bars
        
        result = manager_engine.load_bar_data(
            "rb2401",
            Exchange.SHFE,
            Interval.MINUTE,
            datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        
        assert len(result) == len(sample_bars)
        mock_database.load_bar_data.assert_called_once()
    
    def test_delete_bar_data(self, manager_engine, mock_database):
        """测试删除K线数据"""
        mock_database.delete_bar_data.return_value = 100
        
        count = manager_engine.delete_bar_data(
            "rb2401",
            Exchange.SHFE,
            Interval.MINUTE
        )
        
        assert count == 100
        mock_database.delete_bar_data.assert_called_once()
    
    def test_output_data_to_csv(self, manager_engine, mock_database, sample_bars, tmp_path):
        """测试导出数据到CSV"""
        mock_database.load_bar_data.return_value = sample_bars
        
        csv_path = tmp_path / "test_output.csv"
        
        result = manager_engine.output_data_to_csv(
            str(csv_path),
            "rb2401",
            Exchange.SHFE,
            Interval.MINUTE,
            datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        
        assert result == True
        assert csv_path.exists()
        # 验证CSV文件内容
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            assert len(lines) > 1  # 至少包含表头和一行数据
    
    def test_aggregate_5minute_bars(self, manager_engine, mock_database, sample_bars, mock_main_engine):
        """测试合成5分钟K线"""
        # 模拟数据库中有1分钟数据
        extended_bars = sample_bars * 10  # 扩展数据量
        mock_database.load_bar_data.return_value = extended_bars
        
        # 模拟get_bar_overview返回1分钟数据概览（这样方法才会尝试加载数据）
        minute_overview = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=len(extended_bars),
            start=extended_bars[0].datetime,
            end=extended_bars[-1].datetime
        )
        mock_database.get_bar_overview.return_value = [minute_overview]
        mock_database.save_bar_data = Mock()
        
        # 直接测试方法
        count = manager_engine.aggregate_5minute_bars("rb2401", Exchange.SHFE)
            
        # 验证调用了数据库加载
        assert mock_database.load_bar_data.called
        assert isinstance(count, int)
    
    def test_aggregate_hour_bars(self, manager_engine, mock_database, sample_bars, mock_main_engine):
        """测试合成1小时K线"""
        extended_bars = sample_bars * 10
        mock_database.load_bar_data.return_value = extended_bars
        
        # 模拟get_bar_overview返回1分钟数据概览
        minute_overview = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=len(extended_bars),
            start=extended_bars[0].datetime,
            end=extended_bars[-1].datetime
        )
        mock_database.get_bar_overview.return_value = [minute_overview]
        mock_database.save_bar_data = Mock()
        
        # 直接测试方法
        count = manager_engine.aggregate_hour_bars("rb2401", Exchange.SHFE)
            
        # 验证调用了数据库加载
        assert mock_database.load_bar_data.called
        assert isinstance(count, int)
    
    def test_aggregate_4hour_bars(self, manager_engine, mock_database, sample_bars, mock_main_engine):
        """测试合成4小时K线"""
        extended_bars = sample_bars * 20
        mock_database.load_bar_data.return_value = extended_bars
        
        # 模拟get_bar_overview返回1分钟数据概览（4小时可以从1分钟或1小时合成）
        minute_overview = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=len(extended_bars),
            start=extended_bars[0].datetime,
            end=extended_bars[-1].datetime
        )
        mock_database.get_bar_overview.return_value = [minute_overview]
        mock_database.save_bar_data = Mock()
        
        # 直接测试方法
        count = manager_engine.aggregate_4hour_bars("rb2401", Exchange.SHFE)
            
        # 验证调用了数据库加载
        assert mock_database.load_bar_data.called
        assert isinstance(count, int)

