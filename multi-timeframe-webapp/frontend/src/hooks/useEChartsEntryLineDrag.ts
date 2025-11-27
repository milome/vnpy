import { useState, useCallback, useRef } from 'react'
import type { EChartsType } from 'echarts'
import { ChartPriceLine, PriceLineType, OrderSide } from '../types'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { OrderService } from '../services/orderService'
import { priceToPixelY, pixelYToPrice } from '../utils/echartsCrosshairHelper'

interface UseEChartsEntryLineDragProps {
  priceLineManager: EChartsPriceLineManager | null
  orderService: OrderService
  getChart: () => EChartsType | null
  dragThreshold?: number
}

type DragLineType = 'stop_loss' | 'take_profit' | null

interface UseEChartsEntryLineDragReturn {
  // 状态
  isCreatingFromEntry: boolean
  creatingLineType: DragLineType
  entryPrice: number | null
  currentPrice: number | null
  previewLineId: string | null

  // 方法
  findNearestEntryLine: (pixelY: number) => ChartPriceLine | undefined
  startCreateFromEntry: (entryLine: ChartPriceLine, startY: number) => void
  updateCreateFromEntry: (pixelY: number) => void
  confirmCreateFromEntry: () => boolean // 返回是否成功创建
  cancelCreateFromEntry: () => void
}

/**
 * ECharts从入场线拖拽创建止损/止盈线Hook
 * 根据拖拽方向自动判断创建止损还是止盈
 */
