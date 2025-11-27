import {
  TradingOrder,
  OrderSide,
  OrderStatus,
  CreateOrderRequest,
  UpdateOrderRequest,
  OrderCreatedCallback,
  OrderFilledCallback,
  OrderCancelledCallback,
  OrderUpdatedCallback,
} from '../types';

/**
 * 订单管理服务
 * 负责创建、查询、更新、取消订单
 */
export class OrderService {
  private orders: Map<string, TradingOrder> = new Map();
  private orderIdCounter = 0;

  // 回调函数
  private onOrderCreatedCallbacks: OrderCreatedCallback[] = [];
  private onOrderFilledCallbacks: OrderFilledCallback[] = [];
  private onOrderCancelledCallbacks: OrderCancelledCallback[] = [];
  private onOrderUpdatedCallbacks: OrderUpdatedCallback[] = [];

  /**
   * 生成唯一订单ID
   */
  private generateOrderId(): string {
    this.orderIdCounter++;
    return `order_${Date.now()}_${this.orderIdCounter}`;
  }

  /**
   * 创建新订单
   */
  createOrder(request: CreateOrderRequest): TradingOrder {
    const order: TradingOrder = {
      id: this.generateOrderId(),
      side: request.side,
      price: request.price,
      quantity: request.quantity,
      stopLoss: request.stopLoss,
      takeProfit: request.takeProfit,
      status: OrderStatus.PENDING,
      createdTime: Date.now(),
    };

    this.orders.set(order.id, order);

    // 触发回调
    this.onOrderCreatedCallbacks.forEach(cb => cb(order));

    return order;
  }

  /**
   * 根据ID获取订单
   */
  getOrder(id: string): TradingOrder | undefined {
    return this.orders.get(id);
  }

  /**
   * 获取所有订单
   */
  getAllOrders(): TradingOrder[] {
    return Array.from(this.orders.values());
  }

  /**
   * 获取所有挂单（待成交订单）
   */
  getPendingOrders(): TradingOrder[] {
    return this.getAllOrders().filter(order => order.status === OrderStatus.PENDING);
  }

  /**
   * 获取所有已成交订单
   */
  getFilledOrders(): TradingOrder[] {
    return this.getAllOrders().filter(order => order.status === OrderStatus.FILLED);
  }

  /**
   * 成交订单
   */
  fillOrder(id: string, filledPrice: number): TradingOrder | undefined {
    const order = this.orders.get(id);
    if (!order) return undefined;

    // 已成交的订单不能重复成交
    if (order.status === OrderStatus.FILLED) {
      return order;
    }

    order.status = OrderStatus.FILLED;
    order.filledPrice = filledPrice;
    order.filledTime = Date.now();

    // 触发回调
    this.onOrderFilledCallbacks.forEach(cb => cb(order));

    return order;
  }

  /**
   * 取消订单（未成交的挂单）
   */
  cancelOrder(id: string): boolean {
    const order = this.orders.get(id);
    if (!order) return false;

    // 已成交的订单不能取消
    if (order.status === OrderStatus.FILLED) {
      return false;
    }

    order.status = OrderStatus.CANCELLED;

    // 触发回调
    this.onOrderCancelledCallbacks.forEach(cb => cb(id));

    return true;
  }

  /**
   * 平仓（已成交的订单）
   * 平仓后订单从列表中移除
   */
  closePosition(id: string, closePrice?: number): TradingOrder | undefined {
    const order = this.orders.get(id);
    if (!order) return undefined;

    // 只有已成交的订单才能平仓
    if (order.status !== OrderStatus.FILLED) {
      return undefined;
    }

    // 记录平仓信息（可选）
    const closedOrder = { ...order, closePrice, closeTime: Date.now() };

    // 从订单列表中移除
    this.orders.delete(id);

    // 触发取消回调（通知UI更新）
    this.onOrderCancelledCallbacks.forEach(cb => cb(id));

    console.log('📕 Position closed:', closedOrder);
    return closedOrder;
  }

  /**
   * 移除订单（用于清理）
   */
  removeOrder(id: string): boolean {
    const existed = this.orders.has(id);
    this.orders.delete(id);
    
    if (existed) {
      this.onOrderCancelledCallbacks.forEach(cb => cb(id));
    }
    
    return existed;
  }

  /**
   * 更新订单（价格/止损/止盈）
   */
  updateOrder(request: UpdateOrderRequest): TradingOrder | undefined {
    const order = this.orders.get(request.id);
    if (!order) return undefined;

    // 只有未成交的挂单才能更新价格
    if (request.price !== undefined && order.status === OrderStatus.PENDING) {
      order.price = request.price;
    }
    if (request.stopLoss !== undefined) {
      order.stopLoss = request.stopLoss;
    }
    if (request.takeProfit !== undefined) {
      order.takeProfit = request.takeProfit;
    }

    // 触发回调
    this.onOrderUpdatedCallbacks.forEach(cb => cb(order));

    return order;
  }

  /**
   * 清除所有订单
   */
  clearAllOrders(): void {
    this.orders.clear();
  }

  // 事件订阅方法
  onOrderCreated(callback: OrderCreatedCallback): void {
    this.onOrderCreatedCallbacks.push(callback);
  }

  onOrderFilled(callback: OrderFilledCallback): void {
    this.onOrderFilledCallbacks.push(callback);
  }

  onOrderCancelled(callback: OrderCancelledCallback): void {
    this.onOrderCancelledCallbacks.push(callback);
  }

  onOrderUpdated(callback: OrderUpdatedCallback): void {
    this.onOrderUpdatedCallbacks.push(callback);
  }

  // 移除事件订阅
  offOrderCreated(callback: OrderCreatedCallback): void {
    const index = this.onOrderCreatedCallbacks.indexOf(callback);
    if (index > -1) {
      this.onOrderCreatedCallbacks.splice(index, 1);
    }
  }

  offOrderFilled(callback: OrderFilledCallback): void {
    const index = this.onOrderFilledCallbacks.indexOf(callback);
    if (index > -1) {
      this.onOrderFilledCallbacks.splice(index, 1);
    }
  }

  offOrderCancelled(callback: OrderCancelledCallback): void {
    const index = this.onOrderCancelledCallbacks.indexOf(callback);
    if (index > -1) {
      this.onOrderCancelledCallbacks.splice(index, 1);
    }
  }

  offOrderUpdated(callback: OrderUpdatedCallback): void {
    const index = this.onOrderUpdatedCallbacks.indexOf(callback);
    if (index > -1) {
      this.onOrderUpdatedCallbacks.splice(index, 1);
    }
  }
}

// 单例实例
export const orderService = new OrderService();

