import { useState, useCallback, useRef } from 'react';
import { PriceLineType, OrderSide, ChartPriceLine } from '../types';
import { PriceLineManager } from '../utils/priceLineManager';
import { OrderService } from '../services/orderService';

interface UseAutoTrailingStopLossProps {
  priceLineManager: PriceLineManager | null;
  orderService: OrderService;
  defaultStopLossOffset?: number;
}

interface UseAutoTrailingStopLossReturn {
  // 状态
  stopLossOffset: number;
  autoTrailingEnabled: boolean;

  // 设置方法
  setStopLossOffset: (offset: number) => void;
  setAutoTrailingEnabled: (enabled: boolean) => void;

  // 操作方法
  updateStopLossOnPendingDrag: (orderId: string, newPendingPrice: number) => void;
  updateStopLossTakeProfitOnPendingDrag: (orderId: string, newPendingPrice: number, oldPendingPrice: number) => void;
  calculateStopLossPrice: (entryPrice: number, side: OrderSide) => number;
}

/**
 * 自动追踪止损Hook
 * 当拖动挂单线时，自动更新关联的止损线
 */
export function useAutoTrailingStopLoss({
  priceLineManager,
  orderService,
  defaultStopLossOffset = 50,
}: UseAutoTrailingStopLossProps): UseAutoTrailingStopLossReturn {
  // 止损点数
  const [stopLossOffset, setStopLossOffset] = useState(defaultStopLossOffset);
  const stopLossOffsetRef = useRef(defaultStopLossOffset);

  // 自动追踪开关
  const [autoTrailingEnabled, setAutoTrailingEnabled] = useState(true);
  const autoTrailingEnabledRef = useRef(true);

  // 更新ref
  const updateStopLossOffset = useCallback((offset: number) => {
    setStopLossOffset(offset);
    stopLossOffsetRef.current = offset;
  }, []);

  const updateAutoTrailingEnabled = useCallback((enabled: boolean) => {
    setAutoTrailingEnabled(enabled);
    autoTrailingEnabledRef.current = enabled;
  }, []);

  /**
   * 根据入场价和方向计算止损价
   */
  const calculateStopLossPrice = useCallback((entryPrice: number, side: OrderSide): number => {
    const offset = stopLossOffsetRef.current;
    if (side === OrderSide.BUY) {
      // 买入订单，止损在入场价下方
      return entryPrice - offset;
    } else {
      // 卖出订单，止损在入场价上方
      return entryPrice + offset;
    }
  }, []);

  /**
   * 当拖动挂单线时更新止损线
   */
  const updateStopLossOnPendingDrag = useCallback((orderId: string, newPendingPrice: number) => {
    // 检查是否启用自动追踪
    if (!autoTrailingEnabledRef.current) {
      return;
    }

    if (!priceLineManager) {
      return;
    }

    // 获取订单信息
    const order = orderService.getOrder(orderId);
    if (!order) {
      return;
    }

    // 计算新的止损价
    const newStopLossPrice = calculateStopLossPrice(newPendingPrice, order.side);

    // 获取该订单的所有价格线
    const orderLines = priceLineManager.getLinesByOrderId(orderId);
    
    // 查找止损线
    const stopLossLine = orderLines.find(line => line.type === PriceLineType.STOP_LOSS);

    if (stopLossLine) {
      // 更新现有止损线
      priceLineManager.updateLine(stopLossLine.id, {
        price: newStopLossPrice,
        title: `止损 @ ${newStopLossPrice.toFixed(0)}`,
      });
    } else {
      // 创建新的止损线
      priceLineManager.createStopLossLine({
        orderId: orderId,
        price: newStopLossPrice,
        side: order.side,
      });
    }

    // 同时更新订单的止损价
    orderService.updateOrder({
      id: orderId,
      stopLoss: newStopLossPrice,
    });
  }, [priceLineManager, orderService, calculateStopLossPrice]);

  /**
   * 当拖动挂单线时同时更新止损线和止盈线（保持相对偏移量不变）
   * @param orderId 订单ID
   * @param newPendingPrice 新的挂单价格
   * @param oldPendingPrice 旧的挂单价格（用于计算偏移量）
   */
  const updateStopLossTakeProfitOnPendingDrag = useCallback((orderId: string, newPendingPrice: number, oldPendingPrice: number) => {
    if (!priceLineManager) {
      return;
    }

    // 获取订单信息
    const order = orderService.getOrder(orderId);
    if (!order) {
      return;
    }

    // 计算价格变化量
    const priceDelta = newPendingPrice - oldPendingPrice;
    
    // 获取该订单的所有价格线
    const orderLines = priceLineManager.getLinesByOrderId(orderId);
    
    // 查找止损线
    const stopLossLine = orderLines.find(line => line.type === PriceLineType.STOP_LOSS);
    // 查找止盈线
    const takeProfitLine = orderLines.find(line => line.type === PriceLineType.TAKE_PROFIT);

    // 更新止损线（保持相对偏移量）
    if (stopLossLine) {
      const newStopLossPrice = stopLossLine.price + priceDelta;
      priceLineManager.updateLine(stopLossLine.id, {
        price: newStopLossPrice,
        title: `止损 @ ${newStopLossPrice.toFixed(0)}`,
      });
      // 更新订单的止损价
      orderService.updateOrder({
        id: orderId,
        stopLoss: newStopLossPrice,
      });
    }

    // 更新止盈线（保持相对偏移量）
    if (takeProfitLine) {
      const newTakeProfitPrice = takeProfitLine.price + priceDelta;
      priceLineManager.updateLine(takeProfitLine.id, {
        price: newTakeProfitPrice,
        title: `止盈 @ ${newTakeProfitPrice.toFixed(0)}`,
      });
      // 更新订单的止盈价
      orderService.updateOrder({
        id: orderId,
        takeProfit: newTakeProfitPrice,
      });
    }
  }, [priceLineManager, orderService]);

  return {
    stopLossOffset,
    autoTrailingEnabled,
    setStopLossOffset: updateStopLossOffset,
    setAutoTrailingEnabled: updateAutoTrailingEnabled,
    updateStopLossOnPendingDrag,
    updateStopLossTakeProfitOnPendingDrag,
    calculateStopLossPrice,
  };
}

