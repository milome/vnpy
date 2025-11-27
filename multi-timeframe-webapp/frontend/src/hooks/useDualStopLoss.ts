import { useState, useCallback, useRef } from 'react';
import { PriceLineType, OrderSide, ChartPriceLine } from '../types';
import { PriceLineManager } from '../utils/priceLineManager';

interface UseDualStopLossProps {
  priceLineManager: PriceLineManager | null;
  lagFactor?: number; // 滞后系数，0-1之间，默认0.3表示影子线移动速度是主线的30%
}

interface UseDualStopLossReturn {
  // 状态
  isDraggingStopLoss: boolean;
  isProtectionActive: boolean;
  originalPrice: number | null;
  currentPrice: number | null;
  shadowPrice: number | null; // 影子线当前价格
  shadowLineId: string | null;
  draggingLineId: string | null;

  // 操作方法
  startDragStopLoss: (stopLossLine: ChartPriceLine, orderSide: OrderSide) => void;
  updateDragStopLoss: (newPrice: number) => void;
  confirmDragStopLoss: () => number | null;
  cancelDragStopLoss: () => void;
}

/**
 * 双止损保护Hook
 * 当拖动止损线时，自动创建一条"影子止损线"保留原始止损位置作为保护
 * 影子止损线会滞后跟随主止损线移动，提供缓冲保护
 */
