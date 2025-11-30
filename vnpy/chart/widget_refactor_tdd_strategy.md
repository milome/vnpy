# ChartWidget 重构 - TDD测试策略

## 📋 测试驱动开发（TDD）红绿灯模式

### TDD 三步骤

1. **🔴 红（Red）**: 先写失败的测试用例
   - 定义期望的行为
   - 测试应该失败（因为功能还未实现）

2. **🟢 绿（Green）**: 写最少的代码让测试通过
   - 实现功能，使测试通过
   - 不追求完美，只求通过

3. **🔵 重构（Refactor）**: 优化代码，保持测试通过
   - 改进代码质量
   - 确保所有测试仍然通过

## 🎯 测试覆盖率要求

### 覆盖率目标
- **总体覆盖率**: > 95%
- **分支覆盖率**: > 90%
- **语句覆盖率**: > 95%
- **函数覆盖率**: > 95%

### 覆盖率统计工具
- **工具**: `pytest-cov` + `coverage`
- **命令**: 
  ```bash
  pytest tests/chart/ --cov=vnpy.chart --cov-report=html --cov-report=term-missing
  coverage report --show-missing
  ```

### 覆盖率配置
创建 `.coveragerc` 文件：
```ini
[run]
source = vnpy/chart
omit = 
    */tests/*
    */__pycache__/*
    */conftest.py

[report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

## 📁 测试文件结构

```
tests/
├── chart/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── test_base.py             # 测试基类和工具函数
│   ├── test_widget.py           # 核心功能测试
│   ├── test_widget_position.py  # 持仓管理测试
│   ├── test_widget_order.py    # 订单处理测试
│   ├── test_widget_trigger.py  # 触发下单/平仓测试
│   ├── test_widget_mouse.py    # 鼠标事件测试
│   ├── test_widget_chart.py    # 图表更新测试
│   ├── test_widget_database.py # 数据库操作测试
│   └── test_widget_cursor.py   # 光标类测试
└── requirements-test.txt        # 测试依赖
```

## 🧪 测试用例设计原则

### 1. 单元测试
- 测试单个方法/函数
- 使用 Mock 隔离依赖
- 快速执行

### 2. 集成测试
- 测试模块间的交互
- 使用真实对象（适度）
- 验证整体功能

### 3. 测试命名规范
```python
def test_<method_name>_<scenario>_<expected_result>():
    """测试方法名_场景_期望结果"""
    pass
```

### 4. 测试组织
- **Arrange**: 准备测试数据
- **Act**: 执行被测试的方法
- **Assert**: 验证结果

## 📝 测试示例

### 示例1: 持仓管理模块测试

```python
# tests/chart/test_widget_position.py

import pytest
from unittest.mock import Mock, MagicMock, patch
from vnpy.trader.object import PositionData
from vnpy.trader.constant import Direction
from vnpy.chart.widget_position import ChartWidgetPositionMixin
from vnpy.chart.widget import ChartWidget


class TestChartWidgetPosition:
    """持仓管理模块测试"""
    
    @pytest.fixture
    def widget(self):
        """创建ChartWidget实例"""
        widget = ChartWidget()
        widget._main_engine = Mock()
        widget._event_engine = Mock()
        widget._vt_symbol = "MHI2512.HKFE"
        widget._price_line_manager = Mock()
        widget._position_holdings = {}
        widget._entry_line_relations = {}
        return widget
    
    @pytest.fixture
    def position_data(self):
        """创建持仓数据"""
        position = PositionData(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10,
            frozen=0,
            price=20000,
            pnl=1000
        )
        return position
    
    def test_register_position_events_success(self, widget):
        """测试成功注册持仓事件"""
        # Arrange
        widget._event_engine = Mock()
        
        # Act
        widget._register_position_events()
        
        # Assert
        assert widget._event_engine.register.call_count == 3
    
    def test_register_position_events_no_event_engine(self, widget):
        """测试没有event_engine时的情况"""
        # Arrange
        widget._event_engine = None
        
        # Act
        widget._register_position_events()
        
        # Assert
        # 应该记录日志但不报错
        assert True
    
    def test_on_position_update_matched_contract(self, widget, position_data):
        """测试合约匹配的持仓更新"""
        # Arrange
        widget._vt_symbol = "MHI2512.HKFE"
        position_data.vt_symbol = "MHI2512.HKFE"
        
        # Act
        widget._on_position_update(Mock(data=position_data))
        
        # Assert
        # 验证信号被发出或方法被调用
        assert True
    
    def test_update_entry_line_pnl_zero_position(self, widget, position_data):
        """测试持仓为0时的更新逻辑"""
        # Arrange
        position_data.volume = 0
        widget._position_holdings = {"long": Mock()}
        
        # Act
        widget._update_entry_line_pnl(position_data)
        
        # Assert
        # 验证持仓记录被清除
        assert "long" not in widget._position_holdings
    
    def test_update_entry_line_pnl_with_position(self, widget, position_data):
        """测试有持仓时的更新逻辑"""
        # Arrange
        position_data.volume = 10
        widget._position_holdings = {"long": Mock()}
        widget._price_line_manager.get_all_lines.return_value = {}
        
        # Act
        widget._update_entry_line_pnl(position_data)
        
        # Assert
        # 验证入场线被更新
        assert True
    
    def test_clear_frozen_position_lines(self, widget, position_data):
        """测试清除冻结持仓线"""
        # Arrange
        position_data.volume = 10
        position_data.frozen = 10
        widget._price_line_manager.get_all_lines.return_value = {}
        
        # Act
        widget._clear_frozen_position_lines(position_data)
        
        # Assert
        # 验证冻结持仓线被清除
        assert True
