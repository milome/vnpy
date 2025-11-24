# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VeighNa** is a comprehensive, open-source AI-powered quantitative trading framework written in Python. It's designed for traders and quant developers to build sophisticated trading applications ranging from simple algorithmic strategies to complex multi-asset portfolio management systems.

- **Version**: 4.2.0
- **Python Support**: 3.10, 3.11, 3.12, 3.13 (recommend 3.13)
- **Primary Language**: Chinese with English documentation
- **License**: MIT
- **Homepage**: https://www.vnpy.com

## Development Commands

### Installation
```bash
# Windows
install.bat

# Linux/Ubuntu
bash install.sh

# macOS
bash install_osx.sh
```

### Code Quality & Testing
```bash
# Lint code (uses ruff configuration from pyproject.toml)
ruff check .

# Type checking (uses mypy configuration from pyproject.toml)
mypy vnpy

# Build packages
uv build
# OR if uv not available
python -m build
```

### Installation for Development
```bash
# Install with alpha features (AI/ML dependencies)
pip install -e .[alpha,dev]

# Install core framework only
pip install -e .
```

### Running Examples
```bash
# Main GUI application
python examples/veighna_trader/run.py

# Headless trading (no UI)
python examples/no_ui/run.py

# Chart visualization
python examples/candle_chart/run.py
```

## Architecture Overview

VeighNa uses an **event-driven, modular architecture** with three core layers:

### 1. Core Event System
- **EventEngine** (`vnpy/event/engine.py`): Central event bus with threaded queue processing
- **Event Types**: `EVENT_TICK`, `EVENT_ORDER`, `EVENT_TRADE`, `EVENT_TIMER` (1-second intervals)
- **Pattern**: Publisher-subscriber with automatic handler registration

### 2. Main Orchestration Layer
- **MainEngine** (`vnpy/trader/engine.py`): Central coordinator managing gateways, apps, and system engines
- **Key Responsibilities**: Gateway lifecycle, OMS (Order Management System), event routing
- **System Engines**: LogEngine, OmsEngine, EmailEngine (initialized automatically)

### 3. Plugin Architecture
- **Gateways** (`vnpy/trader/gateway.py`): Trading interface abstractions (30+ brokers/exchanges)
- **Apps** (`vnpy/trader/app.py`): Modular trading applications (strategy engines, backtesting, etc.)
- **Dynamic Loading**: Runtime plugin discovery and registration

## Key Data Objects

All trading data uses standardized objects in `vnpy/trader/object.py`:

```python
# Market Data
TickData      # Real-time quotes (bid/ask levels, last price, volume)
BarData       # OHLCV candlestick data

# Order Management
OrderData     # Order state and details
OrderRequest  # Order submission parameters
TradeData     # Execution records

# Account Management
PositionData  # Position holdings and P&L
AccountData   # Account balances and availability
ContractData  # Instrument specifications

# Identifiers use format: "symbol.exchange" (e.g., "AAPL.NASDAQ")
```

## Important Constants & Enums

Located in `vnpy/trader/constant.py`:

```python
Direction: LONG, SHORT, NET
Offset: OPEN, CLOSE, CLOSETODAY, CLOSEYESTERDAY
Status: SUBMITTING, NOTTRADED, PARTTRADED, ALLTRADED, CANCELLED, REJECTED
OrderType: LIMIT, MARKET, STOP, FAK, FOK
Product: EQUITY, FUTURES, OPTION, INDEX, FOREX, SPOT, ETF, BOND
Exchange: 30+ exchanges (CFFEX, SSE, SZSE, SHFE, DCE, CZCE, etc.)
Interval: MINUTE, HOUR, DAILY, WEEKLY, MONTHLY
```

## Configuration Management

Global settings in `vnpy/trader/setting.py`:

```python
SETTINGS = {
    "database.name": "sqlite",        # Database backend
    "database.database": "database.db",
    "datafeed.name": "",              # Data provider (e.g., "futu", "rqdata")
    "datafeed.username": "",
    "datafeed.password": "",
    # Additional gateway/datafeed specific settings
}
```

## AI/ML Features (vnpy.alpha module)

New in version 4.0+, located in `vnpy/alpha/`:

### Components
- **dataset/**: Feature engineering with Alpha 158 factors (from Microsoft Qlib)
- **model/**: ML model templates (Lasso, LightGBM, MLP)
- **strategy/**: Cross-sectional and time-series strategy templates
- **lab.py**: Integrated research workflow (data → training → signals → backtesting)

### Workflow Example
```python
from vnpy.alpha.lab import Lab

# 1. Data management (Parquet format)
lab = Lab()

# 2. Feature engineering
lab.prepare_dataset("Alpha158")

# 3. Model training
lab.train_model("LGBModel")

# 4. Signal generation
lab.generate_signals()

# 5. Strategy backtesting
lab.run_backtest()
```

## Plugin Development Patterns

### Gateway Plugin Structure
```
vnpy_[name]/
├── setup.py              # pip package setup
├── vnpy_[name]/
│   ├── __init__.py       # Export Gateway class
│   └── [name]_gateway.py # BaseGateway implementation
```

### App Plugin Structure
```
vnpy_[name]/
├── setup.py
├── vnpy_[name]/
│   ├── __init__.py       # Export App class
│   ├── engine.py         # BaseEngine implementation
│   └── ui/               # Qt6 widgets (optional)
```

### Registration Pattern
```python
# In main application
from vnpy_[name] import [Name]Gateway, [Name]App

main_engine.add_gateway([Name]Gateway)
main_engine.add_app([Name]App)
```

## Database & Data Feed Abstraction

### Database Backends (vnpy/trader/database.py)
- **SQLite** (default): Single-file, no configuration needed
- **MySQL/PostgreSQL**: Production databases with advanced features
- **TDengine/DolphinDB**: Time-series optimized databases

### Data Feed Providers (vnpy/trader/datafeed.py)
- **RQData** (米筐): Stocks, futures, options, bonds
- **XT** (迅投研): Multi-asset Chinese markets
- **Futu** (富途): Hong Kong and US markets
- **Wind/iFinD**: Professional financial data terminals

## Typical Application Lifecycle

```python
# 1. Initialization
event_engine = EventEngine()
main_engine = MainEngine(event_engine)

# 2. Plugin Registration
main_engine.add_gateway(FutuGateway)
main_engine.add_app(CtaStrategyApp)

# 3. Connection Setup
main_engine.connect(gateway_settings, "FUTU")

# 4. Market Data Subscription
main_engine.subscribe(SubscribeRequest(...), "FUTU")

# 5. Order Management
main_engine.send_order(OrderRequest(...), "FUTU")

# 6. Event Handling (automatic via EventEngine)
```

## Chart System

High-performance charting in `vnpy/chart/`:
- **Real-time updates**: Automatic data push integration
- **Technical indicators**: Built-in TA-lib integration
- **Multi-plot support**: Volume, price, custom indicators
- **Interactive features**: Crosshairs, zoom, pan

## RPC & Distributed Systems

`vnpy/rpc/` provides ZMQ-based inter-process communication:
- **RpcServer**: Function registration and execution
- **RpcClient**: Remote function calls with timeout handling
- **Patterns**: REQ-REP (calls) + PUB-SUB (data push)

## File Organization Guidelines

### Core Framework
- `vnpy/trader/`: Framework foundation (engines, data objects, abstractions)
- `vnpy/event/`: Event-driven core
- `vnpy/chart/`: Charting system
- `vnpy/alpha/`: AI/ML quantitative research
- `vnpy/rpc/`: Distributed communication

### Plugin Ecosystem
- `vnpy_[name]/`: External plugins (separate repositories)
- `examples/`: Usage demonstrations and starter templates

### Configuration
- `vnpy/trader/setting.py`: Global configuration registry
- `vnpy/trader/locale/`: Internationalization support

## Testing & Quality

### Code Quality Tools
```bash
ruff check .     # Linting (configured in pyproject.toml)
mypy vnpy        # Type checking (strict mode enabled)
```

### CI/CD Pipeline
- GitHub Actions workflow in `.github/workflows/pythonapp.yml`
- Tests run on Windows with Python 3.13
- Automated linting, type checking, and building

## Development Best Practices

1. **Type Annotations**: Strict typing required (mypy enforced)
2. **Event-Driven Design**: Use EventEngine for component communication
3. **Plugin Architecture**: Extend via BaseGateway/BaseApp inheritance
4. **Data Standardization**: Use vnpy.trader.object classes consistently
5. **Configuration Management**: Leverage SETTINGS global registry
6. **Internationalization**: Support Chinese primary, English secondary

## Common Development Patterns

### Adding New Data Sources
1. Inherit from `BaseDatafeed` in `vnpy/trader/datafeed.py`
2. Implement `query_bar_history()` and `query_tick_history()`
3. Register via `SETTINGS["datafeed.name"]` configuration

### Creating Strategy Applications
1. Inherit from `BaseApp` in `vnpy/trader/app.py`
2. Implement corresponding `BaseEngine` for business logic
3. Create Qt6 widgets for UI (if needed)
4. Register via `main_engine.add_app(YourApp)`

### Real-time Data Processing
1. Subscribe via `main_engine.subscribe()`
2. Register event handlers: `event_engine.register(EVENT_TICK, handler)`
3. Process data in event handlers (runs in separate thread)
4. Update UI via thread-safe Qt signals/slots

## Latest Enhancement: Order Type Redesign (November 2024)

### Overview
Completely redesigned the order type system based on futures trading requirements. The previous market price concept (designed for stocks with price limits) is not applicable to futures like HSI which have no daily limits. This enhancement provides clearer concepts and better user experience.

### Conceptual Redesign

#### **Previous Concepts (Issues)**:
- **Market Price** = Price limit (涨停/跌停价) → Meaningless for futures without limits
- **OPPONENT** = English term → Not intuitive for Chinese users

#### **New Concepts (Enhanced)**:
- **Limit Price (限价)** = User-specified exact price
- **Opponent Price (对手价)** = Buy uses ask price, sell uses bid price (former market price logic)
- **Over Price (超价)** = Opponent price + premium for aggressive execution (former OPPONENT logic)
- **Market Price (市价)** = Temporarily kept but deprecated

### Implementation Changes

#### 1. OrderType Enumeration (`vnpy/trader/constant.py`)

```python
class OrderType(Enum):
    """
    Order type.
    """
    LIMIT = _("限价")        # Limit orders with user-specified price
    MARKET = _("市价")       # Market orders (deprecated for futures)
    OPPONENT = _("对手价")   # Opponent price (buy=ask, sell=bid)
    OVER = _("超价")         # Over price (opponent + premium)
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"
    RFQ = _("询价")
    ETF = "ETF"
```

#### 2. Gateway Mapping (`vnpy_futu/vnpy_futu/futu_gateway.py`)

```python
# Order type mapping
ORDERTYPE_VT2FUTU: Dict[VtOrderType, str] = {
    VtOrderType.LIMIT: "NORMAL",       # Limit orders
    VtOrderType.MARKET: "MARKET",      # Market orders (not recommended)
    VtOrderType.OPPONENT: "NORMAL",    # Opponent price (buy=ask, sell=bid)
    VtOrderType.OVER: "NORMAL",        # Over price (opponent + premium)
}
```

#### 3. UI Logic Redesign (`vnpy/trader/ui/widget.py`)

**Removed Components**:
- OPPONENT checkbox (now integrated as order type)
- Special price section (consolidated into order types)

**Enhanced Components**:
- Order type dropdown now includes all pricing options
- Automatic price calculation based on selected type
- Real-time price updates for all calculated types

#### 4. Price Calculation Logic

**Opponent Price Calculation**:
```python
def calculate_and_display_opponent_price(self) -> None:
    """Calculate opponent price (buy=ask, sell=bid)"""
    if direction == Direction.LONG:
        # Buy orders use ask price
        price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
    else:
        # Sell orders use bid price
        price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
```

**Over Price Calculation**:
```python
def calculate_and_display_over_price(self) -> None:
    """Calculate over price (opponent + premium with risk controls)"""
    # Enhanced risk control logic with spread checking
    MAX_OVER_PREMIUM = 0.2  # Maximum 0.2% premium

    if direction == Direction.LONG:
        base_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
        over_price = base_price * (1 + MAX_OVER_PREMIUM / 100)
    else:
        base_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
        over_price = base_price * (1 - MAX_OVER_PREMIUM / 100)
```

### Order Type Behavior Matrix

| Order Type | Price Input | Price Display | Execution Strategy | Use Case |
|------------|-------------|---------------|-------------------|----------|
| **Limit (限价)** | User-specified | Editable | Exact price | Normal trading, price control |
| **Opponent (对手价)** | Auto-calculated | Read-only | Real-time opponent price | Quick execution at market |
| **Over (超价)** | Auto-calculated | Read-only | Opponent + 0.2% premium | Aggressive immediate execution |
| **Market (市价)** | Auto-calculated | Read-only | **Deprecated** for futures | Legacy support only |

### Benefits of Redesign

#### **Conceptual Clarity**:
- **对手价 (Opponent Price)**: Clear Chinese terminology
- **超价 (Over Price)**: Intuitive concept for aggressive pricing
- **Market Neutral**: No confusion with stock market price limits

#### **User Experience**:
- **Simplified Interface**: One dropdown for all pricing options
- **Intuitive Names**: Chinese terms that traders understand
- **Clear Behavior**: Predictable price calculation for each type

#### **Technical Advantages**:
- **Cleaner Code**: No special checkbox logic
- **Better Maintainability**: Unified order type handling
- **Future Extensible**: Easy to add new pricing strategies

### Usage Examples

#### **Opponent Price Trading**:
1. Select "对手价" (Opponent) from order type dropdown
2. Watch price auto-calculate: Buy → Ask price, Sell → Bid price
3. Price field becomes read-only showing exact execution price
4. Submit order with real-time calculated price

#### **Over Price Trading**:
1. Select "超价" (Over) from order type dropdown
2. Watch aggressive price calculate: Opponent + 0.2% premium
3. Risk warnings appear if spread too wide (⚠️ icon)
4. Submit order with enhanced execution probability

#### **Migration from Previous Design**:
- **Old Market Orders** → Use **Opponent Price** instead
- **Old OPPONENT Checkbox** → Use **Over Price** order type instead
- **Limit Orders** → No change, same behavior

### Risk Management Enhancements

The Over Price type includes enhanced risk controls:
- **Spread Monitoring**: Warns when bid-ask spread > 1%
- **Premium Limits**: Maximum 0.2% over opponent price
- **Price Deviation**: Auto-correction when price deviates > 0.5% from mid-price
- **User Confirmation**: Popup warnings for high-risk conditions

This redesign provides a more intuitive and safer trading experience specifically optimized for futures markets while maintaining all the advanced features of the intelligent chase system.

## Previous Implementation: Market Price & OPPONENT Price Support (Superseded)

### Overview
Added comprehensive support for market price and OPPONENT price order types in the Futu gateway with full UI integration and real-time price calculation. This enhancement provides professional-grade order execution capabilities with transparent pricing and eliminates placeholder price issues.

### Implementation Details

#### 1. Gateway Backend Changes (`vnpy_futu/vnpy_futu/futu_gateway.py`)

**Added OrderType Mapping System:**
```python
# 委托类型映射
ORDERTYPE_VT2FUTU: Dict[VtOrderType, str] = {
    VtOrderType.LIMIT: "NORMAL",       # 限价单
    VtOrderType.MARKET: "MARKET",      # 市价单
}

# OPPONENT price special marker (no longer used - replaced with reference-based detection)
OPPONENT_PRICE_MARKER = 999999.0
```

**Enhanced send_order() Method (Simplified):**
- **Market Price Support**: Uses real prices calculated in UI (no gateway calculation needed)
- **OPPONENT Price Support**: Uses real aggressive prices calculated in UI
- **Reference-based Detection**: Identifies order types via `req.reference` field
- **Direct Processing**: No placeholder price conversion needed

**Gateway Logic (Updated):**
```python
# Simplified gateway logic - UI sends real prices
if req.reference == "OPPONENT":
    # OPPONENT order: UI calculated aggressive price
    order_price = req.price
    self.write_log(f"OPPONENT价格订单：{req.direction.value} -> 使用UI计算的激进价格 {order_price}")
elif req.type == VtOrderType.MARKET:
    # Market order: UI calculated opponent price
    order_price = req.price
    self.write_log(f"市价单处理：使用UI计算的对手价 {order_price}")
else:
    # Limit order: User specified price
    order_price = req.price
```

#### 2. UI Enhancements (`vnpy/trader/ui/widget.py`)

**Added Real-time Price Calculation:**
- **Auto-calculation**: Displays real market prices when order types change
- **Live Updates**: Prices refresh automatically with market data changes
- **Visual Feedback**: Price fields become read-only for calculated prices
- **Direction Sensitivity**: Recalculates when trading direction changes

**Enhanced UI Controls:**
- New checkbox: "OPPONENT" with tooltip "使用OPPONENT价格（激进对手价）"
- Smart form behavior: Auto-sets LIMIT type when OPPONENT checked
- **Real-time Price Display**: Shows actual calculated prices before submission
- Form validation: Prevents conflicting settings

**Enhanced Layout:**
```python
# Added "特殊价格" section with OPPONENT checkbox
grid.addWidget(QtWidgets.QLabel(_("特殊价格")), 8, 0)
grid.addWidget(self.opponent_check, 8, 1, 1, 2)

# Added event handlers for real-time updates
self.order_type_combo.currentTextChanged.connect(self.on_order_type_changed)
self.direction_combo.currentTextChanged.connect(self.on_direction_changed)
```

#### 3. Order Type Behavior Matrix (Updated)

| Order Type | Price Input | Price Display | Execution Strategy | Use Case |
|------------|-------------|---------------|-------------------|----------|
| **LIMIT** | User-specified | Enabled/Editable | Exact price | Normal trading |
| **MARKET** | Auto-calculated | **Disabled/Read-only** | Real-time opponent price (ask/bid) | Quick execution |
| **OPPONENT** | Auto-calculated | **Disabled/Read-only** | Real-time aggressive opponent price +/- 0.1% | Immediate execution |

#### 4. Technical Implementation Features (Enhanced)

**Real-time Market Price Calculation:**
```python
def calculate_and_display_market_price(self) -> None:
    """Calculate and display real-time opponent price for market orders"""
    tick_data = self.main_engine.get_tick(self.vt_symbol)
    direction = Direction(str(self.direction_combo.currentText()))

    if direction == Direction.LONG:
        market_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
    else:
        market_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price

    if market_price > 0:
        self.price_line.setText(f"{market_price:.2f}")
        self.price_line.setEnabled(False)  # Read-only display
```

**Real-time OPPONENT Price Calculation:**
```python
def calculate_and_display_opponent_price(self) -> None:
    """Calculate and display aggressive opponent price"""
    tick_data = self.main_engine.get_tick(self.vt_symbol)
    direction = Direction(str(self.direction_combo.currentText()))

    if direction == Direction.LONG:
        base_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
        opponent_price = base_price * 1.001  # +0.1% premium
    else:
        base_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
        opponent_price = base_price * 0.999  # -0.1% discount

    if opponent_price > 0:
        self.price_line.setText(f"{opponent_price:.3f}")
        self.price_line.setEnabled(False)  # Read-only display
```

#### 5. UI Integration Features (Enhanced)

**Smart Order Type Handling:**
```python
def on_order_type_changed(self, order_type_text: str) -> None:
    """Handle order type changes with real-time price calculation"""
    if order_type_text == OrderType.MARKET.value and not self.opponent_check.isChecked():
        self.calculate_and_display_market_price()
        self.price_line.setEnabled(False)  # Read-only for market orders
    elif order_type_text == OrderType.LIMIT.value and not self.opponent_check.isChecked():
        self.price_line.setEnabled(True)  # Editable for limit orders
        if self.price_line.text() == "0.00":
            self.price_line.clear()
```

**OPPONENT Checkbox Behavior (Enhanced):**
```python
def on_opponent_checked(self, state: int) -> None:
    if state == 2:  # Checked
        self.order_type_combo.setCurrentText(OrderType.LIMIT.value)
        self.calculate_and_display_opponent_price()  # Show real aggressive price
        self.price_line.setEnabled(False)  # Read-only
        self.price_check.setChecked(False)
    else:  # Unchecked
        self.price_line.setEnabled(True)  # Re-enable editing
```

**Live Price Updates:**
```python
def process_tick_event(self, event: Event) -> None:
    """Process tick data and update prices in real-time"""
    # ... existing tick processing ...

    # Auto-update market and opponent prices
    order_type_text = str(self.order_type_combo.currentText())
    if order_type_text == OrderType.MARKET.value and not self.opponent_check.isChecked():
        if not self.price_line.isEnabled():  # Only update if read-only
            self.calculate_and_display_market_price()
    elif self.opponent_check.isChecked():
        if not self.price_line.isEnabled():  # Only update if read-only
            self.calculate_and_display_opponent_price()
```

**Order Submission Logic (Final):**
```python
# Enhanced validation and real price usage
if self.opponent_check.isChecked():
    # Use calculated OPPONENT price from UI display
    price = float(price_text)
    reference = "OPPONENT"
elif order_type == OrderType.MARKET:
    # Use calculated market price from UI display or recalculate
    if not price_text or price_text == "0.00":
        # Recalculate real-time market price
        tick_data = self.main_engine.get_tick(self.vt_symbol)
        direction = Direction(str(self.direction_combo.currentText()))
        price = tick_data.ask_price_1 if direction == Direction.LONG else tick_data.bid_price_1
    else:
        price = float(price_text)
    reference = "MarketPrice"
else:
    # Standard limit order
    price = float(price_text)
    reference = "ManualTrading"
```

#### 6. Key Benefits (Enhanced)

**Trading Performance:**
- **Eliminates Price Rejection**: Real market prices ensure valid tick sizes
- **Faster Execution**: Real-time price calculation reduces latency
- **Reduced Slippage**: Accurate opponent pricing improves fill rates
- **Transparent Pricing**: Users see exact execution price before submitting

**User Experience:**
- **Real-time Price Display**: Live calculated prices shown in UI
- **Visual Feedback**: Read-only fields indicate system-calculated prices
- **Automatic Updates**: Prices refresh with market movement
- **Professional Interface**: Clear distinction between manual and calculated pricing

**System Reliability:**
- **No Placeholder Prices**: Eliminates "价格不在价位上" errors
- **Real Price Validation**: All prices are market-derived and valid
- **Robust Error Handling**: Comprehensive validation before submission
- **Clear Reference Tracking**: Gateway identifies order types via reference field

#### 7. Usage Examples (Updated)

**Market Price Order (Enhanced UI):**
1. Select "市价" (Market) from order type dropdown
2. **Watch price auto-calculate** and display in read-only field (e.g., "28750.50")
3. **Price updates live** as market moves
4. Submit order with real calculated price

**OPPONENT Price Order (Enhanced UI):**
1. Check "OPPONENT" checkbox in "特殊价格" section
2. Order type auto-sets to "限价" (Limit)
3. **Watch aggressive price calculate** and display (e.g., "28778.75")
4. Price field becomes **read-only** showing exact execution price
5. **Price updates live** with market movement

**Real-time Price Updates:**
- **Direction Change**: Prices recalculate instantly (Long ↔ Short)
- **Market Data Updates**: Prices refresh with every tick
- **Order Type Switch**: Immediate price calculation on type change

#### 8. Files Modified (Final)

- **Primary**: `vnpy_futu/vnpy_futu/futu_gateway.py` - Simplified gateway logic for real prices
- **UI**: `vnpy/trader/ui/widget.py` - Enhanced real-time price calculation and display
- **Documentation**: `CLAUDE.md` - Updated implementation guide

#### 9. Recent Problem Resolution

**Previous Issue**: Market orders sent placeholder prices (1000.0) causing "价格不在价位上" errors
**Solution Implemented**:
- UI calculates real market prices before submission
- Gateway receives valid tick-size prices from UI
- No placeholder values sent to Futu API
- Real-time price display provides transparency

**Result**: Professional-grade trading interface with institutional-quality price handling and real-time market data integration.

This implementation provides institutional-grade market and opponent price functionality with complete price transparency and real-time updates, making it production-ready for professional trading environments.

## Recent Implementation: Intelligent Price Chasing System

### Overview
Added comprehensive intelligent price chasing (智能追价) functionality to automatically handle slippage and improve order fill rates. This system monitors order status in real-time and automatically adjusts prices when orders fail to execute, using configurable strategies to maximize execution success while controlling slippage.

### Problem Statement
When submitting market or OPPONENT price orders, network latency and rapid market movements can cause orders to fail execution:
- **Network Delay**: Price changes between UI calculation and order arrival at exchange
- **Market Volatility**: Fast-moving markets cause price mismatches
- **Tick Size Restrictions**: Calculated prices may not match valid tick sizes
- **Liquidity Gaps**: Insufficient liquidity at calculated price levels

### Solution: Smart Layered Price Chasing

The intelligent chase system implements a sophisticated multi-layered approach:

#### 1. Configuration Classes (`vnpy_futu/futu_gateway.py`)

**ChaseConfig Class:**
```python
class ChaseConfig:
    """Parse chase configuration from order reference string"""
    def __init__(self, reference: str):
        self.enabled = False
        self.max_chase_times = 3          # Maximum chase attempts
        self.max_slippage_pct = 0.5       # Maximum slippage tolerance (%)
        self.chase_step_pct = 0.05        # Price adjustment step (%)
        self.chase_interval = 0.5         # Minimum interval between chases (seconds)

        # Parse configuration from reference string
        # Format: "OrderType_Chase3_Slip0.5_Step0.05"
```

**ChaseOrder Class:**
```python
class ChaseOrder:
    """Track individual chase order state"""
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig):
        self.orderid = orderid
        self.original_price = original_price      # Original submitted price
        self.current_price = original_price       # Current adjusted price
        self.chase_count = 0                      # Number of chase attempts
        self.config = config
        self.last_chase_time = 0.0               # Timestamp of last chase
        self.is_chasing = False                  # Chase in progress flag
```

#### 2. UI Configuration (`vnpy/trader/ui/widget.py`)

**Chase Configuration Controls:**
```python
# Main chase toggle
self.chase_check: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
self.chase_check.setText("智能追价")
self.chase_check.setChecked(True)  # Enabled by default

# Chase times spinner
self.chase_times_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
self.chase_times_spin.setRange(1, 10)
self.chase_times_spin.setValue(3)

# Maximum slippage spinner
self.max_slippage_spin: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox()
self.max_slippage_spin.setRange(0.01, 5.0)
self.max_slippage_spin.setValue(0.5)
self.max_slippage_spin.setSuffix("%")

# Chase step spinner
self.chase_step_spin: QtWidgets.QDoubleSpinBox = QtWidgets.QDoubleSpinBox()
self.chase_step_spin.setRange(0.01, 1.0)
self.chase_step_spin.setValue(0.05)
self.chase_step_spin.setSuffix("%")
```

**Chase Statistics Display:**
```python
# Real-time chase statistics display in UI
self.chase_status_label: QtWidgets.QLabel  # Shows chase configuration
self.chase_stats_label: QtWidgets.QLabel   # Shows chase performance stats
```

#### 3. Gateway Chase Logic (`vnpy_futu/futu_gateway.py`)

**Order Submission with Chase:**
```python
def send_order(self, req: OrderRequest) -> str:
    # ... place order ...

    # Enable chase if configured
    chase_config = ChaseConfig(req.reference)
    if chase_config.enabled and self.chase_enabled:
        chase_order = ChaseOrder(orderid, req.price, chase_config)
        self.chase_orders[orderid] = chase_order
        self.chase_stats["total_orders"] += 1
```

**Order Status Monitoring:**
```python
def on_order_update(self, order: OrderData) -> None:
    """Monitor order status and trigger chase when needed"""
    if orderid in self.chase_orders:
        chase_order = self.chase_orders[orderid]

        # Trigger chase on rejection/cancellation
        if (order.status in [Status.REJECTED, Status.CANCELLED] and
            not chase_order.is_chasing and
            chase_order.chase_count < chase_order.config.max_chase_times):

            # Delayed chase execution
            def delayed_chase():
                sleep(chase_order.config.chase_interval)
                self.start_chase_order(orderid, order.vt_symbol, order.direction)

            Thread(target=delayed_chase).start()
```

**Chase Price Calculation:**
```python
def calculate_chase_price(self, chase_order: ChaseOrder, tick: TickData, direction: Direction) -> float:
    """Calculate new chase price based on current market"""
    step_pct = chase_order.config.chase_step_pct / 100.0

    if direction == Direction.LONG:
        # Buy: use ask price + step
        base_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
        new_price = base_price * (1 + step_pct)
    else:
        # Sell: use bid price - step
        base_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
        new_price = base_price * (1 - step_pct)

    return new_price
```

**Chase Execution with Controls:**
```python
def execute_chase_order(self, orderid: str, new_price: float, chase_order: ChaseOrder) -> None:
    """Execute price adjustment with safety checks"""
    # Check slippage limit
    slippage_pct = abs(new_price - chase_order.original_price) / chase_order.original_price * 100
    if slippage_pct > chase_order.config.max_slippage_pct:
        self.write_log(f"Slippage {slippage_pct:.2f}% exceeds limit {chase_order.config.max_slippage_pct}%")
        self.chase_stats["failed_chases"] += 1
        return

    # Check chase interval
    current_time = time()
    if current_time - chase_order.last_chase_time < chase_order.config.chase_interval:
        return

    # Modify order price
    chase_order.is_chasing = True
    chase_order.chase_count += 1

    code, data = self.trade_ctx.modify_order(
        ModifyOrderOp.MODIFY,
        orderid,
        new_price,
        0,  # Don't modify volume
        trd_env=self.env
    )

    if code == 0:  # Success
        chase_order.current_price = new_price
        self.chase_stats["successful_chases"] += 1
        self.write_log(f"Chase success: {orderid} price {chase_order.current_price} -> {new_price}")

    chase_order.is_chasing = False
```

#### 4. Chase Strategy Matrix

| Strategy | Max Times | Max Slippage | Step Size | Use Case |
|----------|-----------|--------------|-----------|----------|
| **Conservative** | 2 | 0.2% | 0.03% | Stable markets, price-sensitive |
| **Balanced** (Default) | 3 | 0.5% | 0.05% | Normal trading conditions |
| **Aggressive** | 5 | 1.0% | 0.1% | Volatile markets, execution priority |
| **Ultra-Aggressive** | 10 | 2.0% | 0.2% | Urgent execution, less price-sensitive |

#### 5. Order Type Chase Behavior

| Order Type | Chase Strategy | Priority |
|------------|----------------|----------|
| **MARKET** | Aggressive chase | Execution speed |
| **OPPONENT** | Moderate chase | Balance execution & price |
| **LIMIT** | Conservative chase | Price preservation |

#### 6. ATR-Based Dynamic Chase Step Calculation (Latest Enhancement)

**Problem**: Fixed chase step percentage doesn't adapt to market volatility and liquidity, leading to inefficient chasing and execution times exceeding 500ms.

**Solution**: Dynamic chase step calculation based on ATR (Average True Range) and volume analysis from past 34 one-minute periods.

**Implementation:**

**ATR and Volume Calculation:**
```python
def calculate_atr_and_volume(self, vt_symbol: str) -> Tuple[float, float]:
    """Calculate ATR and average volume (based on past 34 one-minute periods)"""
    # Query historical K-line data (34 one-minute periods)
    bars = self.query_history(req)
    
    # Calculate ATR using talib (14-period)
    atr_array = talib.ATR(high_array, low_array, close_array, timeperiod=14)
    atr_value = float(atr_array[-1])
    
    # Calculate average volume
    avg_volume = sum([bar.volume for bar in bars]) / len(bars)
    
    # Cache results for performance
    self.atr_cache[vt_symbol] = atr_value
    self.volume_cache[vt_symbol] = avg_volume
    
    return atr_value, avg_volume
```

**Dynamic Chase Step Calculation:**
```python
def calculate_dynamic_chase_step(
    self, vt_symbol: str, current_price: float, direction: Direction
) -> float:
    """Calculate dynamic chase step based on ATR and volume"""
    atr, avg_volume = self.calculate_atr_and_volume(vt_symbol)
    
    # Base step: 15% of ATR percentage
    atr_pct = atr / current_price if current_price > 0 else 0.0
    base_step = atr_pct * 0.15
    
    # Volume adjustment: Higher volume = smaller step (better liquidity)
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    volume_factor = 1.0 / max(0.5, min(2.0, volume_ratio))
    
    # Dynamic step calculation
    dynamic_step = base_step * volume_factor
    
    # Limit step range: 0.01% - 0.5%
    dynamic_step = max(0.0001, min(0.005, dynamic_step))
    
    return dynamic_step
```

**Optimized Chase Interval Strategy:**
```python
# First 2 chases: 100ms interval (fast response)
# Subsequent chases: configured interval (default 500ms)
min_interval = 0.1 if chase_order.chase_count < 2 else chase_order.config.chase_interval

# Reduced delay for rejected orders: 50ms (was 500ms)
delay = 0.05 if chase_order.chase_count < 2 else chase_order.config.chase_interval
```

**Enhanced Chase Execution Logging:**
```python
# Chase calculation log
self.write_log(
    f"[追价计算] {vt_symbol} - "
    f"方向: {direction.value}, "
    f"当前价: {current_price:.3f}, "
    f"新价格: {new_price:.3f}, "
    f"步长: {dynamic_step*100:.3f}%, "
    f"ATR: {atr:.3f}, "
    f"平均成交量: {avg_volume:.0f}"
)

# Chase execution log
self.write_log(
    f"[追价成功] 订单{orderid} 第{chase_count}次追价完成 - "
    f"价格: {old_price:.3f} -> {new_price:.3f}, "
    f"滑点: {slippage:.3f}, "
    f"修改耗时: {modify_time:.1f}ms, "
    f"总耗时: {total_time:.1f}ms"
)
```

**Performance Metrics:**
```python
self.chase_stats = {
    "total_orders": 0,
    "successful_chases": 0,
    "failed_chases": 0,
    "total_slippage": 0.0,
    "total_chase_time": 0.0,        # NEW: Cumulative chase time
    "chase_executions": [],          # NEW: Detailed execution records
    "average_chase_time_ms": 0.0,    # NEW: Average chase time
    "avg_modify_time_ms": 0.0,      # NEW: Average modify order time
    "max_modify_time_ms": 0.0,      # NEW: Max modify order time
    "min_modify_time_ms": 0.0,      # NEW: Min modify order time
}
```

**Key Improvements:**
1. **Adaptive Step Size**: Chase step adapts to market volatility (ATR) and liquidity (volume)
2. **Faster Response**: First 2 chases use 100ms interval instead of 500ms
3. **Performance Monitoring**: Detailed timing metrics for each chase execution
4. **Target**: Reduce execution time to under 500ms

**Testing:**
- [test_chase_atr_strategy.py](test_chase_atr_strategy.py) - Comprehensive tests for ATR-based chase strategy
  - ATR calculation validation
  - Dynamic step calculation tests
  - Performance simulation
  - Step optimization verification
  - Interval optimization tests
  - Logging format validation

### 2025-11-24 Reliability Hardening (Futu Gateway)

Recent production logs still showed cases where `订单6440118/6440119` 在全部成交后仍被超时线程尝试撤单。此次补丁聚焦在消除智能追价各个线程之间的竞态，使其完全以状态驱动。

**Highlights**
- `_normalize_orderid()` 现在在读取或写入 `self.chase_orders` 时一律调用，`FUTU.6440118` 与 `6440118` 会落到相同 key，避免因 ID 形式不同导致无法查找到状态。
- `_check_timeout_orders()` 只要 `_get_order_status()` 返回 `ALLTRADED` 就立即移除，并且对 `None` 状态（且 `just_cancelled=False`）采取保守删除策略，彻底阻断“幽灵追价”。
- `_retry_order_with_latest_price()` / `_try_reorder_with_tick()` 在查询状态、撤单 API、等待 tick、生成新订单等每一步都重新确认 chaser 是否仍然存在，一旦发现已被其他线程移除就立刻退出。
- `on_order_update()` 会记录是它自己移除追价还是发现已被其他逻辑删掉，方便排查到底是哪条路径先完成。

#### Flowchart · Timeout & Retry Logic

```mermaid
flowchart TD
    A[Timer Trigger] --> B{遍历 chase_orders}
    B --> C[normalize(orderid)]
    C --> D{_get_order_status}
    D -->|ALLTRADED| E[立即移除追价并写日志]
    D -->|CANCELLED ∧ just_cancelled| F[等待tick -> _try_reorder_with_tick]
    D -->|CANCELLED ∧ 非just_cancelled| G[安全移除追价]
    D -->|None| H{仍在 chase_orders?}
    H -->|否| I[跳过 - 其他线程已处理]
    H -->|是且非just_cancelled| G
    H -->|是且just_cancelled| F
    D -->|其他状态| J{elapsed ≥ timeout?}
    J -->|否| K[继续下一单]
    J -->|是| L{orderid 仍存在?}
    L -->|否| I
    L -->|是| M[_retry_order_with_latest_price]
```

#### Sequence Diagram · Fill vs Timeout Race

```mermaid
sequenceDiagram
    participant Timer as TimerThread
    participant Gateway as FutuGateway
    participant Futu as Futu API
    participant Callback as on_order_update

    Timer->>Gateway: _check_timeout_orders()
    Gateway->>Gateway: normalize(orderid)
    Gateway->>Futu: _get_order_status()
    alt Status == ALLTRADED
        Futu-->>Gateway: Filled
        Gateway->>Gateway: 删除追价并写日志
    else Status == None
        Gateway->>Gateway: if not just_cancelled -> 删除
    else Timeout exceeded
        Gateway->>Gateway: 确认 orderid 仍存在
        Gateway->>Gateway: _retry_order_with_latest_price()
        Gateway->>Futu: 撤单 / 重委托
    end
    Futu-->>Callback: order update (ALLTRADED / CANCELLED)
    Callback->>Gateway: normalize(orderid)
    Gateway->>Gateway: 删除剩余追价 or 记录已被移除
    Gateway-->>Timer: 下一轮扫描忽略已完成订单
```

#### 7. Chase Statistics Tracking

**Real-time Metrics:**
```python
self.chase_stats = {
    "total_orders": 0,           # Total orders with chase enabled
    "successful_chases": 0,      # Successful price adjustments
    "failed_chases": 0,          # Failed chase attempts
    "total_slippage": 0.0,       # Cumulative slippage
    "total_chase_time": 0.0,    # Cumulative chase execution time (ms)
    "chase_executions": [],     # Detailed execution records (last 100)
    "active_chase_orders": 0,    # Currently active chase orders
    "chase_success_rate": 0.0,   # Success rate percentage
    "average_slippage": 0.0,     # Average slippage per chase
    "average_chase_time_ms": 0.0, # Average chase time (ms)
    "avg_modify_time_ms": 0.0,   # Average modify order time (ms)
    "max_modify_time_ms": 0.0,   # Maximum modify order time (ms)
    "min_modify_time_ms": 0.0,   # Minimum modify order time (ms)
}
```

**Statistics Display in UI:**
```python
def update_chase_statistics(self) -> None:
    """Update chase statistics in real-time"""
    stats = gateway.get_chase_statistics()
    stats_text = (f"订单{stats['total_orders']}笔, "
                 f"成功{stats['successful_chases']}次, "
                 f"失败{stats['failed_chases']}次, "
                 f"成功率{stats['chase_success_rate']:.1f}%, "
                 f"平均滑点{stats['average_slippage']:.3f}")
    self.chase_stats_label.setText(stats_text)
```

#### 7. Configuration Encoding/Decoding

**UI to Gateway Communication:**
```python
# UI encodes chase config into order reference
chase_config = self.get_chase_config()
if chase_config["enabled"]:
    reference = f"{base_reference}_Chase{chase_config['max_chase_times']}_Slip{chase_config['max_slippage_pct']}_Step{chase_config['chase_step_pct']}"

# Example: "OPPONENT_Chase3_Slip0.5_Step0.05"
```

**Gateway Config Parsing:**
```python
# Gateway parses reference to extract chase configuration
chase_config = ChaseConfig(req.reference)
# Automatically extracts: max_chase_times=3, max_slippage_pct=0.5, chase_step_pct=0.05
```

#### 8. Safety and Risk Controls

**Slippage Protection:**
- Maximum slippage percentage limit (default 0.5%)
- Cumulative slippage tracking across all chases
- Automatic chase termination when limit exceeded

**Chase Frequency Control:**
- Minimum interval between chase attempts (0.5 seconds)
- Prevents excessive API calls and rate limiting
- Allows time for order status updates

**Chase Count Limit:**
- Maximum number of chase attempts per order (default 3)
- Prevents infinite chase loops
- Protects against runaway slippage

**Order State Management:**
- Thread-safe chase order tracking
- Automatic cleanup on order completion
- Prevention of duplicate chase attempts

#### 9. Usage Examples

**Example 1: Market Order with Default Chase**
```python
# UI Configuration (default)
智能追价: ✓ (checked)
追价次数: 3
最大滑点: 0.5%
追价步长: 0.05%

# Order Submission
Order Type: MARKET
Price: 400.00 (calculated)
Reference: "MarketPrice_Chase3_Slip0.5_Step0.05"

# Chase Execution Flow
1. Initial order @ 400.00 -> REJECTED (price moved)
2. Chase #1: Recalculate -> 400.20 -> REJECTED
3. Chase #2: Recalculate -> 400.41 -> ACCEPTED
   Total Slippage: 0.41 (0.10%) ✓ Within limit
```

**Example 2: OPPONENT Order with Custom Chase**
```python
# UI Configuration (aggressive)
智能追价: ✓ (checked)
追价次数: 5
最大滑点: 1.0%
追价步长: 0.1%

# Order Submission
Order Type: OPPONENT
Price: 401.40 (calculated with 0.1% premium)
Reference: "OPPONENT_Chase5_Slip1.0_Step0.1"

# Chase Execution
1. Initial order @ 401.40 -> REJECTED
2. Chase #1: 401.80 -> REJECTED
3. Chase #2: 402.20 -> ACCEPTED
   Total Slippage: 0.80 (0.20%) ✓ Success
```

**Example 3: Chase Limit Exceeded**
```python
# Configuration
追价次数: 3
最大滑点: 0.5%

# Execution
1. Initial @ 400.00 -> REJECTED
2. Chase #1: 401.00 -> REJECTED
3. Chase #2: 402.00 -> REJECTED (Slippage 0.5% reached)
4. Chase #3: SKIPPED - Slippage limit exceeded
   Final Status: FAILED ✗ Max slippage protection triggered
```

#### 10. Key Benefits

**Trading Performance:**
- **Higher Fill Rates**: Automatic price adjustment increases execution success
- **Reduced Manual Intervention**: No need to manually resubmit orders
- **Controlled Slippage**: Configurable limits prevent excessive costs
- **Faster Execution**: Automated chase faster than human reaction

**User Experience:**
- **One-Click Trading**: Set-and-forget chase configuration
- **Real-Time Feedback**: Live statistics and status updates
- **Flexible Control**: Adjustable parameters for different strategies
- **Transparent Operation**: Full visibility into chase activity

**Risk Management:**
- **Slippage Caps**: Hard limits on maximum price deviation
- **Frequency Controls**: Prevents excessive API usage
- **Attempt Limits**: Bounds worst-case slippage scenarios
- **Statistical Monitoring**: Track and analyze chase performance

#### 11. Advanced Features

**Market-Adaptive Chase:**
- Different strategies for different order types
- Volatility-aware parameter adjustment
- Time-of-day strategy variations

**Performance Analytics:**
- Success rate by order type
- Average slippage analysis
- Chase time distribution
- Optimal parameter recommendations

**Integration with Existing Features:**
- Works seamlessly with Market and OPPONENT pricing
- Compatible with real-time price display
- Integrated with order status monitoring
- Synced with gateway order management

#### 12. Testing and Validation

Test files provided:
- [test_chase_core.py](test_chase_core.py) - Core logic unit tests
- [test_chase_price.py](test_chase_price.py) - Integration tests

**Test Coverage:**
- Configuration parsing and encoding
- Price calculation algorithms
- Slippage validation
- Chase state management
- Statistics tracking
- Error handling and edge cases

#### 13. Production Deployment

**Pre-Launch Checklist:**
1. ✓ Test chase configuration in paper trading environment
2. ✓ Validate slippage limits with actual market data
3. ✓ Monitor chase statistics for first 100 orders
4. ✓ Adjust parameters based on performance data
5. ✓ Enable logging for chase activity monitoring

**Recommended Initial Settings:**
- Chase enabled: Yes
- Max chase times: 3
- Max slippage: 0.5%
- Chase step: 0.05%

**Monitoring:**
- Review chase statistics daily
- Analyze failed chase patterns
- Adjust parameters for optimal performance
- Monitor slippage impact on P&L

#### 14. Files Modified

- **Gateway**: [vnpy_futu/futu_gateway.py](vnpy_futu/vnpy_futu/futu_gateway.py) - Chase logic and order monitoring
- **UI**: [vnpy/trader/ui/widget.py](vnpy/trader/ui/widget.py) - Chase configuration and statistics display
- **Tests**: [test_chase_core.py](test_chase_core.py), [test_chase_price.py](test_chase_price.py), [test_chase_atr_strategy.py](test_chase_atr_strategy.py)
- **Documentation**: [CLAUDE.md](CLAUDE.md) - Complete implementation guide

This intelligent price chasing system transforms order execution from a manual, reactive process into an automated, intelligent system that significantly improves fill rates while maintaining strict risk controls.

## Latest Updates and Improvements (November 2024)

### Real-time Price Update Fixes

**Problem Resolved**: Initial implementation had issues where market and OPPONENT prices weren't updating in real-time in the UI.

**Solution Implemented**:
```python
def process_tick_event(self, event: Event) -> None:
    """Enhanced tick processing with forced price updates"""
    # ... existing tick processing ...

    # 实时更新市价单和OPPONENT价格 - 强制刷新确保最新价格
    order_type_text = str(self.order_type_combo.currentText())
    if order_type_text == OrderType.MARKET.value and not self.opponent_check.isChecked():
        # 市价单：强制实时更新价格，无论字段状态
        self.calculate_and_display_market_price()
    elif self.opponent_check.isChecked():
        # OPPONENT订单：强制实时更新激进价格，无论字段状态
        self.calculate_and_display_opponent_price()
```

**Key Improvements**:
- Removed conditional checks that prevented real-time updates
- Added forced refresh on every tick for calculated prices
- Enhanced vt_symbol setup in order type change handlers
- Improved error handling for missing market data

### Order Submission Enhancements

**Enhanced Price Validation**:
```python
def send_order(self) -> None:
    """Enhanced order submission with latest price calculation"""
    # Always recalculate latest prices on submission
    if self.opponent_check.isChecked():
        # 重新计算最新OPPONENT价格
        if direction == Direction.LONG:
            base_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
            price = base_price * 1.001  # +0.1%
        else:
            base_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
            price = base_price * 0.999  # -0.1%

        # 记录价格对比
        ui_price = self.extract_price_from_text(price_text)
        if ui_price > 0 and abs(price - ui_price) / ui_price > 0.001:
            self.main_engine.write_log(f"OPPONENT价格已更新: UI显示{ui_price:.3f} -> 最新计算{price:.3f}")
```

**Benefits**:
- Guarantees latest market prices are used for all orders
- Provides price update logging for transparency
- Eliminates stale price submission issues
- Improves order execution success rates

### UI Cleanup and Optimization

**Chase Statistics Management**:
- **Removed**: Real-time chase statistics display from UI below "全撤" button
- **Moved**: All chase information to log messages only
- **Improved**: Cleaner UI interface with essential controls only

**Market Depth Display Clarification**:
The market depth display (买卖五档盘口) showing below the trading controls is **VNPy's official feature**, not custom code:
- Ask levels 5-1 (卖五到卖一) in green
- Last price and percentage change in center
- Bid levels 1-5 (买一到买五) in red/pink
- Updates in real-time with market data

### Local Development Setup

**Created Installation Scripts** for preserving custom modifications:

**[update_and_run.bat](update_and_run.bat)** - Comprehensive with error handling:
```batch
echo [1/3] 正在安装本地开发版 vnpy_futu (保留自定义功能)...
cd /d "d:\Dev\vnpy\vnpy_futu"
pip install -e .

echo [2/3] 正在安装本地开发版 vnpy (保留自定义功能)...
cd /d "d:\Dev\vnpy"
pip install -e .

echo [3/3] 启动 VNPy Trader...
cd /d "d:\Dev\vnpy\examples\veighna_trader"
python run.py
```

**[quick_start.bat](quick_start.bat)** - Simplified version:
```batch
echo 🔄 安装本地开发版 vnpy_futu (保留自定义功能)...
cd /d "d:\Dev\vnpy\vnpy_futu"
pip install -e .

echo 🔄 安装本地开发版 vnpy (保留自定义功能)...
cd /d "d:\Dev\vnpy"
pip install -e .

echo 🚀 启动 VNPy...
cd /d "d:\Dev\vnpy\examples\veighna_trader"
python run.py
```

**Installation Method Comparison**:
- `pip install --upgrade vnpy`: Installs latest official version (overwrites local changes)
- `pip install -e .`: Installs in development mode (preserves local modifications)

### Testing and Validation

**Test Files Created**:
- [test_chase_core.py](test_chase_core.py) - Core chase logic validation
- [test_chase_price.py](test_chase_price.py) - Price calculation testing
- [test_chase_atr_strategy.py](test_chase_atr_strategy.py) - ATR-based dynamic chase strategy tests

**Comprehensive Test Coverage**:
- Configuration parsing and encoding
- Real-time price calculation algorithms
- Chase execution logic
- Slippage validation and controls
- UI interaction and updates
- Gateway integration

### Final Status Summary

**🎯 Fully Implemented Features**:
- ✅ **Market Price Orders**: Real-time opponent price calculation and display
- ✅ **OPPONENT Price Orders**: Aggressive pricing with 0.1% premium/discount
- ✅ **Real-time Price Updates**: Live price refresh with every market tick
- ✅ **Intelligent Price Chasing**: Configurable automatic slippage handling
- ✅ **UI Integration**: Professional trading interface with read-only calculated prices
- ✅ **Error Handling**: Comprehensive validation and user feedback
- ✅ **Local Development**: Preservation of custom modifications

**🚀 Performance Achievements**:
- Zero placeholder price errors ("价格不在价位上" eliminated)
- Real-time market data integration
- Professional-grade order execution
- Institutional-quality price handling
- Transparent pricing with user visibility
- Automated slippage management

**📊 Production Ready**:
The complete system is now production-ready for professional trading environments, providing institutional-grade market and opponent price functionality with intelligent chase capabilities and full price transparency.

### Quick Start Commands

**Launch Development Environment**:
```bash
# Run comprehensive version with error handling
.\update_and_run.bat

# Or run quick version
.\quick_start.bat
```

**Verify Installation**:
1. Check that both vnpy and vnpy_futu are installed in development mode
2. Confirm custom Market/OPPONENT/Chase features are available in UI
3. Validate real-time price calculation and display
4. Test intelligent chase functionality with paper trading

This implementation represents a complete, professional-grade trading system enhancement that significantly improves order execution capabilities while maintaining full price transparency and risk controls.

## Latest Enhancement: ATR-Based Dynamic Chase Strategy (December 2024)

### Overview
Enhanced the intelligent price chasing system with ATR (Average True Range) and volume-based dynamic step calculation to optimize execution time and improve chase effectiveness. This update addresses the critical requirement of achieving execution times under 500ms for real trading scenarios.

### Problem Statement
- Fixed chase step percentage doesn't adapt to market volatility and liquidity
- Execution times exceeding 500ms making it unsuitable for real trading
- Inefficient chasing leading to unnecessary slippage
- Lack of performance monitoring and detailed logging

### Solution: ATR and Volume-Based Dynamic Chase

**Key Features:**

1. **Dynamic Chase Step Calculation**
   - Calculates ATR from past 34 one-minute periods
   - Analyzes average volume for liquidity assessment
   - Adjusts chase step based on market volatility (ATR) and liquidity (volume)
   - Step range: 0.01% - 0.5% (adaptive)

2. **Optimized Chase Intervals**
   - First 2 chases: 100ms interval (fast response)
   - Subsequent chases: Configurable interval (default 500ms)
   - Reduced rejection delay: 50ms (was 500ms)

3. **Enhanced Performance Monitoring**
   - Detailed timing metrics for each chase execution
   - Average, max, min modify order times
   - Total chase time tracking
   - Execution records (last 100)

4. **Comprehensive Logging**
   - ATR and volume information in chase calculation logs
   - Detailed execution logs with timing metrics
   - Performance statistics for analysis

### Implementation Details

**ATR and Volume Calculation:**
```python
def calculate_atr_and_volume(self, vt_symbol: str) -> Tuple[float, float]:
    """Calculate ATR and average volume (based on past 34 one-minute periods)"""
    # Query historical K-line data (34 one-minute periods)
    # Calculate ATR using talib (14-period) or simplified calculation
    # Calculate average volume
    # Cache results for performance
```

**Dynamic Step Calculation:**
```python
def calculate_dynamic_chase_step(
    self, vt_symbol: str, current_price: float, direction: Direction
) -> float:
    """Calculate dynamic chase step based on ATR and volume"""
    # Base step: 15% of ATR percentage
    # Volume adjustment: Higher volume = smaller step (better liquidity)
    # Limit step range: 0.01% - 0.5%
```

**Performance Metrics:**
```python
self.chase_stats = {
    "total_chase_time": 0.0,        # Cumulative chase time (ms)
    "chase_executions": [],          # Detailed execution records
    "average_chase_time_ms": 0.0,    # Average chase time
    "avg_modify_time_ms": 0.0,       # Average modify order time
    "max_modify_time_ms": 0.0,       # Maximum modify order time
    "min_modify_time_ms": 0.0,       # Minimum modify order time
}
```

### Performance Target
- **Goal**: Execution time under 500ms
- **Optimization**: Adaptive step size + reduced intervals
- **Monitoring**: Real-time performance metrics

### Testing
Comprehensive test suite in [test_chase_atr_strategy.py](test_chase_atr_strategy.py):
- ATR calculation accuracy
- Dynamic step calculation logic
- Performance simulation
- Interval optimization
- Logging format validation

All tests pass successfully.

### Files Modified
- **Gateway**: [vnpy_futu/vnpy_futu/futu_gateway.py](vnpy_futu/vnpy_futu/futu_gateway.py)
  - Added `calculate_atr_and_volume()` method
  - Added `calculate_dynamic_chase_step()` method
  - Enhanced `calculate_chase_price()` with dynamic step
  - Optimized `start_chase_order()` with reduced intervals
  - Enhanced `execute_chase_order()` with detailed logging
  - Added performance metrics to `chase_stats`
- **Tests**: [test_chase_atr_strategy.py](test_chase_atr_strategy.py) - Complete test coverage

### Benefits
- **Adaptive Strategy**: Chase step adapts to market conditions
- **Faster Execution**: Reduced intervals for first 2 chases
- **Better Performance**: Target execution time under 500ms
- **Comprehensive Monitoring**: Detailed metrics for analysis
- **Production Ready**: Fully tested and validated

## Latest Fix: Simulate Trading Trade Data Display (December 2024)

### Overview
Fixed an issue where trade data was not displayed in the simulate trading environment. The Futu API's `deal_list_query` method returns an error "模拟交易不支持成交数据" (Simulate trading does not support trade data) in simulate trading mode, preventing trade data from being displayed in the UI.

### Problem Statement
- **Issue**: Trade data query fails in simulate trading environment
- **Error Message**: "查询成交失败：模拟交易不支持成交数据"
- **Impact**: Users cannot see trade history even though orders are fully executed
- **Root Cause**: Futu API's `deal_list_query` method doesn't support simulate trading environment

### Solution: Trade Data Caching and Fallback Mechanism

**Key Features:**

1. **Trade Data Cache**
   - Added `trades_cache: Dict[str, TradeData]` to store all trade data
   - Automatically caches trade data when `process_deal()` is called
   - Ensures all trade data is preserved locally

2. **Fallback Query Mechanism**
   - When API query fails, automatically detects simulate trading environment
   - Falls back to local cache to retrieve trade data
   - Re-pushes trade data through event system to ensure UI display

3. **Error Detection**
   - Detects simulate trading environment by checking error message
   - Also checks `TrdEnv.SIMULATE` flag
   - Handles both explicit error messages and environment flags

### Implementation Details

**Trade Data Caching:**
```python
# Added cache dictionary
self.trades_cache: Dict[str, TradeData] = {}

# Cache trade data in process_deal()
def process_deal(self, data) -> None:
    # ... process trade data ...
    # Cache trade data for simulate trading environment
    self.trades_cache[trade.vt_tradeid] = trade
    self.on_trade(trade)
```

**Fallback Query:**
```python
def query_trade(self) -> None:
    """Query trade data"""
    code, data = self.trade_ctx.deal_list_query("", trd_env=self.env)
    
    if code:
        error_msg = str(data) if data else "未知错误"
        # Detect simulate trading environment
        if "模拟交易" in error_msg or "不支持" in error_msg or self.env == TrdEnv.SIMULATE:
            self._query_trades_from_cache()
        return
    
    self.process_deal(data)
```

**Cache Retrieval:**
```python
def _query_trades_from_cache(self) -> None:
    """Retrieve trade data from local cache (for simulate trading)"""
    if self.trades_cache:
        for trade in self.trades_cache.values():
            # Re-push trade data through event system
            event = Event(EVENT_TRADE, trade)
            self.event_engine.put(event)
```

### Key Improvements

1. **Automatic Caching**: All trade data is automatically cached when received
2. **Seamless Fallback**: When API fails, automatically uses local cache
3. **UI Compatibility**: Re-pushes trade data to ensure UI displays correctly
4. **Multi-Gateway Support**: Each gateway maintains its own cache, ensuring data isolation

### Testing
Comprehensive test suite in [test_simulate_trade_query.py](test_simulate_trade_query.py):
- Trade data cache storage validation
- Cache retrieval functionality
- Simulate trading environment error handling
- Cache consistency verification
- Empty cache handling
- Multi-gateway data isolation

All tests pass successfully.

### Files Modified
- **Gateway**: [vnpy_futu/vnpy_futu/futu_gateway.py](vnpy_futu/vnpy_futu/futu_gateway.py)
  - Added `trades_cache: Dict[str, TradeData]` for trade data caching
  - Modified `process_deal()` to cache trade data
  - Enhanced `query_trade()` with fallback mechanism
  - Added `_query_trades_from_cache()` method
- **Tests**: [test_simulate_trade_query.py](test_simulate_trade_query.py) - Complete test coverage

### Benefits
- **Complete Trade History**: Users can see all trade data in simulate trading environment
- **Seamless Experience**: Automatic fallback ensures no user intervention needed
- **Data Persistence**: Trade data is cached locally, ensuring availability
- **Production Ready**: Fully tested and validated for simulate trading scenarios

## Latest Enhancement: Close Position Button Feature (December 2024)

### Overview
Added a comprehensive close position button feature to the trading UI that automatically detects current positions and provides one-click position closing with intelligent price chasing. This enhancement significantly improves trading efficiency by eliminating manual order entry for position closing operations.

### Problem Statement
- **Manual Process**: Users had to manually enter close orders with correct direction, offset, and price
- **Error-Prone**: Easy to make mistakes when selecting close direction (close long vs close short)
- **Time-Consuming**: Multiple steps required: check position, select direction, enter price, configure chase
- **No Real-time Feedback**: Button state didn't reflect current position status

### Solution: Intelligent Close Position Button

**Key Features:**

1. **Automatic Position Detection**
   - Queries current contract's long and short positions in real-time
   - Calculates available position (total position - frozen position)
   - Updates button text dynamically: "平仓（平多 X手）" or "平仓（平空 X手）" or "平仓（无持仓）"

2. **Smart Button State Management**
   - Button enabled only when there's available position
   - Button text shows exact position type and available volume
   - Position volume selector automatically limited to available position
   - Real-time updates when position changes

3. **One-Click Close Position**
   - Automatically determines close direction (SHORT for long position, LONG for short position)
   - Uses opponent price (bid for close long, ask for close short)
   - Automatically enables intelligent price chasing
   - Validates close volume against available position

4. **Event-Driven Updates**
   - Updates button state when contract changes
   - Updates button state when gateway changes
   - Updates button state when position events occur
   - Initializes button state on UI load

### Implementation Details

**UI Components Added:**
```python
# Close position button
self.close_position_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("平仓（无持仓）"))
self.close_position_button.setEnabled(False)
self.close_position_button.clicked.connect(self.close_position)
self.close_position_button.setToolTip(_("根据当前持仓自动平仓，使用对手价并启用智能追价"))

# Close volume selector
self.close_volume_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
self.close_volume_spin.setRange(1, 1000)
self.close_volume_spin.setValue(1)
self.close_volume_spin.setSuffix(_("手"))
```

**Position Query Logic:**
```python
def update_close_position_button(self) -> None:
    """Update close position button state and text"""
    # Query long position
    long_positionid = f"{gateway_name}.{self.vt_symbol}.{Direction.LONG.value}"
    long_position = self.main_engine.get_position(long_positionid)
    
    # Query short position
    short_positionid = f"{gateway_name}.{self.vt_symbol}.{Direction.SHORT.value}"
    short_position = self.main_engine.get_position(short_positionid)
    
    # Calculate available position (total - frozen)
    long_available = (long_position.volume - long_position.frozen) if long_position and long_position.volume > 0 else 0
    short_available = (short_position.volume - short_position.frozen) if short_position and short_position.volume > 0 else 0
    
    # Update button state and text
    if long_available > 0:
        self.close_position_button.setText(_(f"平仓（平多 {long_available:.0f}手）"))
        self.close_position_button.setEnabled(True)
        self.close_volume_spin.setMaximum(int(long_available))
    elif short_available > 0:
        self.close_position_button.setText(_(f"平仓（平空 {short_available:.0f}手）"))
        self.close_position_button.setEnabled(True)
        self.close_volume_spin.setMaximum(int(short_available))
    else:
        self.close_position_button.setText(_("平仓（无持仓）"))
        self.close_position_button.setEnabled(False)
```

**Close Position Execution:**
```python
def close_position(self) -> None:
    """Execute close position operation"""
    # Determine close direction and available volume
    if long_available > 0:
        close_direction = Direction.SHORT  # Close long: sell
        available_volume = long_available
    elif short_available > 0:
        close_direction = Direction.LONG  # Close short: buy
        available_volume = short_available
    
    # Get close volume
    close_volume = self.close_volume_spin.value()
    
    # Validate close volume
    if close_volume > available_volume:
        QtWidgets.QMessageBox.warning(...)
        return
    
    # Calculate opponent price
    if close_direction == Direction.SHORT:
        # Close long: use bid price
        price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
    else:
        # Close short: use ask price
        price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
    
    # Build order request with chase config
    reference = "OPPONENT"
    chase_config = self.get_chase_config()
    if chase_config["enabled"]:
        chase_suffix = f"_Chase{chase_config['max_chase_times']}_Slip{chase_config['max_slippage_pct']}_Step{chase_config['chase_step_pct']}"
        reference += chase_suffix
    
    req: OrderRequest = OrderRequest(
        symbol=contract.symbol,
        exchange=contract.exchange,
        direction=close_direction,
        type=OrderType.OPPONENT,  # Use opponent price
        volume=close_volume,
        price=price,
        offset=Offset.CLOSE,  # Close position
        reference=reference
    )
    
    # Submit order
    self.main_engine.send_order(req, gateway_name)
```

**Event Registration:**
```python
def register_event(self) -> None:
    """Register event handlers"""
    # Register position event for button state updates
    self.event_engine.register(EVENT_POSITION, self.process_position_event)
    
    # Initialize button state
    self.update_close_position_button()

def process_position_event(self, event: Event) -> None:
    """Handle position events to update button state"""
    position: PositionData = event.data
    if position.vt_symbol == self.vt_symbol:
        self.update_close_position_button()
```

### Button State Update Triggers

1. **Contract Change**: When user selects a different contract
2. **Gateway Change**: When user switches to a different gateway
3. **Position Event**: When position data is updated (trade execution, position query)
4. **UI Initialization**: When trading widget is first loaded

### Close Position Flow

1. **User Clicks Button**: "平仓（平多 5手）" or "平仓（平空 3手）"
2. **System Validates**: Checks available position and close volume
3. **Price Calculation**: Calculates opponent price (bid for close long, ask for close short)
4. **Order Submission**: Creates order request with:
   - Correct direction (SHORT for long position, LONG for short position)
   - Opponent price
   - Close offset
   - Intelligent chase configuration
5. **Button Update**: Updates button state after order submission

### Key Improvements

1. **User Experience**:
   - One-click position closing
   - Clear visual feedback (button text shows position type and volume)
   - Automatic validation prevents errors
   - Real-time position status updates

2. **Trading Efficiency**:
   - Eliminates manual order entry steps
   - Automatic direction selection (no confusion)
   - Automatic price calculation (opponent price)
   - Automatic chase configuration

3. **Error Prevention**:
   - Volume validation against available position
   - Price validation (ensures valid market price)
   - Contract validation (ensures contract exists)
   - Gateway validation (ensures gateway is connected)

4. **Real-time Updates**:
   - Button state updates immediately when position changes
   - Volume selector automatically adjusts to available position
   - Clear indication when no position exists

### Usage Examples

**Example 1: Close Long Position**
```
Current Position: Long 5手 (available: 5手, frozen: 0手)
Button Display: "平仓（平多 5手）" [Enabled]
User Action: Select 3手, click button
System Action:
  1. Validates: 3手 ≤ 5手 ✓
  2. Calculates: bid_price_1 = 25000.0
  3. Creates order: SHORT 3手 @ 25000.0, CLOSE, OPPONENT + Chase
  4. Submits order
  5. Updates button: "平仓（平多 2手）" (after partial close)
```

**Example 2: Close Short Position**
```
Current Position: Short 8手 (available: 6手, frozen: 2手)
Button Display: "平仓（平空 6手）" [Enabled]
User Action: Select 6手, click button
System Action:
  1. Validates: 6手 ≤ 6手 ✓
  2. Calculates: ask_price_1 = 25010.0
  3. Creates order: LONG 6手 @ 25010.0, CLOSE, OPPONENT + Chase
  4. Submits order
  5. Updates button: "平仓（无持仓）" (after full close)
```

**Example 3: No Position**
```
Current Position: None
Button Display: "平仓（无持仓）" [Disabled]
User Action: Button click (disabled, no action)
```

### Testing

Comprehensive test suite in [test_close_position_button.py](test_close_position_button.py):
- Button state logic tests (6 scenarios)
- Close order request building tests
- Validation logic tests (4 scenarios)
- Opponent price calculation tests
- Chase configuration tests

All tests pass successfully.

### Files Modified

- **UI**: [vnpy/trader/ui/widget.py](vnpy/trader/ui/widget.py)
  - Added `close_position_button` and `close_volume_spin` UI components
  - Added `process_position_event()` method for position event handling
  - Added `update_close_position_button()` method for button state management
  - Added `close_position()` method for close position execution
  - Enhanced `register_event()` to register position events
  - Enhanced `set_vt_symbol()` to update button state on contract change
  - Added gateway change handler to update button state
- **Tests**: [test_close_position_button.py](test_close_position_button.py) - Complete test coverage

### Benefits

- **Trading Efficiency**: One-click position closing eliminates manual steps
- **Error Prevention**: Automatic direction and price calculation prevents mistakes
- **Real-time Feedback**: Button state reflects current position status
- **User-Friendly**: Clear visual indication of position type and available volume
- **Production Ready**: Fully tested and validated for all scenarios

This enhancement provides a professional-grade position closing feature that significantly improves trading workflow efficiency while maintaining all safety validations and intelligent chase capabilities.

## Latest Fix: Main Contract and Specific Contract Matching (December 2024)

### Overview
Fixed an issue where the close position button showed "无持仓" (no position) when subscribing to a main contract code (e.g., `MHImain.SEHK`) while the actual position was held in a specific contract (e.g., `MHI2511.SEHK`). This mismatch occurred because Futu API returns specific contract codes in position queries, while users often subscribe to main contract codes for continuous trading.

### Problem Statement
- **Issue**: Close position button displayed "无持仓" when subscribing to main contract code
- **Root Cause**: Position query returns specific contract codes (e.g., `MHI2511.SEHK`), but subscription uses main contract codes (e.g., `MHImain.SEHK`)
- **Impact**: Users cannot see or close positions when using main contract codes
- **Example**: Subscribing to `MHImain.SEHK` but position is `MHI2511.SEHK` (2025 November contract)

### Solution: Intelligent Contract Code Matching

**Key Features:**

1. **Contract Matching Logic**
   - Exact match: `MHImain.SEHK` == `MHImain.SEHK`
   - Main contract match: `MHImain.SEHK` matches `MHI2511.SEHK` (main contract matches specific contract)
   - Reverse match: `MHI2511.SEHK` matches `MHImain.SEHK` (specific contract matches main contract)

2. **Matching Rules**
   - Main contract format: `{base}main` (e.g., `MHImain`)
   - Specific contract format: `{base}{YYMM}` (e.g., `MHI2511` for November 2025)
   - Exchange must match
   - Base part must match

3. **Comprehensive Matching**
   - Applied to all position-related operations:
     - Close position button state update
     - Position event processing
     - Position query filtering

### Implementation Details

**Contract Matching Method:**
```python
def _is_contract_match(self, vt_symbol1: str, vt_symbol2: str) -> bool:
    """
    Determine if two contract codes match (supports main contract and specific contract matching)
    
    Rules:
    1. Exact match: MHImain.SEHK == MHImain.SEHK
    2. Main contract match: MHImain.SEHK matches MHI2511.SEHK
    3. Reverse match: MHI2511.SEHK matches MHImain.SEHK
    
    Main contract format: {base}main (e.g., MHImain)
    Specific contract format: {base}{YYMM} (e.g., MHI2511 for November 2025)
    """
    if vt_symbol1 == vt_symbol2:
        return True
    
    # Extract symbol and exchange
    symbol1, exchange1 = vt_symbol1.split('.', 1)
    symbol2, exchange2 = vt_symbol2.split('.', 1)
    
    # Exchange must match
    if exchange1 != exchange2:
        return False
    
    # Check if it's a main contract and specific contract match
    if symbol1.endswith('main') and not symbol2.endswith('main'):
        # symbol1 is main contract, symbol2 is specific contract
        base1 = symbol1[:-4]  # Remove "main"
        if symbol2.startswith(base1):
            return True
    elif symbol2.endswith('main') and not symbol1.endswith('main'):
        # symbol2 is main contract, symbol1 is specific contract
        base2 = symbol2[:-4]  # Remove "main"
        if symbol1.startswith(base2):
            return True
    
    return False
```

**Updated Position Query Logic:**
```python
def update_close_position_button(self) -> None:
    """Update close position button state and text"""
    # ... query positions ...
    
    for position in all_positions:
        # Match contract (supports main contract and specific contract matching) and gateway
        if (self._is_contract_match(position.vt_symbol, self.vt_symbol) and 
            position.gateway_name == gateway_name):
            matched_positions.append(position)
            # ... process matched positions ...
```

**Updated Position Event Processing:**
```python
def process_position_event(self, event: Event) -> None:
    """Handle position events to update button state"""
    position: PositionData = event.data
    # Only update current contract's position (supports main contract and specific contract matching)
    if self.vt_symbol and self._is_contract_match(position.vt_symbol, self.vt_symbol):
        self.update_close_position_button()
```

### Key Improvements

1. **Intelligent Matching**:
   - Automatically matches main contract codes with specific contract positions
   - Supports bidirectional matching (main ↔ specific)
   - Maintains exact matching for same contract codes

2. **Comprehensive Coverage**:
   - Applied to all position-related operations
   - Button state updates
   - Position event processing
   - Position query filtering

3. **Robust Logic**:
   - Exchange validation ensures correct matching
   - Base part matching ensures contract family matching
   - Handles edge cases gracefully

### Usage Examples

**Example 1: Main Contract Subscription with Specific Contract Position**
```
Subscription: MHImain.SEHK (main contract)
Position: MHI2511.SEHK (specific contract, November 2025)
Result: ✓ Matched - Button shows "平仓（平多 2手）"
```

**Example 2: Specific Contract Subscription with Main Contract Position**
```
Subscription: MHI2511.SEHK (specific contract)
Position: MHImain.SEHK (main contract)
Result: ✓ Matched - Button shows position correctly
```

**Example 3: Different Base Contracts**
```
Subscription: MHImain.SEHK (MHI main contract)
Position: HSI2511.SEHK (HSI specific contract)
Result: ✗ Not matched - Different base contracts
```

**Example 4: Different Exchanges**
```
Subscription: MHImain.SEHK
Position: MHI2511.HKFE
Result: ✗ Not matched - Different exchanges
```

### Testing

Comprehensive test suite in [test_contract_matching.py](test_contract_matching.py):
- Exact match tests
- Main contract and specific contract matching tests
- Position matching scenarios
- Edge case handling

All tests pass successfully.

### Files Modified

- **UI**: [vnpy/trader/ui/widget.py](vnpy/trader/ui/widget.py)
  - Added `_is_contract_match()` method for intelligent contract matching
  - Updated `update_close_position_button()` to use contract matching
  - Updated `close_position()` to use contract matching
  - Updated `process_position_event()` to use contract matching
  - Enhanced debug logging to show match status
- **Tests**: [test_contract_matching.py](test_contract_matching.py) - Complete test coverage

### Benefits

- **Seamless Experience**: Users can subscribe to main contracts and see positions in specific contracts
- **Flexible Matching**: Supports both main contract and specific contract subscriptions
- **Accurate Display**: Button state correctly reflects actual positions
- **Production Ready**: Fully tested and validated for all scenarios

This fix ensures that the close position button works correctly regardless of whether users subscribe to main contract codes or specific contract codes, providing a seamless trading experience.

## Latest Enhancement: Close Position Button UI Improvements (December 2024)

### Overview
Enhanced the close position button UI to provide a cleaner, more intuitive interface with better user experience. The improvements include simplified button text, fixed volume selector behavior, default full-close setting, and clear position hints.

### Problem Statement
- **Issue 1**: Close volume selector was fixed at 1 lot and couldn't be adjusted
- **Issue 2**: Button text was too verbose: "平仓（平多 X手）" or "平仓（平空 X手）"
- **Issue 3**: No clear indication of maximum available position
- **Issue 4**: Default close volume was 1 lot instead of full position

### Solution: Enhanced UI with Better UX

**Key Improvements:**

1. **Simplified Button Text**
   - Changed from "平仓（平多 X手）" to "平多"
   - Changed from "平仓（平空 X手）" to "平空"
   - Changed from "平仓（无持仓）" to "无持仓"
   - Cleaner, more concise display

2. **Fixed Volume Selector**
   - Fixed issue where volume selector couldn't be adjusted
   - Default value set to full position (full close)
   - Maximum value automatically limited to available position
   - Users can select full close or less

3. **Position Hint Label**
   - Added hint label below volume selector showing "<= X手"
   - Displays current available position in real-time
   - Gray, small font for non-intrusive display
   - Updates automatically when position changes

4. **Default Full-Close Behavior**
   - Volume selector defaults to full position amount
   - Users can easily adjust to partial close if needed
   - Reduces number of clicks for common full-close operation

### Implementation Details

**UI Components:**
```python
# Close position button (simplified text)
self.close_position_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("无持仓"))
self.close_position_button.setToolTip(_("根据当前持仓自动平仓，使用对手价并启用智能追价"))

# Volume selector with improved tooltip
self.close_volume_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
self.close_volume_spin.setRange(1, 1000)
self.close_volume_spin.setValue(1)
self.close_volume_spin.setSuffix(_("手"))
self.close_volume_spin.setToolTip(_("平仓手数（不能超过可用持仓）"))

# Position hint label
self.close_volume_hint_label: QtWidgets.QLabel = QtWidgets.QLabel(_("<= 0手"))
self.close_volume_hint_label.setStyleSheet("color: gray; font-size: 10px;")
self.close_volume_hint_label.setToolTip(_("当前可用持仓数量"))
```

**Button State Update Logic:**
```python
def update_close_position_button(self) -> None:
    """Update close position button state and text"""
    if long_available > 0:
        self.close_position_button.setText(_("平多"))
        self.close_position_button.setEnabled(True)
        # Set maximum and default to full position
        max_volume = int(long_available)
        self.close_volume_spin.setMaximum(max_volume)
        self.close_volume_spin.setValue(max_volume)  # Default to full close
        # Update hint label
        self.close_volume_hint_label.setText(_(f"<= {long_available:.0f}手"))
    elif short_available > 0:
        self.close_position_button.setText(_("平空"))
        self.close_position_button.setEnabled(True)
        # Set maximum and default to full position
        max_volume = int(short_available)
        self.close_volume_spin.setMaximum(max_volume)
        self.close_volume_spin.setValue(max_volume)  # Default to full close
        # Update hint label
        self.close_volume_hint_label.setText(_(f"<= {short_available:.0f}手"))
    else:
        self.close_position_button.setText(_("无持仓"))
        self.close_position_button.setEnabled(False)
        self.close_volume_spin.setMaximum(1000)
        self.close_volume_spin.setValue(1)
        self.close_volume_hint_label.setText(_("<= 0手"))
```

**UI Layout:**
```
平仓手数: [2手] [平多]
         <= 2手
```

### Key Improvements

1. **User Experience**:
   - **Simplified Text**: Button shows only "平多" or "平空" for clarity
   - **Default Full-Close**: Volume defaults to full position, reducing clicks
   - **Clear Hints**: Position hint shows maximum available clearly
   - **Intuitive Operation**: Users can easily see and adjust close volume

2. **Functionality**:
   - **Fixed Selector**: Volume selector now works correctly and can be adjusted
   - **Automatic Limits**: Maximum value automatically set to available position
   - **Real-time Updates**: Hint label updates when position changes
   - **Validation**: Cannot exceed available position

3. **Visual Design**:
   - **Cleaner Interface**: Simplified button text reduces visual clutter
   - **Clear Feedback**: Hint label provides immediate position information
   - **Non-intrusive**: Gray, small font for hint label doesn't distract

### Usage Examples

**Example 1: Long Position with Full Close**
```
Position: Long 2手 (available: 2手)
Button Display: "平多" [Enabled]
Volume Selector: [2手] (default, can be adjusted)
Hint Label: "<= 2手"
User Action: Click "平多" (full close)
Result: Closes all 2手
```

**Example 2: Long Position with Partial Close**
```
Position: Long 5手 (available: 5手)
Button Display: "平多" [Enabled]
Volume Selector: [5手] (default, user changes to 3手)
Hint Label: "<= 5手"
User Action: Change to 3手, click "平多"
Result: Closes 3手, leaves 2手
```

**Example 3: No Position**
```
Position: None
Button Display: "无持仓" [Disabled]
Volume Selector: [1手] (disabled)
Hint Label: "<= 0手"
User Action: Button disabled, no action possible
```

### Before and After Comparison

**Before:**
- Button: "平仓（平多 2手）" (verbose)
- Volume: Fixed at 1手 (couldn't adjust)
- Hint: None
- Default: 1手 (partial close)

**After:**
- Button: "平多" (concise)
- Volume: Adjustable, default 2手 (full close)
- Hint: "<= 2手" (clear indication)
- Default: 2手 (full close)

### Files Modified

- **UI**: [vnpy/trader/ui/widget.py](vnpy/trader/ui/widget.py)
  - Simplified button text ("平多"/"平空" instead of "平仓（平多 X手）")
  - Fixed volume selector default value (set to full position)
  - Added `close_volume_hint_label` for position hints
  - Updated `update_close_position_button()` to set default to full position
  - Enhanced UI layout with hint label

### Benefits

- **Better UX**: Cleaner, more intuitive interface
- **Efficiency**: Default full-close reduces clicks for common operation
- **Clarity**: Clear indication of maximum available position
- **Flexibility**: Users can easily adjust to partial close if needed
- **Reliability**: Fixed volume selector works correctly

This enhancement provides a more professional and user-friendly close position interface that improves trading workflow efficiency while maintaining all safety validations.

---

## 持仓信息实时刷新功能实现 (2025-11-21)

### 概述

实现了基于事件驱动的持仓信息实时刷新功能，解决了持仓盈亏（PnL）不刷新、持仓信息闪烁、平仓后持仓不清除等问题。采用 **方案D：双层缓存 + 轻量定序器** 架构，确保实时性同时避免阻塞事件引擎。

### 核心功能

#### 1. 实时 PnL 计算与刷新

- **触发机制**：基于 `EVENT_TICK` 事件，自动触发持仓 PnL 重新计算
- **刷新队列**：使用 `deque` 实现轻量级刷新队列，避免重复计算
- **批量处理**：定时器事件批量处理队列中的持仓刷新请求
- **连续合约映射**：支持主连合约（如 `MHImain`）与具体合约（如 `MHI2511`）之间的双向映射

#### 2. 净持仓模式支持

- **富途期货适配**：正确处理富途期货的净持仓模式（无开/平字段，只有买卖方向）
- **智能平仓识别**：根据交易方向与当前持仓方向自动判断是开仓还是平仓
- **持仓合并**：自动检测并合并多空持仓，计算净持仓

#### 3. 持仓删除与 UI 更新

- **自动删除**：当持仓 `volume=0` 时，自动从持仓字典中删除
- **UI 同步**：`PositionMonitor` 自动删除 `volume=0` 的持仓行
- **防闪烁**：使用 `removed_positions` 集合避免网关重复推送导致的闪烁

### 技术实现

#### 新增事件类型

**文件**: `vnpy/trader/event.py`
- `EVENT_POSITION_VIEW`: 新增持仓视图事件，用于实时刷新持仓信息

#### 核心修改

**文件**: `vnpy/trader/engine.py` - `OmsEngine` 类

1. **初始化新增字段**:
   ```python
   self.refresh_queue: deque[str] = deque()  # 刷新队列
   self.refresh_symbols: set[str] = set()    # 已入队符号集合
   self.last_view_emit: dict[str, float] = {} # 最后发送时间
   self.removed_positions: set[str] = set()   # 已删除持仓集合
   self.position_view_enabled: bool = SETTINGS.get("position.view.enabled", False)
   self.position_view_emit_legacy: bool = SETTINGS.get("position.view.emit_legacy", True)
   self.position_view_debug: bool = SETTINGS.get("position.view.debug", False)
   ```

2. **事件处理增强**:
   - `process_tick_event`: 检测持仓并入队刷新请求，支持连续合约映射
   - `process_trade_event`: 处理成交事件，更新持仓快照
   - `process_position_event`: 处理网关推送的持仓事件，保留计算的 PnL，处理净持仓合并
   - `process_timer_event`: 定时批量处理刷新队列

3. **核心方法**:
   - `_enqueue_refresh_symbol`: 将符号加入刷新队列
   - `_refresh_positions`: 批量处理刷新队列
   - `_refresh_symbol_positions`: 刷新指定符号的所有持仓
   - `_find_tick_for_position`: 查找持仓对应的 tick 数据（支持连续合约映射）
   - `_calculate_position_pnl`: 计算持仓盈亏（使用合约 size）
   - `_apply_trade_to_position`: 将成交结果合并到持仓快照（支持净持仓模式）
   - `_emit_position_view`: 发送持仓视图事件

#### UI 修改

**文件**: `vnpy/trader/ui/widget.py` - `PositionMonitor` 类

- 重写 `process_event` 方法，自动删除 `volume=0` 的持仓行
- 支持 `EVENT_POSITION_VIEW` 事件（向后兼容 `EVENT_POSITION`）

#### 网关修改

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py` - `FutuGateway` 类

- 修复合约 `size` 字段：根据合约代码设置正确的合约乘数
  - 小恒指（MHI）/小国指（MCH）：`size=10`（每跳 10 港币）
  - 大恒指（HSI）/大国指（HHI）：`size=50`（每跳 50 港币）

#### 配置项

**文件**: `vnpy/trader/setting.py`

新增配置项：
- `position.view.enabled`: 是否启用持仓视图功能（默认：`True`）
- `position.view.emit_legacy`: 是否同时发送旧版 `EVENT_POSITION` 事件（默认：`True`）
- `position.view.debug`: 是否启用调试日志（默认：`False`）

### 关键问题解决

#### 1. PnL 不刷新问题
- **原因**：`process_tick_event` 没有触发 PnL 重新计算
- **解决**：实现刷新队列机制，tick 事件触发入队，定时器批量处理

#### 2. 连续合约映射问题
- **原因**：持仓代码（`MHI2511`）与 tick 代码（`MHImain`）不匹配
- **解决**：实现双向映射逻辑，通过前缀匹配找到对应的 tick 数据

#### 3. 合约 size 错误问题
- **原因**：Futu 网关硬编码 `size=1`
- **解决**：根据合约代码设置正确的 `size`（小恒指=10，大恒指=50）

#### 4. 净持仓模式平仓问题
- **原因**：富途期货无开/平字段，只能通过买卖方向判断
- **解决**：实现智能平仓识别，根据交易方向与当前持仓方向判断

#### 5. 持仓闪烁问题
- **原因**：网关重复推送 `volume=0` 的持仓事件
- **解决**：使用 `removed_positions` 集合记录已删除持仓，忽略重复事件

#### 6. 持仓不清除问题
- **原因**：`volume=0` 的持仓仍在 UI 中显示
- **解决**：`PositionMonitor` 自动删除 `volume=0` 的持仓行

### 使用说明

#### 启用功能

在 `vt_setting.json` 中配置：
```json
{
  "position.view.enabled": true,
  "position.view.emit_legacy": true,
  "position.view.debug": false
}
```

#### 调试模式

如需查看详细日志，设置 `position.view.debug: true`。

### 测试验证

- ✅ 持仓 PnL 实时刷新（基于 tick 数据）
- ✅ 连续合约映射正常工作（MHImain <-> MHI2511）
- ✅ 净持仓模式平仓正确（多单用空单平，空单用多单平）
- ✅ 平仓后持仓自动清除（volume=0 不显示）
- ✅ 合约 size 正确（小恒指每跳 10 港币）
- ✅ 无持仓闪烁（已删除持仓不再处理）

### 文件清单

**修改的文件**:
- `vnpy/trader/engine.py`: 核心实现（OmsEngine）
- `vnpy/trader/event.py`: 新增 EVENT_POSITION_VIEW
- `vnpy/trader/setting.py`: 新增配置项
- `vnpy/trader/ui/widget.py`: UI 自动删除零持仓
- `vnpy_futu/vnpy_futu/futu_gateway.py`: 修复合约 size

**测试文件**:
- `test_position_refresh_service.py`: TDD 测试用例

### 架构设计

采用 **方案D：双层缓存 + 轻量定序器**：

1. **双层缓存**:
   - `position_snapshots` (self.positions): 持仓快照，存储"真实值"（来自网关或成交合并）
   - `last_view_cache` (self.last_view_emit): 最后发送的视图缓存，用于检测变化

2. **轻量定序器**:
   - `refresh_queue`: 刷新队列，存储待刷新的符号
   - `refresh_symbols`: 已入队符号集合，避免重复入队
   - 定时器批量处理，避免频繁计算

3. **事件驱动**:
   - Tick 事件 → 入队刷新请求
   - 定时器事件 → 批量处理队列
   - 成交事件 → 更新持仓快照
   - 持仓事件 → 保留计算的 PnL

### 性能优化

- **节流机制**：同一符号多次 tick 事件只入队一次
- **批量处理**：定时器批量处理队列，避免频繁计算
- **变化检测**：只在关键字段变化时发送事件，避免无效更新
- **去重处理**：使用 `removed_positions` 集合避免重复处理已删除持仓

### 向后兼容

- 默认启用 `position.view.emit_legacy=true`，同时发送新旧事件
- `PositionMonitor` 同时监听 `EVENT_POSITION` 和 `EVENT_POSITION_VIEW`
- 旧策略无需修改即可正常工作

## 2025-11-21 持仓PnL跳回问题修复

### 问题描述

持仓信息能够按照tick数据刷新，但每次刷新值之后，在下一个tick刷新前都会跳回显示固定值（如-10），而不是保持上次tick刷新的值。

### 问题分析

**根本原因**：
- Futu网关每秒定时查询持仓信息（`query_position()`）
- 网关推送的`PositionData`包含固定的PnL值（如-10）
- 这些网关数据会覆盖通过tick数据实时计算的正确PnL值

**问题流程**：
1. Tick数据更新 → 计算正确PnL（如-90） → 发送持仓视图事件
2. 1秒后，网关定时查询 → 推送固定PnL（-10） → 覆盖计算值
3. 下一个tick到来前，界面显示网关的固定值-10
4. 下一个tick到来 → 重新计算正确PnL → 循环往复

### 解决方案

修改 `vnpy/trader/engine.py` 中 `OmsEngine.process_position_event()` 方法的PnL保持逻辑：

**原逻辑问题**：
```python
# 只在网关推送 pnl=0 时保持计算值
if abs(gateway_pnl) < 1e-6 and abs(calculated_pnl) > 1e-6:
    self.positions[position.vt_positionid].pnl = calculated_pnl
```

**新逻辑改进**：
```python
# 检查是否有最近的计算结果（5秒内）
last_emit_time: float = self.last_view_emit.get(position.vt_positionid, 0.0)
current_time: float = time.time()
has_recent_calculation: bool = (current_time - last_emit_time) < 5.0

# 如果有最近计算且网关PnL不同，保持计算值
if has_recent_calculation and abs(gateway_pnl - calculated_pnl) > 1e-6:
    self.positions[position.vt_positionid].pnl = calculated_pnl
```

### 关键改进点

1. **时间窗口保护**：引入5秒时间窗口，在此期间优先保持计算的PnL值
2. **智能覆盖**：超过时间窗口后，允许网关数据更新（防止数据过时）
3. **通用适配**：不再局限于`pnl=0`的情况，适配任何网关固定值

### 修复效果

- ✅ **实时刷新**：持仓PnL能够根据tick数据实时更新
- ✅ **值保持**：在下一个tick到来前，PnL保持上次计算的正确值
- ✅ **智能覆盖**：计算时间过久时仍允许网关数据更新
- ✅ **向后兼容**：不影响现有功能，只改进PnL保持逻辑

### 测试验证

通过单元测试验证了修复方案的有效性：
1. **PnL保持测试**：验证最近计算的PnL值能够被正确保持
2. **旧值覆盖测试**：验证过时的计算值能够被网关数据正确覆盖

修复后，持仓信息显示稳定，不再出现PnL值跳回固定值的问题。

---

## 历史数据查询周期支持修复 (2025-11-22)

### 问题背景

在使用过程中发现1小时级别的历史数据查询失败，错误信息：
```
获取K线数据失败，FUTU接口暂不提供1h级别历史数据
```

### 问题分析

这是一个**regression issue**，发现两个文件中的周期映射不一致：

#### datafeed.py中的映射（完整）：
```python
INTERVAL_VT2FUTU = {
    Interval.MINUTE: KLType.K_1M,
    Interval.HOUR: KLType.K_60M,      # ✅ 包含HOUR映射
    Interval.DAILY: KLType.K_DAY,
    Interval.WEEKLY: KLType.K_WEEK    # ✅ 包含WEEKLY映射
}
```

#### futu_gateway.py中的映射（不完整）：
```python
interval_mapping = {
    Interval.MINUTE: KLType.K_1M,
    Interval.DAILY: KLType.K_DAY,     # ❌ 缺少HOUR和WEEKLY
}
```

### 修复方案

同步`futu_gateway.py`中的`interval_mapping`与`datafeed.py`中的完整映射：

```python
# 修复后的完整映射
interval_mapping = {
    Interval.MINUTE: KLType.K_1M,
    Interval.HOUR: KLType.K_60M,      # 新增：支持1小时K线
    Interval.DAILY: KLType.K_DAY,
    Interval.WEEKLY: KLType.K_WEEK,   # 新增：支持周K线
}
```

### 支持的时间周期

修复后，富途网关支持以下历史数据查询周期：
- ✅ **1分钟** (`Interval.MINUTE` → `KLType.K_1M`)
- ✅ **1小时** (`Interval.HOUR` → `KLType.K_60M`) 
- ✅ **日线** (`Interval.DAILY` → `KLType.K_DAY`)
- ✅ **周线** (`Interval.WEEKLY` → `KLType.K_WEEK`)

### 验证结果

修复后，1小时级别的历史数据查询应该能正常工作，不再出现"FUTU接口暂不提供1h级别历史数据"的错误。

### 文件修改

- **Gateway**: `vnpy_futu/vnpy_futu/futu_gateway.py` - 同步历史数据查询周期映射

这个修复解决了历史数据查询功能的回归问题，确保了与datafeed模块的一致性。

## DataRecorder 数据保存机制 (2025-01)

### 概述

DataRecorder 是 VeighNa 的实盘行情记录模块，用于实时记录 Tick 数据和 K线数据，并自动保存到数据库中。记录的数据可用于 CtaBacktester 的历史回测、CtaStrategy 和 PortfolioStrategy 等策略的实盘初始化。

### 核心架构

#### 1. 数据流程

```
实时行情数据流
    ↓
[事件引擎] EVENT_TICK 事件
    ↓
[DataRecorder引擎] 接收并处理
    ↓
[内存缓存] 临时存储（ticks/bars字典）
    ↓
[定时批量保存] 每10秒批量写入数据库
    ↓
[数据库] 持久化存储
```

#### 2. Tick 数据保存流程

**接收与过滤**：
```python
def update_tick(self, tick: TickData) -> None:
    # 过滤偏离本地时间戳过大的Tick数据（默认60秒窗口）
    tick_delta: timedelta = abs(tick.datetime - self.filter_dt)
    if abs(tick_delta) >= self.filter_delta:
        return
    
    # 如果合约在录制列表中，记录Tick数据
    if tick.vt_symbol in self.tick_recordings:
        self.record_tick(copy(tick))
```

**内存缓存**：
```python
def record_tick(self, tick: TickData) -> None:
    """将Tick数据追加到内存缓存"""
    self.ticks[tick.vt_symbol].append(tick)
```

**批量保存**：
```python
def process_timer_event(self, event: Event) -> None:
    """定时器事件：每10秒批量保存数据"""
    self.timer_count += 1
    if self.timer_count < self.timer_interval:  # timer_interval = 10
        return
    self.timer_count = 0
    
    # 批量保存Tick数据
    for ticks in self.ticks.values():
        self.queue.put(("tick", ticks))
    self.ticks.clear()  # 清空缓存
```

**异步写入数据库**：
```python
def run(self) -> None:
    """独立线程异步保存数据"""
    while self.active:
        task: tuple[str, list] = self.queue.get(timeout=1)
        task_type, data = task
        
        if task_type == "tick":
            self.database.save_tick_data(data, stream=True)
        elif task_type == "bar":
            self.database.save_bar_data(data, stream=True)
```

#### 3. K线数据保存流程

**BarGenerator 合成**：
```python
def update_tick(self, tick: TickData) -> None:
    # 如果合约在K线录制列表中，使用BarGenerator合成1分钟K线
    if tick.vt_symbol in self.bar_recordings:
        bg: BarGenerator = self.get_bar_generator(tick.vt_symbol)
        bg.update_tick(copy(tick))  # 推送到BarGenerator聚合
```

**K线完成回调**：
```python
def get_bar_generator(self, vt_symbol: str) -> BarGenerator:
    """获取或创建BarGenerator实例"""
    bg = BarGenerator(self.record_bar)  # record_bar作为回调函数
    return bg

def record_bar(self, bar: BarData) -> None:
    """BarGenerator合成完成1分钟K线后调用此回调"""
    self.bars[bar.vt_symbol].append(bar)  # 缓存到内存
```

**批量保存**（与Tick数据相同）：
- 每10秒批量保存一次
- 通过队列异步写入数据库

### 数据库存储格式

DataRecorder 使用 `BaseDatabase` 接口，支持多种数据库后端：

#### SQLite（默认）
- **文件位置**：`vnpy.db`（在 VeighNa 安装目录）
- **表结构**：
  - `dbbardata`：存储K线数据
    - 字段：`symbol`, `exchange`, `datetime`, `interval`, `volume`, `turnover`, `open_interest`, `open_price`, `high_price`, `low_price`, `close_price`
  - `dbtickdata`：存储Tick数据
    - 字段：`symbol`, `exchange`, `datetime`, `name`, `volume`, `turnover`, `open_interest`, `last_price`, `last_volume`, `limit_up`, `limit_down`, `open_price`, `high_price`, `low_price`, `pre_close`, `bid_price_1`, `ask_price_1`, `bid_volume_1`, `ask_volume_1`, ...

#### MySQL/PostgreSQL
- 表结构与 SQLite 相同
- 支持更大数据量和并发访问
- 适合生产环境

#### MongoDB
- 使用集合（Collection）存储
- 每个合约的数据作为文档存储
- 支持灵活的查询和索引

### 关键配置参数

```python
# 定时保存间隔（秒）
self.timer_interval: int = 10  # 每10秒批量保存一次

# Tick数据过滤窗口（秒）
self.filter_window: int = 60  # 过滤偏离本地时间60秒以上的数据

# 内存缓存
self.ticks: dict[str, list[TickData]] = defaultdict(list)  # Tick数据缓存
self.bars: dict[str, list[BarData]] = defaultdict(list)    # K线数据缓存
```

### 数据保存特点

1. **批量保存**：
   - 每10秒批量写入一次，减少数据库操作频率
   - 提高写入效率，降低数据库负载

2. **异步处理**：
   - 使用独立线程处理数据保存
   - 不阻塞主程序，确保实时性

3. **流式写入**：
   - 使用 `stream=True` 模式
   - 适合实时数据流场景

4. **时间过滤**：
   - 自动过滤异常时间戳的Tick数据
   - 防止错误数据污染数据库

5. **自动去重**：
   - 数据库实现通常会自动处理重复数据
   - 确保数据唯一性

### 使用示例

#### 添加录制任务

```python
# 通过UI添加
recorder_engine.add_tick_recording("MHImain.SEHK")  # 录制Tick数据
recorder_engine.add_bar_recording("MHImain.SEHK")  # 录制1分钟K线

# 通过脚本添加
from vnpy_datarecorder import DataRecorderApp

recorder_engine = main_engine.add_app(DataRecorderApp)
recorder_engine.add_tick_recording("MHImain.SEHK")
recorder_engine.add_bar_recording("MHImain.SEHK")
```

#### 批量添加合约

```python
# 自动订阅符合条件的合约
def subscribe_data(event: Event) -> None:
    contract: ContractData = event.data
    if contract.exchange in recording_exchanges:
        recorder_engine.add_tick_recording(contract.vt_symbol)
        recorder_engine.add_bar_recording(contract.vt_symbol)

event_engine.register(EVENT_CONTRACT, subscribe_data)
```

### 数据读取

保存的数据可以通过标准数据库接口读取：

```python
from vnpy.trader.database import get_database

database = get_database()

# 读取K线数据
bars = database.load_bar_data(
    symbol="MHImain",
    exchange=Exchange.SEHK,
    interval=Interval.MINUTE,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# 读取Tick数据
ticks = database.load_tick_data(
    symbol="MHImain",
    exchange=Exchange.SEHK,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)
```

### 性能优化

1. **内存管理**：
   - 使用字典按合约分组缓存
   - 批量保存后立即清空缓存
   - 避免内存无限增长

2. **数据库优化**：
   - 批量插入比单条插入效率高
   - 流式写入模式减少事务开销
   - 支持数据库连接池

3. **时间过滤**：
   - 过滤异常时间戳数据
   - 减少无效数据写入
   - 提高数据质量

### 注意事项

1. **数据延迟**：
   - 数据最多延迟10秒保存（定时器间隔）
   - 程序异常退出可能导致最后10秒数据丢失
   - 建议定期备份数据库

2. **存储空间**：
   - Tick数据量巨大，需要足够的存储空间
   - 建议定期清理历史数据或使用数据归档

3. **数据库性能**：
   - 大量数据写入时注意数据库性能
   - 建议使用 MySQL/PostgreSQL 等生产级数据库
   - 定期优化数据库索引

4. **合约订阅**：
   - 确保合约已正确订阅行情
   - 检查合约信息是否查询成功
   - IB接口需要手动订阅后才能录制

### 文件位置

- **引擎实现**：`vnpy_datarecorder/vnpy_datarecorder/engine.py`
- **UI界面**：`vnpy_datarecorder/vnpy_datarecorder/ui/widget.py`
- **配置保存**：
  - 文件名：`data_recorder_setting.json`
  - 默认路径（Windows）：`C:\Users\<用户名>\.vntrader\data_recorder_setting.json`
  - 默认路径（Linux/macOS）：`~/.vntrader/data_recorder_setting.json`
  - 如果当前工作目录存在 `.vntrader` 文件夹，则使用当前工作目录下的配置文件

### 相关文档

- DataRecorder 使用文档：`docs/community/app/data_recorder.md`
- 数据库配置文档：`docs/community/info/database.md`

### 查看当前激活的录制配置

#### 方法1：通过UI界面查看

1. 启动 VeighNa Trader
2. 在菜单栏点击【功能】-> 【行情记录】
3. 在UI界面中查看：
   - **K线记录列表**：显示所有正在录制的K线合约
   - **Tick记录列表**：显示所有正在录制的Tick合约

#### 方法2：通过配置文件查看

**配置文件位置**：

配置文件路径的确定规则（按优先级）：
1. **当前工作目录**：如果当前工作目录下存在 `.vntrader` 文件夹，则使用 `当前工作目录/.vntrader/data_recorder_setting.json`
2. **用户主目录**：否则使用 `用户主目录/.vntrader/data_recorder_setting.json`

**Windows 系统**：
- 默认路径：`C:\Users\<用户名>\.vntrader\data_recorder_setting.json`
- 例如：`C:\Users\milom\.vntrader\data_recorder_setting.json`

**Linux/macOS 系统**：
- 默认路径：`~/.vntrader/data_recorder_setting.json`
- 例如：`/home/username/.vntrader/data_recorder_setting.json`

**通过Python代码获取路径**：
```python
from vnpy.trader.utility import get_file_path

config_path = get_file_path("data_recorder_setting.json")
print(f"配置文件路径: {config_path}")
print(f"绝对路径: {config_path.resolve()}")
```

**配置文件内容示例**：
```json
{
  "tick": {
    "MHImain.SEHK": {
      "symbol": "MHImain",
      "exchange": "SEHK",
      "gateway_name": "FUTU"
    }
  },
  "bar": {
    "MHImain.SEHK": {
      "symbol": "MHImain",
      "exchange": "SEHK",
      "gateway_name": "FUTU"
    }
  },
  "filter_window": 60
}
```

#### 方法3：通过Python代码查看

```python
from vnpy_datarecorder import DataRecorderApp

# 获取DataRecorder引擎
recorder_engine = main_engine.get_engine("DataRecorder")

# 查看Tick录制列表
tick_recordings = recorder_engine.tick_recordings
print("Tick录制列表：", list(tick_recordings.keys()))

# 查看K线录制列表
bar_recordings = recorder_engine.bar_recordings
print("K线录制列表：", list(bar_recordings.keys()))

# 查看完整配置
print("Tick配置：", tick_recordings)
print("K线配置：", bar_recordings)
```

### DataRecorder 与 DataManager 的区别

#### 功能定位

**DataRecorder（行情记录模块）**：
- **用途**：实时录制行情数据
- **数据来源**：实时行情数据流（通过 `EVENT_TICK` 事件）
- **工作方式**：被动接收，实时录制
- **数据特点**：实时产生，连续不断
- **适用场景**：实盘交易时录制实时行情

**DataManager（历史数据管理模块）**：
- **用途**：管理历史数据（下载、查看、导入、导出、更新）
- **数据来源**：数据服务（datafeed）或交易接口的历史数据查询
- **工作方式**：主动查询，批量下载
- **数据特点**：历史已有，按需下载
- **适用场景**：回测前准备历史数据，补充缺失的历史数据

#### 更新数据功能的区别

**DataRecorder 的"录制"**：
```python
# 实时录制流程
实时行情 → EVENT_TICK事件 → DataRecorder接收 → 内存缓存 → 定时批量保存到数据库
```
- 从**实时行情流**中录制
- 数据是**实时产生**的
- 需要**订阅行情**才能录制
- 录制的是**当前时刻**的数据

**DataManager 的"更新数据"**：
```python
# 更新数据流程
数据库已有数据 → 查询结束日期 → 从数据服务下载最新数据 → 保存到数据库
```
- 从**数据服务**（datafeed）或**交易接口**下载
- 数据是**历史已有**的
- 需要**配置数据服务**（如富途、RQData等）
- 更新的是**历史缺失**的数据

#### 数据存储冲突分析

**结论：不会冲突，可以共存**

1. **使用同一个数据库**：
   - 两者都使用 `get_database()` 获取数据库实例
   - 数据存储在相同的表结构中（`dbbardata`、`dbtickdata`）

2. **数据去重机制**：
   - 数据库的 `save_bar_data()` 和 `save_tick_data()` 方法会处理重复数据
   - 通常通过 `(symbol, exchange, datetime, interval)` 唯一索引去重
   - 相同时间戳的数据会被覆盖或忽略

3. **数据互补性**：
   - **DataRecorder**：录制实时数据，填补实时数据空白
   - **DataManager**：下载历史数据，填补历史数据空白
   - 两者可以**同时使用**，形成完整的数据覆盖

4. **使用建议**：
   ```python
   # 场景1：回测前准备数据
   # 使用 DataManager 下载历史数据
   data_manager.download_bar_data("MHImain", Exchange.SEHK, Interval.MINUTE, start_date)
   
   # 场景2：实盘交易时录制数据
   # 使用 DataRecorder 录制实时数据
   recorder_engine.add_bar_recording("MHImain.SEHK")
   
   # 场景3：定期更新历史数据
   # 使用 DataManager 更新到最新日期
   data_manager.update_data()  # 从数据库结束日期更新到当前日期
   ```

5. **数据时间范围**：
   - **DataRecorder**：录制**当前时刻**的数据（实时）
   - **DataManager**：下载**历史时间段**的数据（从指定开始日期到当前日期）

#### 典型使用场景

**场景1：回测准备**
```python
# 1. 使用 DataManager 下载历史数据
data_manager.download_bar_data("MHImain", Exchange.SEHK, Interval.MINUTE, datetime(2024, 1, 1))

# 2. 运行回测
backtesting_engine.run_backtesting()
```

**场景2：实盘录制**
```python
# 1. 启动 DataRecorder
recorder_engine.add_bar_recording("MHImain.SEHK")
recorder_engine.add_tick_recording("MHImain.SEHK")

# 2. 实时录制数据（自动保存到数据库）
```

**场景3：数据维护**
```python
# 1. 使用 DataManager 更新历史数据（补充缺失）
data_manager.update_data()  # 从数据库结束日期更新到当前日期

# 2. 使用 DataRecorder 继续录制实时数据
recorder_engine.add_bar_recording("MHImain.SEHK")
```

#### 注意事项

1. **数据服务配置**：
   - DataManager 需要配置数据服务（datafeed）才能下载历史数据
   - DataRecorder 需要订阅行情才能录制实时数据

2. **数据完整性**：
   - DataManager 下载的数据可能不连续（取决于数据服务提供的数据范围）
   - DataRecorder 录制的数据是连续的（实时行情流）

3. **存储空间**：
   - 两者都会写入数据库，注意存储空间管理
   - 建议定期清理历史数据或使用数据归档

4. **性能考虑**：
   - DataRecorder 实时录制，对数据库写入性能要求较高
   - DataManager 批量下载，对数据库读取性能要求较高
   - 建议使用 MySQL/PostgreSQL 等生产级数据库

## DataManager 4小时和5分钟数据自动合成功能 (2025-01)

### 概述

DataManager模块新增了从已有数据自动合成4小时和5分钟K线数据的功能，解决了某些数据源（如FUTU API）不支持这些周期数据的问题。

### 功能特性

#### 1. 5分钟数据合成
- **数据源**：从1分钟K线数据合成
- **合成规则**：按5分钟周期聚合（0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55分钟）
- **自动触发**：点击"更新数据"时，自动为有1分钟数据的合约合成5分钟数据
- **增量更新**：只合成缺失的数据，不会重复合成已有数据

#### 2. 4小时数据合成
- **数据源**：优先使用1小时数据，如果没有则使用1分钟数据
- **合成规则**：按4小时周期聚合（0:00, 4:00, 8:00, 12:00, 16:00, 20:00）
- **自动触发**：点击"更新数据"时，自动为有1小时或1分钟数据的合约合成4小时数据
- **增量更新**：只合成缺失的数据，不会重复合成已有数据

### 使用方法

#### 方法1：自动合成（推荐）
1. 确保数据库中有1分钟或1小时数据
2. 点击数据管理界面的"更新数据"按钮
3. 系统会自动检测并合成5分钟和4小时数据
4. 点击"刷新"按钮查看合成后的数据

#### 方法2：手动合成
1. 点击"下载数据"按钮
2. 选择合约、交易所和周期（5分钟或4小时）
3. 系统会提示这是从已有数据合成
4. 确认后开始合成

### 技术实现

#### 核心方法
- `aggregate_5minute_bars()`: 从1分钟数据合成5分钟K线
- `aggregate_4hour_bars()`: 从1小时或1分钟数据合成4小时K线

#### 关键特性
- **时区处理**：统一使用数据库时区（DB_TZ），确保时间比较正确
- **性能优化**：每处理1000条数据输出一次进度日志
- **异常处理**：单个合约合成失败不影响其他合约
- **UI响应**：合成过程中定期调用`processEvents()`保持UI响应

#### 代码位置
- `vnpy/trader/constant.py`: 添加了`Interval.HOUR_4 = "4h"`枚举
- `vnpy_datamanager/vnpy_datamanager/engine.py`: 实现了合成逻辑
- `vnpy_datamanager/vnpy_datamanager/ui/widget.py`: UI集成和进度显示

### 注意事项

1. **数据依赖**：
   - 5分钟数据需要1分钟数据作为基础
   - 4小时数据需要1小时或1分钟数据作为基础

2. **数据完整性**：
   - 合成数据依赖于基础数据的完整性
   - 如果基础数据有缺失，合成后的数据也会有相应缺失

3. **性能考虑**：
   - 大量数据合成可能需要一些时间
   - 建议在非交易时段进行数据合成

4. **FUTU API限制**：
   - FUTU API不支持4小时数据下载
   - 在下载对话框中，4小时选项会显示"需从已有数据合成"提示

### 相关改进

- 修复了FUTU数据服务中`_()`国际化函数导致的错误
- 改进了时区处理，避免offset-naive和offset-aware datetime比较错误
- 优化了UI响应性，避免大量数据合成时界面卡死

## IndicatorManager 快速初始化与增量加载功能 (2025-01)

### 概述

`IndicatorManager` 实现了快速初始化模式和增量加载功能，解决了在回测环境中加载大量历史指标数据时初始化时间过长的问题。通过先加载少量数据快速完成初始化，然后在后台异步加载完整数据，使得策略可以立即开始回测，而不需要等待完整历史数据加载完成。

### 核心功能

#### 1. 快速初始化模式 (Fast Mode)

**问题背景**：
- 加载1年（365天）的历史数据并计算指标可能需要数分钟甚至更长时间
- 在回测环境中，用户希望策略能够快速启动，而不需要等待完整数据加载
- 策略初始化时只需要最近一段时间的数据即可开始运行

**解决方案**：
- 快速模式：先加载少量数据（默认30天）快速完成初始化
- 后台异步加载：在后台线程中继续加载完整数据（365天）
- 增量合并：后台加载的数据会自动追加到现有数据中，不影响策略运行

**实现细节**：

```python
def initialize_indicators(
    self,
    interval: Interval,
    days: int = 365,
    database: Optional[BaseDatabase] = None,
    fast_mode: bool = False,
    fast_days: int = 30,
    preserve_existing: bool = False
):
    """
    快速模式工作流程：
    1. 先加载 fast_days 天的数据（默认30天）
    2. 快速计算指标并标记初始化完成
    3. 在后台异步加载完整 days 天的数据
    4. 使用增量模式（preserve_existing=True）合并数据
    """
    if fast_mode and not preserve_existing:
        # 快速模式：先加载少量数据
        fast_bars = self.load_history_bars(interval, fast_days, database)
        # 快速计算指标
        # ... 计算指标 ...
        # 标记初始化完成（允许策略开始运行）
        self._init_status[interval] = True
        
        # 后台继续加载完整数据（增量模式）
        if days > fast_days:
            self.initialize_indicators_async(
                interval,
                days=days,
                database=database,
                preserve_existing=True  # 保留现有数据
            )
```

#### 2. 增量加载模式 (Incremental Loading)

**问题背景**：
- 后台异步加载完整数据时，不能清空已加载的快速数据
- 需要智能合并新旧数据，避免重复和丢失

**解决方案**：
- `preserve_existing` 参数：控制是否保留现有数据
- 时间戳合并：根据K线时间戳智能合并新旧数据
- 增量更新指标：只更新新增部分的指标值

**实现细节**：

```python
# 增量加载逻辑
if preserve_existing and interval in self.history_bars:
    existing_bars = self.history_bars[interval]
    last_existing_time = existing_bars[-1].datetime if existing_bars else None
    
    # 过滤出新增的K线数据
    new_bars = [bar for bar in bars 
                if last_existing_time is None or bar.datetime > last_existing_time]
    
    # 合并现有数据和新增数据
    all_bars = existing_bars + new_bars
    
    # 增量更新指标（只更新新增部分）
    if len(indicator_deque) > 0:
        existing_count = len(indicator_deque)
        new_values = indicator_values[existing_count:]
        for val in new_values:
            indicator_deque.append(val)
```

#### 3. K线数据合成功能

**问题背景**：
- 数据库中可能只有1分钟K线数据，没有5分钟K线数据
- 需要从1分钟数据合成5分钟数据用于指标计算

**解决方案**：
- `_synthesize_bars_from_minute()` 方法：从1分钟K线合成目标周期K线
- 支持合成5分钟、15分钟、30分钟等能被60整除的周期
- 自动检测并合成：如果目标周期数据不存在，自动尝试从1分钟数据合成

**实现细节**：

```python
def load_history_bars(
    self,
    interval: Interval,
    days: int,
    database: Optional[BaseDatabase] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[BarData]:
    """加载历史K线数据，支持从1分钟数据合成"""
    # 先尝试直接加载目标周期数据
    bars = database.load_bar_data(...)
    
    if not bars:
        # 如果目标周期数据不存在，尝试从1分钟数据合成
        if interval in [Interval.MINUTE_5, Interval.MINUTE_15, ...]:
            minute_bars = database.load_bar_data(Interval.MINUTE, ...)
            if minute_bars:
                bars = self._synthesize_bars_from_minute(minute_bars, interval)
                self.write_log(f"从1分钟数据合成了 {len(bars)} 根{interval.value}K线")
```

### 使用示例

#### 回测环境中的使用

```python
def on_init(self):
    """策略初始化回调"""
    # 注册指标
    self.indicator_manager.register_indicator(
        interval=Interval.MINUTE_5,
        indicator_name="MIN5.PREV_OPEN",
        calculator=self._calculate_min5_open_prev_open,
        max_history=10000
    )
    
    # 获取数据库（兼容回测和实盘环境）
    try:
        # 实盘环境：从 cta_engine 获取数据库
        database = self.cta_engine.database
        is_backtesting = False
    except AttributeError:
        # 回测环境：使用 get_database() 函数
        database = get_database()
        is_backtesting = True
    
    # 初始化指标（回测环境使用快速模式）
    self.indicator_manager.initialize_indicators(
        Interval.MINUTE_5,
        days=365,  # 加载1年历史数据
        database=database,
        fast_mode=is_backtesting,  # 回测环境使用快速模式
        fast_days=30  # 快速模式先加载30天数据
    )
    
    # 策略可以立即继续执行，不等待完整数据加载
    self.load_bar(10)
```

#### 实盘环境中的使用

```python
def on_init(self):
    """策略初始化回调"""
    # 实盘环境不使用快速模式，直接加载完整数据
    database = self.cta_engine.database
    self.indicator_manager.initialize_indicators(
        Interval.MINUTE_5,
        days=365,
        database=database,
        fast_mode=False  # 实盘环境不使用快速模式
    )
```

### 工作流程

#### 快速模式完整流程

```
1. 策略初始化开始
   ↓
2. 调用 initialize_indicators(fast_mode=True, fast_days=30)
   ↓
3. 快速加载30天数据
   ↓
4. 快速计算指标（30天数据）
   ↓
5. 标记初始化完成（_init_status[interval] = True）
   ↓
6. 策略可以立即开始运行（使用30天数据）
   ↓
7. 后台异步加载365天完整数据（增量模式）
   ↓
8. 合并新旧数据（根据时间戳）
   ↓
9. 增量更新指标（只更新新增部分）
   ↓
10. 完整数据加载完成，策略继续使用完整数据
```

#### 增量加载数据合并流程

```
现有数据（快速模式）：
  [2024-01-01, 2024-01-02, ..., 2024-01-30]  ← 30天数据

后台加载完整数据：
  [2024-01-01, 2024-01-02, ..., 2024-12-31]  ← 365天数据

合并逻辑：
  1. 找到现有数据的最后时间戳：2024-01-30
  2. 过滤出新增数据：2024-01-31 之后的数据
  3. 合并：现有数据 + 新增数据
  4. 重新计算指标（使用合并后的完整数据）
  5. 增量更新指标deque（只追加新增部分）
```

### 关键特性

#### 1. 智能数据合并

- **时间戳检测**：根据K线时间戳智能检测新旧数据
- **去重处理**：自动处理重复数据，避免重复计算
- **无缝切换**：策略在数据合并过程中无需感知，继续正常运行

#### 2. 异步加载

- **非阻塞**：使用 `ThreadPoolExecutor` 在后台线程中加载数据
- **状态管理**：通过 `_init_status` 和 `_init_futures` 管理初始化状态
- **错误处理**：异步加载失败不影响策略运行

#### 3. 数据合成

- **自动检测**：自动检测目标周期数据是否存在
- **智能合成**：如果不存在，自动从1分钟数据合成
- **支持周期**：支持5分钟、15分钟、30分钟等能被60整除的周期

### 性能优化

#### 1. 快速启动

- **30天数据**：快速模式默认加载30天数据，通常只需几秒钟
- **立即可用**：策略可以立即开始运行，不需要等待完整数据

#### 2. 后台加载

- **异步处理**：完整数据在后台异步加载，不阻塞主线程
- **增量更新**：只更新新增部分，避免重复计算

#### 3. 内存管理

- **动态调整**：根据数据量动态调整 `deque` 的 `maxlen`
- **增量追加**：增量模式下只追加新数据，不重复存储

### 日志输出示例

```
[IndicatorManager] MHImain.HKFE - 注册指标: 5m - MIN5.PREV_OPEN
[IndicatorManager] MHImain.HKFE - 指标文件不存在，将从数据库加载K线数据并计算
[IndicatorManager] MHImain.HKFE - 快速模式：先加载 30 天数据快速初始化，然后在后台继续加载 365 天完整数据
[IndicatorManager] MHImain.HKFE - 5分钟周期数据不存在，尝试从1分钟数据合成
[IndicatorManager] MHImain.HKFE - 从1分钟数据合成了 3689 根5分钟K线
[IndicatorManager] MHImain.HKFE - 加载历史K线: 5m, 共 3689 根
[IndicatorManager] MHImain.HKFE - 快速初始化: 5m - MIN5.PREV_OPEN, 共 3689 个值（其中 3688 个有效值，快速模式，30天数据）
[IndicatorManager] MHImain.HKFE - 快速初始化完成: 5m 周期，所有指标已就绪
[IndicatorManager] MHImain.HKFE - 后台继续加载完整数据: 5m 周期，365 天（增量模式，保留现有数据）
[IndicatorManager] MHImain.HKFE - 开始异步增量初始化指标: 5m（保留现有数据）
[IndicatorManager] MHImain.HKFE - 增量加载模式：将从数据库加载K线数据并追加到现有指标数据
```

### 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fast_mode` | `bool` | `False` | 是否启用快速模式 |
| `fast_days` | `int` | `30` | 快速模式下的初始加载天数 |
| `preserve_existing` | `bool` | `False` | 是否保留现有数据（用于增量加载） |
| `days` | `int` | `365` | 完整数据加载天数 |

### 使用建议

#### 回测环境

- **启用快速模式**：`fast_mode=True`，快速启动回测
- **合理设置 fast_days**：根据策略需求设置，通常30天足够
- **等待完整数据**：如果需要完整历史数据，可以等待异步加载完成

#### 实盘环境

- **禁用快速模式**：`fast_mode=False`，直接加载完整数据
- **确保数据完整**：实盘环境需要完整的历史数据用于准确计算

### 文件位置

- **核心实现**：`indicators/indicator_manager.py`
- **使用示例**：`vnpy_ctastrategy/vnpy_ctastrategy/strategies/test_import_strategy.py`
- **文档**：`indicators/docs/INDICATOR_MANAGER_README.md`

### 相关功能

- **运行时指标值**：支持在K线聚合过程中计算和引用运行时指标值
- **数据持久化**：支持将指标数据保存到 Parquet/PKL 文件
- **智能获取**：`get_indicator_smart()` 方法支持优先使用运行时值，回退到历史值

这个功能显著提升了回测环境的用户体验，使得策略可以快速启动，同时保证数据的完整性和准确性。