export function useDualStopLoss({
  priceLineManager,
  lagFactor = 0.3, // 默认滞后系数0.3，影子线移动速度是主线的30%
}: UseDualStopLossProps): UseDualStopLossReturn {
  // 拖动状态
  const [isDraggingStopLoss, setIsDraggingStopLoss] = useState(false);
  const [originalPrice, setOriginalPrice] = useState<number | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [shadowPrice, setShadowPrice] = useState<number | null>(null);
  const [shadowLineId, setShadowLineId] = useState<string | null>(null);
  const [draggingLineId, setDraggingLineId] = useState<string | null>(null);

  // 使用ref避免闭包问题
  const isDraggingRef = useRef(false);
  const originalPriceRef = useRef<number | null>(null);
  const currentPriceRef = useRef<number | null>(null);
  const shadowPriceRef = useRef<number | null>(null);
  const shadowLineIdRef = useRef<string | null>(null);
  const draggingLineIdRef = useRef<string | null>(null);
  const orderSideRef = useRef<OrderSide | null>(null);
  const lagFactorRef = useRef(lagFactor);

  // 保护状态：当正在拖动且有影子线时，保护激活
  const isProtectionActive = isDraggingStopLoss && shadowLineId !== null;

  /**
   * 开始拖动止损线
   */
  const startDragStopLoss = useCallback((stopLossLine: ChartPriceLine, orderSide: OrderSide) => {
    if (!priceLineManager) return;

    // 保存原始信息
    const origPrice = stopLossLine.price;
    setOriginalPrice(origPrice);
    setCurrentPrice(origPrice);
    setShadowPrice(origPrice);
    setDraggingLineId(stopLossLine.id);
    setIsDraggingStopLoss(true);

    originalPriceRef.current = origPrice;
    currentPriceRef.current = origPrice;
    shadowPriceRef.current = origPrice;
    draggingLineIdRef.current = stopLossLine.id;
    isDraggingRef.current = true;
    orderSideRef.current = orderSide;

    // 创建影子止损线（半透明，点线样式）
    const shadowColor = '#ffa50280'; // 橙色半透明
    const shadowLine = priceLineManager.createPriceLine({
      id: `shadow_${stopLossLine.id}_${Date.now()}`,
      orderId: stopLossLine.orderId,
      type: PriceLineType.STOP_LOSS,
      price: origPrice,
      color: shadowColor,
      lineWidth: 1,
      lineStyle: 'dotted',
      title: `保护止损 @ ${origPrice.toFixed(0)}`,
      draggable: false, // 影子线不可拖动
    });

    setShadowLineId(shadowLine.id);
    shadowLineIdRef.current = shadowLine.id;

    console.log('🛡️ Dual stop loss protection activated:', {
      originalPrice: origPrice,
      shadowLineId: shadowLine.id,
    });
  }, [priceLineManager]);

  /**
   * 更新拖动位置
   * 影子止损线会滞后跟随，移动速度是主止损线的 lagFactor 倍
   */
  const updateDragStopLoss = useCallback((newPrice: number) => {
    if (!isDraggingRef.current || !priceLineManager) return;

    const origPrice = originalPriceRef.current;
    const shadowId = shadowLineIdRef.current;
    const currentShadowPrice = shadowPriceRef.current;

    if (origPrice === null || currentShadowPrice === null) return;

    setCurrentPrice(newPrice);
    currentPriceRef.current = newPrice;

    // 计算影子线的新位置（滞后跟随）
    // 影子线朝着主止损线移动，但速度更慢
    const priceDelta = newPrice - currentShadowPrice;
    const newShadowPrice = currentShadowPrice + priceDelta * lagFactorRef.current;

    // 更新影子线位置
    if (shadowId) {
      setShadowPrice(newShadowPrice);
      shadowPriceRef.current = newShadowPrice;

      priceLineManager.updateLine(shadowId, {
        price: newShadowPrice,
        title: `保护止损 @ ${newShadowPrice.toFixed(0)}`,
      });
    }
  }, [priceLineManager]);

  /**
   * 确认拖动（删除影子线，确认新止损位置）
   */
  const confirmDragStopLoss = useCallback((): number | null => {
    if (!isDraggingRef.current || !priceLineManager) return null;

    const confirmedPrice = currentPriceRef.current;
    const shadowId = shadowLineIdRef.current;

    // 删除影子线
    if (shadowId) {
      priceLineManager.removeLine(shadowId);
    }

    console.log('✅ Dual stop loss confirmed:', {
      originalPrice: originalPriceRef.current,
      newPrice: confirmedPrice,
      finalShadowPrice: shadowPriceRef.current,
    });

    // 重置状态
    setIsDraggingStopLoss(false);
    setOriginalPrice(null);
    setCurrentPrice(null);
    setShadowPrice(null);
    setShadowLineId(null);
    setDraggingLineId(null);

    isDraggingRef.current = false;
    originalPriceRef.current = null;
    currentPriceRef.current = null;
    shadowPriceRef.current = null;
    shadowLineIdRef.current = null;
    draggingLineIdRef.current = null;
    orderSideRef.current = null;

    return confirmedPrice;
  }, [priceLineManager]);

  /**
   * 取消拖动（恢复原始止损位置，删除影子线）
   */
  const cancelDragStopLoss = useCallback(() => {
    if (!isDraggingRef.current || !priceLineManager) return;

    const origPrice = originalPriceRef.current;
    const shadowId = shadowLineIdRef.current;
    const lineId = draggingLineIdRef.current;

    // 删除影子线
    if (shadowId) {
      priceLineManager.removeLine(shadowId);
    }

    // 恢复主止损线到原始位置
    if (lineId && origPrice !== null) {
      priceLineManager.updateLine(lineId, {
        price: origPrice,
        title: `止损 @ ${origPrice.toFixed(0)}`,
      });
    }

    console.log('↩️ Dual stop loss cancelled, restored to:', origPrice);

    // 重置状态
    setIsDraggingStopLoss(false);
    setOriginalPrice(null);
    setCurrentPrice(null);
    setShadowPrice(null);
    setShadowLineId(null);
    setDraggingLineId(null);

    isDraggingRef.current = false;
    originalPriceRef.current = null;
    currentPriceRef.current = null;
    shadowPriceRef.current = null;
    shadowLineIdRef.current = null;
    draggingLineIdRef.current = null;
    orderSideRef.current = null;
  }, [priceLineManager]);

  return {
    isDraggingStopLoss,
    isProtectionActive,
    originalPrice,
    currentPrice,
    shadowPrice,
    shadowLineId,
    draggingLineId,
    startDragStopLoss,
    updateDragStopLoss,
    confirmDragStopLoss,
    cancelDragStopLoss,
  };
}

