import { describe, it, expect, beforeEach, vi } from 'vitest';
import { OrderService } from '../services/orderService';
import { OrderSide, OrderStatus, CreateOrderRequest } from '../types';

describe('OrderService', () => {
  let orderService: OrderService;

  beforeEach(() => {
    orderService = new OrderService();
  });

  describe('createOrder', () => {
    it('should create a pending order with correct properties', () => {
      const request: CreateOrderRequest = {
        side: OrderSide.BUY,
        price: 21000,
        quantity: 2,
      };

      const order = orderService.createOrder(request);

      expect(order.id).toBeDefined();
      expect(order.side).toBe(OrderSide.BUY);
      expect(order.price).toBe(21000);
      expect(order.quantity).toBe(2);
      expect(order.status).toBe(OrderStatus.PENDING);
      expect(order.createdTime).toBeDefined();
    });

    it('should create order with stop loss', () => {
      const request: CreateOrderRequest = {
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        stopLoss: 20950,
      };

      const order = orderService.createOrder(request);

      expect(order.stopLoss).toBe(20950);
    });

    it('should create order with take profit', () => {
      const request: CreateOrderRequest = {
        side: OrderSide.SELL,
        price: 21000,
        quantity: 1,
        takeProfit: 20900,
      };

      const order = orderService.createOrder(request);

      expect(order.takeProfit).toBe(20900);
    });

    it('should generate unique IDs for each order', () => {
      const order1 = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      const order2 = orderService.createOrder({
        side: OrderSide.SELL,
        price: 21100,
        quantity: 1,
      });

      expect(order1.id).not.toBe(order2.id);
    });
  });

  describe('getOrder', () => {
    it('should return the order by id', () => {
      const created = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });

      const retrieved = orderService.getOrder(created.id);

      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe(created.id);
    });

    it('should return undefined for non-existent order', () => {
      const retrieved = orderService.getOrder('non-existent-id');

      expect(retrieved).toBeUndefined();
    });
  });

  describe('getAllOrders', () => {
    it('should return all orders', () => {
      orderService.createOrder({ side: OrderSide.BUY, price: 21000, quantity: 1 });
      orderService.createOrder({ side: OrderSide.SELL, price: 21100, quantity: 2 });

      const orders = orderService.getAllOrders();

      expect(orders).toHaveLength(2);
    });

    it('should return empty array when no orders', () => {
      const orders = orderService.getAllOrders();

      expect(orders).toHaveLength(0);
    });
  });

  describe('getPendingOrders', () => {
    it('should return only pending orders', () => {
      const order1 = orderService.createOrder({ side: OrderSide.BUY, price: 21000, quantity: 1 });
      orderService.createOrder({ side: OrderSide.SELL, price: 21100, quantity: 2 });
      orderService.fillOrder(order1.id, 21000);

      const pendingOrders = orderService.getPendingOrders();

      expect(pendingOrders).toHaveLength(1);
      expect(pendingOrders[0].status).toBe(OrderStatus.PENDING);
    });
  });

  describe('getFilledOrders', () => {
    it('should return only filled orders', () => {
      const order1 = orderService.createOrder({ side: OrderSide.BUY, price: 21000, quantity: 1 });
      orderService.createOrder({ side: OrderSide.SELL, price: 21100, quantity: 2 });
      orderService.fillOrder(order1.id, 21000);

      const filledOrders = orderService.getFilledOrders();

      expect(filledOrders).toHaveLength(1);
      expect(filledOrders[0].status).toBe(OrderStatus.FILLED);
    });
  });

  describe('fillOrder', () => {
    it('should mark order as filled with filled price and time', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });

      const filled = orderService.fillOrder(order.id, 20995);

      expect(filled).toBeDefined();
      expect(filled?.status).toBe(OrderStatus.FILLED);
      expect(filled?.filledPrice).toBe(20995);
      expect(filled?.filledTime).toBeDefined();
    });

    it('should return undefined for non-existent order', () => {
      const filled = orderService.fillOrder('non-existent', 21000);

      expect(filled).toBeUndefined();
    });

    it('should not fill already filled order', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      orderService.fillOrder(order.id, 21000);

      const secondFill = orderService.fillOrder(order.id, 21100);

      expect(secondFill?.filledPrice).toBe(21000); // Original fill price
    });
  });

  describe('cancelOrder', () => {
    it('should mark order as cancelled', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });

      const success = orderService.cancelOrder(order.id);

      expect(success).toBe(true);
      expect(orderService.getOrder(order.id)?.status).toBe(OrderStatus.CANCELLED);
    });

    it('should return false for non-existent order', () => {
      const success = orderService.cancelOrder('non-existent');

      expect(success).toBe(false);
    });

    it('should not cancel already filled order', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      orderService.fillOrder(order.id, 21000);

      const success = orderService.cancelOrder(order.id);

      expect(success).toBe(false);
      expect(orderService.getOrder(order.id)?.status).toBe(OrderStatus.FILLED);
    });
  });

  describe('updateOrder', () => {
    it('should update stop loss', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        stopLoss: 20950,
      });

      const updated = orderService.updateOrder({
        id: order.id,
        stopLoss: 20900,
      });

      expect(updated?.stopLoss).toBe(20900);
    });

    it('should update take profit', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });

      const updated = orderService.updateOrder({
        id: order.id,
        takeProfit: 21100,
      });

      expect(updated?.takeProfit).toBe(21100);
    });

    it('should return undefined for non-existent order', () => {
      const updated = orderService.updateOrder({
        id: 'non-existent',
        stopLoss: 20900,
      });

      expect(updated).toBeUndefined();
    });
  });

  describe('event callbacks', () => {
    it('should call onOrderCreated callback when order is created', () => {
      const callback = vi.fn();
      orderService.onOrderCreated(callback);

      orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });

      expect(callback).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledWith(expect.objectContaining({
        side: OrderSide.BUY,
        price: 21000,
      }));
    });

    it('should call onOrderFilled callback when order is filled', () => {
      const callback = vi.fn();
      orderService.onOrderFilled(callback);

      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      orderService.fillOrder(order.id, 21000);

      expect(callback).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledWith(expect.objectContaining({
        status: OrderStatus.FILLED,
        filledPrice: 21000,
      }));
    });

    it('should call onOrderCancelled callback when order is cancelled', () => {
      const callback = vi.fn();
      orderService.onOrderCancelled(callback);

      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      orderService.cancelOrder(order.id);

      expect(callback).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledWith(order.id);
    });

    it('should call onOrderUpdated callback when order is updated', () => {
      const callback = vi.fn();
      orderService.onOrderUpdated(callback);

      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
      });
      orderService.updateOrder({ id: order.id, stopLoss: 20900 });

      expect(callback).toHaveBeenCalledTimes(1);
      expect(callback).toHaveBeenCalledWith(expect.objectContaining({
        stopLoss: 20900,
      }));
    });
  });

  describe('clearAllOrders', () => {
    it('should remove all orders', () => {
      orderService.createOrder({ side: OrderSide.BUY, price: 21000, quantity: 1 });
      orderService.createOrder({ side: OrderSide.SELL, price: 21100, quantity: 2 });

      orderService.clearAllOrders();

      expect(orderService.getAllOrders()).toHaveLength(0);
    });
  });
});


