import { useState, useCallback, useRef } from 'react'
import { PriceLineType, OrderSide, ChartPriceLine } from '../types'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'

interface UseEChartsDualStopLossProps {
  priceLineManager: EChartsPriceLineManager | null
  lagFactor?: number // 滞后系数，0-1之间，默认0.3表示影子线移动速度是主线的30%
  onShadowStopLossTriggered?: (orderId: string, triggerPrice: number) => void // 当价格突破影子止损线时触发
}

interface UseEChartsDualStopLossReturn {
  // 状态
  isDraggingStopLoss: boolean
  isProtectionActive: boolean
  originalPrice: number | null
  currentPrice: number | null
  shadowPrice: number | null // 影子线当前价格
  shadowLineId: string | null
  draggingLineId: string | null
  draggingOrderId: string | null // 正在拖拽的订单ID

  // 操作方法
  startDragStopLoss: (stopLossLine: ChartPriceLine, orderSide: OrderSide) => void
  updateDragStopLoss: (newPrice: number) => void
  confirmDragStopLoss: () => number | null
  cancelDragStopLoss: () => void
  checkShadowStopLossBreached: (marketPrice: number) => boolean // 检查市场价是否突破影子止损
}

/**
 * ECharts双止损保护Hook
 * 当拖动止损线时，自动创建一条"影子止损线"保留原始止损位置作为保护
 * 影子止损线会滞后跟随主止损线移动，提供缓冲保护
 * 当价格突破影子止损线时，立即触发平仓操作
 */