```

### 示例2: 订单处理模块测试

```python
# tests/chart/test_widget_order.py

import pytest
from unittest.mock import Mock, MagicMock, patch
from vnpy.trader.object import OrderData
from vnpy.trader.constant import Status, Direction, Offset
from vnpy.chart.widget_order import ChartWidgetOrderMixin
from vnpy.chart.widget import ChartWidget


class TestChartWidgetOrder:
    """订单处理模块测试"""
    
    @pytest.fixture
    def widget(self):
        """创建ChartWidget实例"""
        widget = ChartWidget()
        widget._main_engine = Mock()
        widget._drawing_order_controller = Mock()
        widget._processed_order_updates = {}
        widget._order_update_dedup_ttl = 1.0
        return widget
    
    @pytest.fixture
    def order_data(self):
        """创建订单数据"""
        order = OrderData(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            orderid="12345",
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=20000,
            volume=10,
            traded=10,
            status=Status.ALLTRADED
        )
        return order
    
    def test_on_order_update_duplicate_filtered(self, widget, order_data):
        """测试订单去重机制"""
        # Arrange
        order_key = f"{order_data.vt_orderid}_{order_data.status.value}"
        widget._processed_order_updates[order_key] = time()
        
        # Act
        widget._on_order_update(Mock(data=order_data))
        
        # Assert
        # 验证重复订单被过滤
        assert True
    
    def test_on_order_update_alltraded_creates_entry_line(self, widget, order_data):
        """测试全部成交订单创建入场线"""
        # Arrange
        order_data.status = Status.ALLTRADED
        widget._drawing_order_controller.get_line_id_for_order.return_value = "line_123"
        widget._drawing_order_controller.update_line_from_order.return_value = True
        
        # Act
        widget._process_order_update(order_data)
        
        # Assert
        widget._drawing_order_controller.update_line_from_order.assert_called_once()
    
    def test_process_order_update_main_thread(self, widget, order_data):
        """测试主线程中的订单处理"""
        # Arrange
        with patch('vnpy.trader.ui.QtCore.QThread.currentThread') as mock_thread:
            mock_thread.return_value = Mock()
            
            # Act
            widget._process_order_update(order_data)
            
            # Assert
            assert True
```

### 示例3: 触发模块测试

```python
# tests/chart/test_widget_trigger.py

import pytest
from unittest.mock import Mock, MagicMock, patch
from vnpy.trader.object import TickData
from vnpy.chart.widget_trigger import ChartWidgetTriggerMixin
from vnpy.chart.widget import ChartWidget


