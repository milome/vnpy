// Timeframe enum for different K-line periods
export enum Timeframe {
  ONE_MINUTE = '1min',
  FIVE_MINUTES = '5min',
  ONE_HOUR = '1hour',
  FOUR_HOURS = '4hour',
  ONE_DAY = '1day'
}

// K-line data structure from CSV
export interface KLineData {
  symbol: string;
  exchange: string;
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
  open_interest: number;
}

// Normalized K-line data for chart rendering
export interface ChartKLineData {
  timestamp: number;  // Unix timestamp
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  midpointTimestamp?: number;  // 可选：K线数量中点的时间戳（用于绘制影线）
}

// Chart configuration for each timeframe
export interface TimeframeConfig {
  timeframe: Timeframe;
  lineWidth: number;
  opacity: number;
  zIndex: number;
}

// CSV parsing result
export interface CSVParseResult {
  data: KLineData[];
  error?: Error;
}

// Trading order types
export enum OrderSide {
  BUY = 'buy',
  SELL = 'sell'
}

export enum OrderStatus {
  PENDING = 'pending',
  FILLED = 'filled',
  CANCELLED = 'cancelled'
}

// Trading order
export interface TradingOrder {
  id: string;
  side: OrderSide;
  price: number;
  quantity: number;
  stopLoss?: number;
  takeProfit?: number;
  status: OrderStatus;
  filledPrice?: number;
  filledTime?: number;
  createdTime: number;
}

// Drawing mode for line-based ordering
export enum DrawingMode {
  NONE = 'none',
  PENDING = 'pending',            // 挂单画线模式
  ORDER_LINE = 'order_line',      // 画线下单模式
  STOP_LOSS_LINE = 'stop_loss',   // 设置止损模式
  TAKE_PROFIT_LINE = 'take_profit' // 设置止盈模式
}

// Price line types for visualization
export enum PriceLineType {
  ENTRY = 'entry',           // 入场价格线
  STOP_LOSS = 'stop_loss',   // 止损线
  TAKE_PROFIT = 'take_profit', // 止盈线
  PENDING = 'pending',       // 挂单线
  PREVIEW = 'preview'        // 预览线（鼠标移动时）
}

// Price line configuration
export interface ChartPriceLine {
  id: string;
  orderId?: string;          // 关联的订单ID
  type: PriceLineType;
  price: number;
  color: string;
  lineWidth: number;
  lineStyle: 'solid' | 'dashed' | 'dotted';
  title?: string;            // 显示的标签文字
  draggable?: boolean;       // 是否可拖拽
}

// Order marker on chart (for filled orders)
export interface OrderMarker {
  id: string;
  orderId: string;
  time: number;              // Unix timestamp
  price: number;
  side: OrderSide;
  quantity: number;
  text?: string;
}

// Order creation request (from drawing)
export interface CreateOrderRequest {
  side: OrderSide;
  price: number;
  quantity: number;
  stopLoss?: number;
  takeProfit?: number;
}

// Order update request
export interface UpdateOrderRequest {
  id: string;
  price?: number;           // 挂单价格（移动挂单线时更新）
  stopLoss?: number;
  takeProfit?: number;
}

// Callback types for order events
export type OrderCreatedCallback = (order: TradingOrder) => void;
export type OrderFilledCallback = (order: TradingOrder) => void;
export type OrderCancelledCallback = (orderId: string) => void;
export type OrderUpdatedCallback = (order: TradingOrder) => void;