export function useEChartsDualStopLoss({
  priceLineManager,
  lagFactor = 0.3, // 默认滞后系数0.3，影子线移动速度是主线的30%
  onShadowStopLossTriggered,
}: UseEChartsDualStopLossProps): UseEChartsDualStopLossReturn {
  // 拖动状态
  const [isDraggingStopLoss, setIsDraggingStopLoss] = useState(false)
  const [originalPrice, setOriginalPrice] = useState<number | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [shadowPrice, setShadowPrice] = useState<number | null>(null)
  const [shadowLineId, setShadowLineId] = useState<string | null>(null)
  const [draggingLineId, setDraggingLineId] = useState<string | null>(null)
  const [draggingOrderId, setDraggingOrderId] = useState<string | null>(null)

  // 使用ref避免闭包问题
  const isDraggingRef = useRef(false)
  const originalPriceRef = useRef<number | null>(null)
  const currentPriceRef = useRef<number | null>(null)
  const shadowPriceRef = useRef<number | null>(null)
  const shadowLineIdRef = useRef<string | null>(null)
  const draggingLineIdRef = useRef<string | null>(null)
  const draggingOrderIdRef = useRef<string | null>(null)
  const orderSideRef = useRef<OrderSide | null>(null)
  const lagFactorRef = useRef(lagFactor)
  const onShadowStopLossTriggeredRef = useRef(onShadowStopLossTriggered)

  // 保护状态：当正在拖动且有影子线时，保护激活
  const isProtectionActive = isDraggingStopLoss && shadowLineId !== null

  /**
   * 开始拖动止损线
   */
  const startDragStopLoss = useCallback((stopLossLine: ChartPriceLine, orderSide: OrderSide) => {
    if (!priceLineManager) return

    // 如果已经有影子线，先删除它（防止重复创建）
    const existingShadowId = shadowLineIdRef.current
    if (existingShadowId) {
      priceLineManager.removeLine(existingShadowId)
      shadowLineIdRef.current = null
      setShadowLineId(null)
    }

    // 保存原始信息
    const origPrice = stopLossLine.price
    const orderId = stopLossLine.orderId || ''
    setOriginalPrice(origPrice)
    setCurrentPrice(origPrice)
    setShadowPrice(origPrice)
    setDraggingLineId(stopLossLine.id)
    setDraggingOrderId(orderId)
    setIsDraggingStopLoss(true)

    originalPriceRef.current = origPrice
    currentPriceRef.current = origPrice
    shadowPriceRef.current = origPrice
    draggingLineIdRef.current = stopLossLine.id
    draggingOrderIdRef.current = orderId
    isDraggingRef.current = true
    orderSideRef.current = orderSide

    // 创建影子止损线（半透明，点线样式）
    const shadowColor = '#ffa50280' // 橙色半透明
    const shadowLine = priceLineManager.createPriceLine({
      id: `shadow_${stopLossLine.id}_${Date.now()}`,
      orderId: stopLossLine.orderId,
      type: PriceLineType.SHADOW,
      price: origPrice,
      color: shadowColor,
      lineWidth: 1,
      lineStyle: 'dotted',
      title: `保护止损 @ ${origPrice.toFixed(0)}`,
      draggable: false, // 影子线不可拖动
    })

    setShadowLineId(shadowLine.id)
    shadowLineIdRef.current = shadowLine.id

    console.log('🛡️ ECharts Dual stop loss protection activated:', {
      originalPrice: origPrice,
      shadowLineId: shadowLine.id,
    })
  }, [priceLineManager])

  /**
   * 更新拖动位置
   * 影子止损线会滞后跟随，移动速度是主止损线的 lagFactor 倍
   */
  const updateDragStopLoss = useCallback((newPrice: number) => {
    if (!isDraggingRef.current || !priceLineManager) return

    const origPrice = originalPriceRef.current
    const shadowId = shadowLineIdRef.current
    const draggingId = draggingLineIdRef.current
    const currentShadowPrice = shadowPriceRef.current

    if (origPrice === null || currentShadowPrice === null) return

    setCurrentPrice(newPrice)
    currentPriceRef.current = newPrice

    // 更新主止损线位置
    if (draggingId) {
      priceLineManager.updateLine(draggingId, {
        price: newPrice,
        title: `止损 @ ${newPrice.toFixed(0)}`,
      })
    }

    // 计算影子线的新位置（滞后跟随）
    // 影子线朝着主止损线移动，但速度更慢
    const priceDelta = newPrice - currentShadowPrice
    const newShadowPrice = currentShadowPrice + priceDelta * lagFactorRef.current

    // 更新影子线位置
    if (shadowId) {
      setShadowPrice(newShadowPrice)
      shadowPriceRef.current = newShadowPrice

      priceLineManager.updateLine(shadowId, {
        price: newShadowPrice,
        title: `保护止损 @ ${newShadowPrice.toFixed(0)}`,
      })
    }
  }, [priceLineManager])

  /**
   * 确认拖动（删除影子线，确认新止损位置）
   */
  const confirmDragStopLoss = useCallback((): number | null => {
    if (!priceLineManager) return null

    const confirmedPrice = currentPriceRef.current
    const shadowId = shadowLineIdRef.current

    // 删除影子线（无论是否正在拖动，只要有影子线就删除）
    if (shadowId) {
      priceLineManager.removeLine(shadowId)
    }

    // 如果不是正在拖动状态，直接返回
    if (!isDraggingRef.current) {
      // 清理可能遗留的影子线ID
      setShadowLineId(null)
      shadowLineIdRef.current = null
      return confirmedPrice
    }

    // 重置状态
    setIsDraggingStopLoss(false)
    setOriginalPrice(null)
    setCurrentPrice(null)
    setShadowPrice(null)
    setShadowLineId(null)
    setDraggingLineId(null)
    setDraggingOrderId(null)

    isDraggingRef.current = false
    originalPriceRef.current = null
    currentPriceRef.current = null
    shadowPriceRef.current = null
    shadowLineIdRef.current = null
    draggingLineIdRef.current = null
    draggingOrderIdRef.current = null
    orderSideRef.current = null

    return confirmedPrice
  }, [priceLineManager])

  /**
   * 取消拖动（恢复原始止损位置，删除影子线）
   */
  const cancelDragStopLoss = useCallback(() => {
    if (!priceLineManager) return

    const origPrice = originalPriceRef.current
    const shadowId = shadowLineIdRef.current
    const lineId = draggingLineIdRef.current

    // 删除影子线（无论是否正在拖动，只要有影子线就删除）
    if (shadowId) {
      priceLineManager.removeLine(shadowId)
    }

    // 恢复主止损线到原始位置
    if (lineId && origPrice !== null) {
      priceLineManager.updateLine(lineId, {
        price: origPrice,
        title: `止损 @ ${origPrice.toFixed(0)}`,
      })
    }

    // 重置状态
    setIsDraggingStopLoss(false)
    setOriginalPrice(null)
    setCurrentPrice(null)
    setShadowPrice(null)
    setShadowLineId(null)
    setDraggingLineId(null)
    setDraggingOrderId(null)

    isDraggingRef.current = false
    originalPriceRef.current = null
    currentPriceRef.current = null
    shadowPriceRef.current = null
    shadowLineIdRef.current = null
    draggingLineIdRef.current = null
    draggingOrderIdRef.current = null
    orderSideRef.current = null
  }, [priceLineManager])

  /**
   * 检查市场价是否突破影子止损线
   * 如果突破，触发平仓回调并返回true
   * @param marketPrice 当前市场价格
   * @returns 是否触发了止损
   */
  const checkShadowStopLossBreached = useCallback((marketPrice: number): boolean => {
    if (!isDraggingRef.current) return false
    
    const shadowCurrentPrice = shadowPriceRef.current
    const orderSide = orderSideRef.current
    const orderId = draggingOrderIdRef.current
    
    if (shadowCurrentPrice === null || orderSide === null || !orderId) return false
    
    let breached = false
    
    // 多单：市场价跌破影子止损价
    // 空单：市场价涨破影子止损价
    if (orderSide === OrderSide.BUY) {
      breached = marketPrice <= shadowCurrentPrice
    } else {
      breached = marketPrice >= shadowCurrentPrice
    }
    
    if (breached) {
      // 触发平仓回调
      if (onShadowStopLossTriggeredRef.current) {
        onShadowStopLossTriggeredRef.current(orderId, marketPrice)
      }
      
      // 清理状态
      cancelDragStopLoss()
      
      // 显示提示
      alert(`⚠️ 影子止损触发！\n\n市场价格 ${marketPrice.toFixed(0)} 已突破保护止损价 ${shadowCurrentPrice.toFixed(0)}\n订单已自动平仓`)
    }
    
    return breached
  }, [cancelDragStopLoss])

  return {
    isDraggingStopLoss,
    isProtectionActive,
    originalPrice,
    currentPrice,
    shadowPrice,
    shadowLineId,
    draggingLineId,
    draggingOrderId,
    startDragStopLoss,
    updateDragStopLoss,
    confirmDragStopLoss,
    cancelDragStopLoss,
    checkShadowStopLossBreached,
  }
}