export function useEChartsEntryLineDrag({
  priceLineManager,
  orderService,
  getChart,
  dragThreshold = 10,
}: UseEChartsEntryLineDragProps): UseEChartsEntryLineDragReturn {
  // 状态
  const [isCreatingFromEntry, setIsCreatingFromEntry] = useState(false)
  const [creatingLineType, setCreatingLineType] = useState<DragLineType>(null)
  const [entryPrice, setEntryPrice] = useState<number | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [previewLineId, setPreviewLineId] = useState<string | null>(null)

  // Refs
  const isCreatingRef = useRef(false)
  const entryPriceRef = useRef<number | null>(null)
  const currentPriceRef = useRef<number | null>(null)
  const previewLineIdRef = useRef<string | null>(null)
  const orderIdRef = useRef<string | null>(null)
  const orderSideRef = useRef<OrderSide | null>(null)
  const creatingLineTypeRef = useRef<DragLineType>(null)
  const startYRef = useRef<number | null>(null) // 记录起始Y坐标，用于判断是否实际拖拽
  const hasDraggedRef = useRef(false) // 是否实际发生了拖拽
  const minDragDistance = 15 // 最小拖拽距离（像素），小于此距离视为点击而非拖拽

  /**
   * 查找最近的入场线
   */
  const findNearestEntryLine = useCallback((pixelY: number): ChartPriceLine | undefined => {
    const chart = getChart()
    if (!priceLineManager || !chart) return undefined

    const allLines = priceLineManager.getAllLines()
    // 只查找入场线（成本线）
    const entryLines = allLines.filter(line => line.type === PriceLineType.ENTRY && line.orderId)

    let nearestLine: ChartPriceLine | undefined
    let minDistance = Infinity

    for (const line of entryLines) {
      const lineY = priceToPixelY(chart, line.price)
      if (lineY === null) continue

      const distance = Math.abs(pixelY - lineY)
      if (distance < dragThreshold && distance < minDistance) {
        minDistance = distance
        nearestLine = line
      }
    }

    return nearestLine
  }, [priceLineManager, getChart, dragThreshold])

  /**
   * 根据订单方向和价格变化判断应该创建什么类型的线
   */
  const determineLineType = useCallback((
    orderSide: OrderSide,
    entryPrice: number,
    currentPrice: number
  ): DragLineType => {
    const priceDiff = currentPrice - entryPrice

    if (orderSide === OrderSide.BUY) {
      // 多单：价格低于入场价 = 止损，价格高于入场价 = 止盈
      return priceDiff < 0 ? 'stop_loss' : 'take_profit'
    } else {
      // 空单：价格高于入场价 = 止损，价格低于入场价 = 止盈
      return priceDiff > 0 ? 'stop_loss' : 'take_profit'
    }
  }, [])

  /**
   * 开始从入场线创建
   */
  const startCreateFromEntry = useCallback((entryLine: ChartPriceLine, startY: number) => {
    if (!priceLineManager || !entryLine.orderId) return

    const order = orderService.getOrder(entryLine.orderId)
    if (!order) return

    setIsCreatingFromEntry(true)
    setEntryPrice(entryLine.price)
    setCurrentPrice(entryLine.price)

    isCreatingRef.current = true
    entryPriceRef.current = entryLine.price
    currentPriceRef.current = entryLine.price
    orderIdRef.current = entryLine.orderId
    orderSideRef.current = order.side
    startYRef.current = startY // 记录起始Y坐标
    hasDraggedRef.current = false // 重置拖拽标志

    console.log('🎯 ECharts Started creating from entry line:', {
      orderId: entryLine.orderId,
      entryPrice: entryLine.price,
      orderSide: order.side,
      startY,
    })
  }, [priceLineManager, orderService])

  /**
   * 更新创建位置
   */
  const updateCreateFromEntry = useCallback((pixelY: number) => {
    const chart = getChart()
    if (!isCreatingRef.current || !chart || !priceLineManager) return

    const startY = startYRef.current
    if (startY === null) return

    // 检查是否拖拽了足够的距离
    const dragDistance = Math.abs(pixelY - startY)
    if (dragDistance < minDragDistance) {
      // 距离太短，还不算真正的拖拽，不创建预览线
      return
    }

    // 标记为已拖拽
    hasDraggedRef.current = true

    const newPrice = pixelYToPrice(chart, pixelY)
    if (newPrice === null) return

    const entryP = entryPriceRef.current
    const orderSide = orderSideRef.current
    const orderId = orderIdRef.current

    if (entryP === null || orderSide === null || orderId === null) return

    // 判断线类型
    const lineType = determineLineType(orderSide, entryP, newPrice)

    setCurrentPrice(newPrice)
    setCreatingLineType(lineType)
    currentPriceRef.current = newPrice
    creatingLineTypeRef.current = lineType

    // 确定颜色和标题
    const isStopLoss = lineType === 'stop_loss'
    const color = isStopLoss ? '#ffa502' : '#1e90ff' // 橙色止损，蓝色止盈
    const title = isStopLoss 
      ? `止损 @ ${newPrice.toFixed(0)}` 
      : `止盈 @ ${newPrice.toFixed(0)}`

    // 如果类型变化或者还没有预览线，创建/更新预览线
    const previewId = previewLineIdRef.current

    if (!previewId) {
      // 创建预览线
      const previewLine = priceLineManager.createPriceLine({
        id: `preview_sl_tp_${Date.now()}`,
        orderId: orderId,
        type: isStopLoss ? PriceLineType.STOP_LOSS : PriceLineType.TAKE_PROFIT,
        price: newPrice,
        color: color + '99', // 半透明
        lineWidth: 1,
        lineStyle: 'dashed',
        title: title,
        draggable: false,
      })
      setPreviewLineId(previewLine.id)
      previewLineIdRef.current = previewLine.id
    } else {
      // 更新预览线
      priceLineManager.updateLine(previewId, {
        price: newPrice,
        color: color + '99',
        type: isStopLoss ? PriceLineType.STOP_LOSS : PriceLineType.TAKE_PROFIT,
        title: title,
      })
    }
  }, [getChart, priceLineManager, determineLineType])

  /**
   * 确认创建
   * @returns 是否成功创建了止损/止盈线
   */
  const confirmCreateFromEntry = useCallback((): boolean => {
    if (!isCreatingRef.current || !priceLineManager) {
      resetState()
      return false
    }

    // 检查是否实际发生了拖拽
    if (!hasDraggedRef.current) {
      // 没有拖拽（只是点击或双击），取消创建
      console.log('⏹️ ECharts No drag detected, cancelling creation')
      const previewId = previewLineIdRef.current
      if (previewId) {
        priceLineManager.removeLine(previewId)
      }
      resetState()
      return false
    }

    const orderId = orderIdRef.current
    const orderSide = orderSideRef.current
    const finalPrice = currentPriceRef.current
    const lineType = creatingLineTypeRef.current
    const previewId = previewLineIdRef.current

    if (!orderId || !orderSide || finalPrice === null || !lineType) {
      // 数据不完整，取消
      if (previewId) {
        priceLineManager.removeLine(previewId)
      }
      resetState()
      return false
    }

    // 移除预览线
    if (previewId) {
      priceLineManager.removeLine(previewId)
    }

    // 创建正式的止损/止盈线
    if (lineType === 'stop_loss') {
      priceLineManager.createStopLossLine({
        orderId,
        price: finalPrice,
        side: orderSide,
      })
      // 更新订单
      orderService.updateOrder({ id: orderId, stopLoss: finalPrice })
      console.log('✅ ECharts Created stop loss line:', finalPrice)
    } else {
      priceLineManager.createTakeProfitLine({
        orderId,
        price: finalPrice,
        side: orderSide,
      })
      // 更新订单
      orderService.updateOrder({ id: orderId, takeProfit: finalPrice })
      console.log('✅ ECharts Created take profit line:', finalPrice)
    }

    resetState()
    return true
  }, [priceLineManager, orderService])

  /**
   * 取消创建
   */
  const cancelCreateFromEntry = useCallback(() => {
    if (!isCreatingRef.current || !priceLineManager) return

    const previewId = previewLineIdRef.current
    if (previewId) {
      priceLineManager.removeLine(previewId)
    }

    console.log('↩️ ECharts Cancelled creating from entry')
    resetState()
  }, [priceLineManager])

  /**
   * 重置状态
   */
  const resetState = () => {
    setIsCreatingFromEntry(false)
    setCreatingLineType(null)
    setEntryPrice(null)
    setCurrentPrice(null)
    setPreviewLineId(null)

    isCreatingRef.current = false
    entryPriceRef.current = null
    currentPriceRef.current = null
    previewLineIdRef.current = null
    orderIdRef.current = null
    orderSideRef.current = null
    creatingLineTypeRef.current = null
    startYRef.current = null
    hasDraggedRef.current = false
  }

  return {
    isCreatingFromEntry,
    creatingLineType,
    entryPrice,
    currentPrice,
    previewLineId,
    findNearestEntryLine,
    startCreateFromEntry,
    updateCreateFromEntry,
    confirmCreateFromEntry,
    cancelCreateFromEntry,
  }
}