class TestChartWidgetTrigger:
    """触发下单/平仓模块测试"""
    
    @pytest.fixture
    def widget(self):
        """创建ChartWidget实例"""
        widget = ChartWidget()
        widget._main_engine = Mock()
        widget._vt_symbol = "MHI2512.HKFE"
        widget._price_line_manager = Mock()
        widget._breakthrough_monitor = Mock()
        widget._pending_order_trigger_lock = Mock()
        return widget
    
    @pytest.fixture
    def tick_data(self):
        """创建Tick数据"""
        tick = TickData(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20000,
            bid_price_1=19999,
            ask_price_1=20001
        )
        return tick
    
    def test_trigger_pending_order_breakthrough_success(self, widget, tick_data):
        """测试挂单线突破下单成功"""
        # Arrange
        line = Mock()
        line.get_order_volume.return_value = 10
        line.get_order_offset.return_value = "OPEN"
        line.get_price.return_value = 20000
        line.get_direction.return_value = "long"
        
        widget._main_engine.send_order.return_value = "order_123"
        widget._main_engine.get_contract.return_value = Mock(gateway_name="test")
        
        # Act
        result = widget.trigger_pending_order_breakthrough("line_123", line, tick_data)
        
        # Assert
        assert result is True
        widget._main_engine.send_order.assert_called_once()
    
    def test_trigger_stop_loss_close_long_position(self, widget, tick_data):
        """测试多仓止损触发"""
        # Arrange
        line = Mock()
        line.get_price.return_value = 19900
        line.get_direction.return_value = "long"
        line.get_volume.return_value = 10
        
        tick_data.last_price = 19899  # 低于止损价
        
        position = Mock()
        position.volume = 10
        position.frozen = 0
        widget._main_engine.get_position.return_value = position
        widget._main_engine.get_contract.return_value = Mock(gateway_name="test")
        widget._main_engine.send_order.return_value = "order_123"
        
        # Act
        result = widget.trigger_stop_loss_close("line_123", line, tick_data)
        
        # Assert
        assert result is True
        widget._main_engine.send_order.assert_called_once()
    
    def test_trigger_take_profit_close_short_position(self, widget, tick_data):
        """测试空仓止盈触发"""
        # Arrange
        line = Mock()
        line.get_price.return_value = 20100
        line.get_direction.return_value = "short"
        line.get_volume.return_value = 10
        
        tick_data.last_price = 20099  # 低于止盈价（空仓止盈）
        
        position = Mock()
        position.volume = 10
        position.frozen = 0
        widget._main_engine.get_position.return_value = position
        widget._main_engine.get_contract.return_value = Mock(gateway_name="test")
        widget._main_engine.send_order.return_value = "order_123"
        
        # Act
        result = widget.trigger_take_profit_close("line_123", line, tick_data)
        
        # Assert
        assert result is True
        widget._main_engine.send_order.assert_called_once()
```

## 🔧 测试工具和配置

### pytest 配置 (pytest.ini)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=vnpy.chart
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=95
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

### conftest.py 示例
```python
# tests/chart/conftest.py

import pytest
from unittest.mock import Mock
from vnpy.chart.widget import ChartWidget


@pytest.fixture
def mock_main_engine():
    """创建模拟的MainEngine"""
    engine = Mock()
    engine.write_log = Mock()
    engine.get_contract = Mock(return_value=Mock(gateway_name="test"))
    engine.get_all_positions = Mock(return_value=[])
    engine.get_all_active_orders = Mock(return_value=[])
    return engine


@pytest.fixture
def mock_event_engine():
    """创建模拟的EventEngine"""
    engine = Mock()
    engine.register = Mock()
    return engine


@pytest.fixture
def chart_widget(mock_main_engine, mock_event_engine):
    """创建ChartWidget实例用于测试"""
    widget = ChartWidget()
    widget._main_engine = mock_main_engine
    widget._event_engine = mock_event_engine
    widget._vt_symbol = "MHI2512.HKFE"
    return widget
```

## 📊 覆盖率报告

### 生成覆盖率报告
```bash
# 运行测试并生成覆盖率报告
pytest tests/chart/ --cov=vnpy.chart --cov-report=html --cov-report=term-missing

# 查看HTML报告
open htmlcov/index.html

# 查看终端报告
coverage report
```

### 覆盖率检查
在 CI/CD 中集成覆盖率检查：
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest tests/chart/ --cov=vnpy.chart --cov-report=xml --cov-fail-under=95
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## ✅ 测试检查清单

### 每个模块拆分前
- [ ] 编写测试用例（红）
- [ ] 运行测试，确认失败（红）
- [ ] 实现功能（绿）
- [ ] 运行测试，确认通过（绿）
- [ ] 检查覆盖率，确保 > 95%
- [ ] 重构代码（保持测试通过）
- [ ] 再次检查覆盖率

### 集成测试
- [ ] 测试所有模块的集成
- [ ] 测试端到端场景
- [ ] 性能测试
- [ ] 回归测试

## 🎯 测试覆盖率目标

| 模块 | 目标覆盖率 | 关键方法 |
|------|----------|---------|
| widget.py | > 95% | 所有公共方法 |
| widget_position.py | > 95% | _update_entry_line_pnl |
| widget_order.py | > 95% | _process_order_update |
| widget_trigger.py | > 95% | trigger_* 方法 |
| widget_mouse.py | > 90% | mouse*Event 方法 |
| widget_chart.py | > 95% | update_* 方法 |
| widget_database.py | > 95% | 所有方法 |
| widget_cursor.py | > 95% | 所有方法 |

## 📝 注意事项

1. **Mock 使用**
   - 适度使用 Mock，不要过度 Mock
   - 对于复杂对象，使用 MagicMock
   - 对于简单对象，使用真实对象

2. **测试隔离**
   - 每个测试应该独立
   - 使用 fixture 准备测试数据
   - 清理测试后的状态

3. **测试速度**
   - 单元测试应该快速（< 1秒）
   - 集成测试可以稍慢
   - 使用 pytest markers 标记慢速测试

4. **测试维护**
   - 测试代码也要保持整洁
   - 遵循 DRY 原则
   - 使用 fixture 复用代码

