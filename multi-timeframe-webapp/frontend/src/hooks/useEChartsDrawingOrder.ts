import { useState, useCallback, useRef } from 'react'
import { DrawingMode, OrderSide, CreateOrderRequest } from '../types'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { OrderService } from '../services/orderService'

interface UseEChartsDrawingOrderProps {
  priceLineManager: EChartsPriceLineManager | null
  orderService: OrderService
}

interface ConfirmOrderOptions {
  side: OrderSide
  quantity: number
  stopLoss?: number
  takeProfit?: number
}

interface UseEChartsDrawingOrderReturn {
  // 状态
  drawingMode: DrawingMode
  isDrawing: boolean
  previewPrice: number | null
  isOrderDialogOpen: boolean
  pendingOrderPrice: number | null

  // 模式控制
  enableDrawingMode: (mode: DrawingMode) => void
  disableDrawingMode: () => void

  // 事件处理
  handleCrosshairMove: (price: number | null) => void
  handleClick: () => void
  handleEscape: () => void

  // 订单操作
  confirmOrder: (options: ConfirmOrderOptions) => void
  closeOrderDialog: () => void
  cancelPendingOrder: (orderId: string) => void
}

/**
 * ECharts版画线下单交互Hook
 * 管理画线模式、预览线、下单对话框等交互逻辑
 * 
 * 与TradingView版本的区别：
 * - 使用EChartsPriceLineManager代替PriceLineManager
 * - 通过回调方式通知图表更新（ECharts不支持直接操作series）
 */
export function useEChartsDrawingOrder({
  priceLineManager,
  orderService,
}: UseEChartsDrawingOrderProps): UseEChartsDrawingOrderReturn {
  // 画线模式状态
  const [drawingMode, setDrawingMode] = useState<DrawingMode>(DrawingMode.NONE)
  
  // 使用ref跟踪最新的drawingMode，避免闭包问题
  const drawingModeRef = useRef<DrawingMode>(DrawingMode.NONE)
  
  // 预览价格（鼠标位置对应的价格）
  const [previewPrice, setPreviewPrice] = useState<number | null>(null)
  const previewPriceRef = useRef<number | null>(null)
  
  // 下单对话框状态
  const [isOrderDialogOpen, setIsOrderDialogOpen] = useState(false)
  const [pendingOrderPrice, setPendingOrderPrice] = useState<number | null>(null)
  const pendingOrderPriceRef = useRef<number | null>(null)

  // 是否处于画线模式
  const isDrawing = drawingMode !== DrawingMode.NONE

  /**
   * 启用画线模式
   */
  const enableDrawingMode = useCallback((mode: DrawingMode) => {
    setDrawingMode(mode)
    drawingModeRef.current = mode
  }, [])

  /**
   * 禁用画线模式
   */
  const disableDrawingMode = useCallback(() => {
    setDrawingMode(DrawingMode.NONE)
    drawingModeRef.current = DrawingMode.NONE
    setPreviewPrice(null)
    previewPriceRef.current = null
    
    // 移除预览线
    if (priceLineManager) {
      priceLineManager.removePreviewLine()
    }
  }, [priceLineManager])

  /**
   * 处理十字光标移动
   * 在ECharts中，需要从mousemove事件获取价格
   */
  const handleCrosshairMove = useCallback((price: number | null) => {
    if (drawingModeRef.current === DrawingMode.NONE || price === null) return

    setPreviewPrice(price)
    previewPriceRef.current = price

    // 更新预览线
    if (priceLineManager) {
      priceLineManager.createPreviewLine(price)
    }
  }, [priceLineManager])

  /**
   * 处理点击事件
   */
  const handleClick = useCallback(() => {
    if (drawingModeRef.current === DrawingMode.NONE) return
    if (previewPriceRef.current === null) return

    // 打开下单对话框
    setPendingOrderPrice(previewPriceRef.current)
    pendingOrderPriceRef.current = previewPriceRef.current
    setIsOrderDialogOpen(true)
  }, [])

  /**
   * 处理ESC键
   */
  const handleEscape = useCallback(() => {
    if (isOrderDialogOpen) {
      setIsOrderDialogOpen(false)
      setPendingOrderPrice(null)
      pendingOrderPriceRef.current = null
    } else if (drawingModeRef.current !== DrawingMode.NONE) {
      disableDrawingMode()
    }
  }, [isOrderDialogOpen, disableDrawingMode])

  /**
   * 确认下单
   */
  const confirmOrder = useCallback((options: ConfirmOrderOptions) => {
    const currentPendingPrice = pendingOrderPriceRef.current
    if (currentPendingPrice === null) return

    // 创建订单请求
    const request: CreateOrderRequest = {
      side: options.side,
      price: currentPendingPrice,
      quantity: options.quantity,
      stopLoss: options.stopLoss,
      takeProfit: options.takeProfit,
    }

    // 创建订单
    const order = orderService.createOrder(request)

    // 创建价格线
    if (priceLineManager) {
      // 创建挂单线
      priceLineManager.createPendingLine({
        orderId: order.id,
        price: currentPendingPrice,
        side: options.side,
        quantity: options.quantity,
      })

      // 创建止损线（如果指定）
      if (options.stopLoss !== undefined) {
        priceLineManager.createStopLossLine({
          orderId: order.id,
          price: options.stopLoss,
          side: options.side,
        })
      }

      // 创建止盈线（如果指定）
      if (options.takeProfit !== undefined) {
        priceLineManager.createTakeProfitLine({
          orderId: order.id,
          price: options.takeProfit,
          side: options.side,
        })
      }
    }

    // 关闭对话框并退出画线模式
    setIsOrderDialogOpen(false)
    setPendingOrderPrice(null)
    pendingOrderPriceRef.current = null
    disableDrawingMode()
  }, [orderService, priceLineManager, disableDrawingMode])

  /**
   * 关闭下单对话框
   */
  const closeOrderDialog = useCallback(() => {
    setIsOrderDialogOpen(false)
    setPendingOrderPrice(null)
  }, [])

  /**
   * 取消挂单
   */
  const cancelPendingOrder = useCallback((orderId: string) => {
    // 取消订单
    orderService.cancelOrder(orderId)

    // 移除相关价格线
    if (priceLineManager) {
      priceLineManager.removeLinesByOrderId(orderId)
    }
  }, [orderService, priceLineManager])

  return {
    // 状态
    drawingMode,
    isDrawing,
    previewPrice,
    isOrderDialogOpen,
    pendingOrderPrice,

    // 模式控制
    enableDrawingMode,
    disableDrawingMode,

    // 事件处理
    handleCrosshairMove,
    handleClick,
    handleEscape,

    // 订单操作
    confirmOrder,
    closeOrderDialog,
    cancelPendingOrder,
  }
}

