import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, CandlestickSeries, LineData, LineSeries, HistogramSeries, HistogramData, Time } from 'lightweight-charts'
import { Timeframe, ChartKLineData, DrawingMode, TradingOrder, PriceLineType, OrderSide, OrderStatus } from '../types'
import { dataService } from '../services/dataService'
import { OrderService } from '../services/orderService'
import { aggregateTo4Hours } from '../utils/timeframeAggregator'
import { calculateEndTimestamp } from '../utils/fourHourCandleRenderer'
import { PriceLineManager } from '../utils/priceLineManager'
import { OrderMarkerManager } from '../utils/orderMarkerManager'
import { useDrawingOrder } from '../hooks/useDrawingOrder'
import { usePriceLineDrag } from '../hooks/usePriceLineDrag'
import { useAutoTrailingStopLoss } from '../hooks/useAutoTrailingStopLoss'
import { useDualStopLoss } from '../hooks/useDualStopLoss'
import { useEntryLineDrag } from '../hooks/useEntryLineDrag'
import OrderDialog from './OrderDialog'
import './MultiTimeframeChart.css'

interface TradingViewChartProps {
  timeframes: Timeframe[]
  startDate?: string
  endDate?: string
  height?: string
}

// 创建全局订单服务实例
const orderService = new OrderService();

/**
 * TradingView Lightweight Charts Multi-Timeframe Component
 * Displays 1-minute candlesticks with custom-drawn 4-hour candlesticks using line primitives
 */
export default function TradingViewChart({
  timeframes,
  startDate,
  endDate,
  height = '100%',
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const lineSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const [loading, setLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState<string>('') // 当前加载阶段
  const hasInitialLoadedRef = useRef(false) // 是否已完成首次加载
  const [error, setError] = useState<string | null>(null)
  const [oneMinData, setOneMinData] = useState<ChartKLineData[]>([])
  const [fourHourData, setFourHourData] = useState<ChartKLineData[]>([])
  
  // 当前光标所在K线的信息
  const [crosshairData, setCrosshairData] = useState<{
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    change: number;
    changePercent: number;
  } | null>(null)
  
  // 价格线管理器
  const [priceLineManager, setPriceLineManager] = useState<PriceLineManager | null>(null)
  
  // 标记管理器
  const [markerManager, setMarkerManager] = useState<OrderMarkerManager | null>(null)
  
  // 订单列表
  const [pendingOrders, setPendingOrders] = useState<TradingOrder[]>([])
  const [filledOrders, setFilledOrders] = useState<TradingOrder[]>([])

  // 画线下单Hook
  const {
    drawingMode,
    isDrawing,
    previewPrice,
    isOrderDialogOpen,
    pendingOrderPrice,
    enableDrawingMode,
    disableDrawingMode,
    handleCrosshairMove,
    handleClick,
    handleEscape,
    confirmOrder,
    closeOrderDialog,
    cancelPendingOrder,
  } = useDrawingOrder({
    priceLineManager,
    orderService,
  })

  // 自动追踪止损Hook
  const {
    stopLossOffset,
    autoTrailingEnabled,
    setStopLossOffset,
    setAutoTrailingEnabled,
    updateStopLossOnPendingDrag,
    updateStopLossTakeProfitOnPendingDrag,
  } = useAutoTrailingStopLoss({
    priceLineManager,
    orderService,
    defaultStopLossOffset: 50,
  })

  // 双止损保护Hook
  const {
    isDraggingStopLoss,
    isProtectionActive,
    originalPrice: dualStopLossOriginalPrice,
    currentPrice: dualStopLossCurrentPrice,
    shadowPrice: dualStopLossShadowPrice,
    startDragStopLoss,
    updateDragStopLoss,
    confirmDragStopLoss,
    cancelDragStopLoss,
  } = useDualStopLoss({
    priceLineManager,
    lagFactor: 0.3, // 影子线跟随速度为主线的30%
  })

  // 从入场线拖拽创建止损/止盈Hook
  const {
    isCreatingFromEntry,
    creatingLineType,
    entryPrice: creatingEntryPrice,
    currentPrice: creatingCurrentPrice,
    findNearestEntryLine,
    startCreateFromEntry,
    updateCreateFromEntry,
    confirmCreateFromEntry,
    cancelCreateFromEntry,
  } = useEntryLineDrag({
    priceLineManager,
    orderService,
    series: candlestickSeriesRef.current,
  })

  // 价格线拖拽处理
  const handlePriceLineChange = useCallback((lineId: string, orderId: string, newPrice: number, lineType: any) => {
    console.log('📍 Price line changed:', { lineId, orderId, newPrice, lineType })
    
    // 更新订单价格
    const order = orderService.getOrder(orderId)
    if (!order) return

    if (lineType === 'pending') {
      // 获取旧的挂单价格（用于计算止损止盈的偏移量）
      const oldPrice = order.price
      console.log('📍 Pending order price updated:', { oldPrice, newPrice })
      
      // 更新订单的挂单价格（成交时使用这个价格）
      orderService.updateOrder({ id: orderId, price: newPrice })
      
      // 同时更新止损线和止盈线（保持相对偏移量不变）
      updateStopLossTakeProfitOnPendingDrag(orderId, newPrice, oldPrice)
    } else if (lineType === 'stop_loss') {
      orderService.updateOrder({ id: orderId, stopLoss: newPrice })
    } else if (lineType === 'take_profit') {
      orderService.updateOrder({ id: orderId, takeProfit: newPrice })
    }
  }, [updateStopLossTakeProfitOnPendingDrag])

  // 价格线拖拽Hook
  const {
    isDragging: isPriceLineDragging,
    draggingLine,
    findNearestDraggableLine,
    findNearestOrderLine,
    startDrag,
    updateDrag,
    endDrag,
    cancelDrag,
    getCursorStyle,
  } = usePriceLineDrag({
    priceLineManager,
    series: candlestickSeriesRef.current,
    onPriceChange: handlePriceLineChange,
  })

  // 鼠标悬停在价格线附近的状态
  const [isNearPriceLine, setIsNearPriceLine] = useState(false)

  // 删除挂单的处理函数（双击价格线删除）
  const handleDeleteOrder = useCallback((orderId: string) => {
    if (confirm('确定要删除这个挂单吗？')) {
      cancelPendingOrder(orderId)
    }
  }, [cancelPendingOrder])

  // 平仓处理函数（已成交订单双击入场线）
  const handleClosePosition = useCallback((orderId: string) => {
    const order = orderService.getOrder(orderId)
    if (!order || order.status !== OrderStatus.FILLED) return

    const actionText = order.side === OrderSide.BUY ? '卖出平仓' : '买入平仓'
    const confirmMsg = `确定要${actionText} ${order.quantity}手吗？\n\n持仓方向: ${order.side === OrderSide.BUY ? '多单' : '空单'}\n入场价格: ${order.filledPrice}\n\n注：平仓将通过对手价快速成交`

    if (confirm(confirmMsg)) {
      // 构建平仓请求
      const closeRequest = {
        orderId,
        side: order.side === OrderSide.BUY ? 'SELL' : 'BUY', // 反向操作
        quantity: order.quantity,
        type: 'MARKET', // 市价单（对手价）
      }
      
      console.log('📤 Close position request:', closeRequest)

      // TODO: 调用后端平仓接口
      // const response = await closePositionAPI(closeRequest)
      // 
      // 收到平仓成交确认后，执行以下清理操作：
      // onClosePositionFilled(orderId)
      
      // 临时：模拟平仓成交，立即清理
      // 正式环境应在收到后端成交确认后调用
      const simulateImmediateClose = true // 设为false时需等待后端确认
      if (simulateImmediateClose) {
        onClosePositionFilled(orderId)
        alert(`✅ 平仓成功！\n${actionText} ${order.quantity}手`)
      } else {
        alert(`平仓请求已发送！\n${actionText} ${order.quantity}手\n等待成交确认...`)
      }
    }
  }, [priceLineManager])

  // 平仓成交后的清理操作
  const onClosePositionFilled = useCallback((orderId: string, closePrice?: number) => {
    console.log('🧹 Cleaning up closed position:', orderId)

    // 1. 从图表移除该订单的所有价格线（入场线、止损线、止盈线）
    if (priceLineManager) {
      const removedCount = priceLineManager.removeLinesByOrderId(orderId)
      console.log(`  - Removed ${removedCount} price lines from chart`)
    }

    // 2. 从订单服务中移除该订单
    const closedOrder = orderService.closePosition(orderId, closePrice)
    if (closedOrder) {
      console.log('  - Order closed and removed:', closedOrder)
    }

    // 3. 订单列表会通过事件系统自动更新（onOrderCancelled回调）
  }, [priceLineManager])

  // 删除止损线（已成交订单双击止损线）
  const handleDeleteStopLossLine = useCallback((orderId: string, lineId: string) => {
    if (confirm('确定要删除此止损线吗？\n\n⚠️ 删除后将失去止损保护')) {
      // 从图表移除止损线
      if (priceLineManager) {
        priceLineManager.removeLine(lineId)
      }
      // 更新订单，清除止损价格
      orderService.updateOrder({ id: orderId, stopLoss: undefined })
      console.log('🗑️ Stop loss line deleted:', lineId)
    }
  }, [priceLineManager])

  // 删除止盈线（已成交订单双击止盈线）
  const handleDeleteTakeProfitLine = useCallback((orderId: string, lineId: string) => {
    if (confirm('确定要删除此止盈线吗？')) {
      // 从图表移除止盈线
      if (priceLineManager) {
        priceLineManager.removeLine(lineId)
      }
      // 更新订单，清除止盈价格
      orderService.updateOrder({ id: orderId, takeProfit: undefined })
      console.log('🗑️ Take profit line deleted:', lineId)
    }
  }, [priceLineManager])

  // TradingView chart colors (Chinese convention)
  const chartColors = {
    upColor: 'transparent',  // 阳线填充透明（空心）
    downColor: '#00d9ff',    // 青色-阴线（实心）
    borderUpColor: '#ff4757', // 阳线边框红色
    borderDownColor: '#00d9ff',
    wickUpColor: '#ff4757',
    wickDownColor: '#00d9ff',
  }

  // 4-hour drawing colors
  const fourHourColors = {
    upColor: '#ff4757',
    downColor: '#00d9ff',
    lineWidth: 2,
  }

  useEffect(() => {
    console.log('🔧 TradingView - Component mounted')

    const initTimer = setTimeout(() => {
      if (!chartContainerRef.current) {
        console.error('❌ TradingView - No container ref')
        setError('Container element not available')
        return
      }

      console.log('🔧 TradingView - Initializing chart...')

      try {
        const chart = createChart(chartContainerRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: '#1e1e1e' },
            textColor: '#ffffff',
          },
          grid: {
            vertLines: { color: '#404040' },
            horzLines: { color: '#404040' },
          },
          crosshair: {
            mode: 1,
          },
          rightPriceScale: {
            borderColor: '#404040',
            scaleMargins: {
              top: 0.05,   // 顶部留5%边距
              bottom: 0.22, // 底部留22%给成交量区域
            },
          },
          timeScale: {
            borderColor: '#404040',
            timeVisible: true,
            secondsVisible: false,
            minBarSpacing: 0.1, // 允许更大比例的缩放（默认约为3-4，值越小可缩得越小）
          },
          handleScale: {
            axisPressedMouseMove: {
              time: true,
              price: true,
            },
            mouseWheel: true,
            pinch: true,
          },
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight || 500,
        })

        chartRef.current = chart
        console.log('✅ TradingView - Chart created with minBarSpacing: 0.1')

        // 确保 minBarSpacing 设置生效（允许更大范围的缩放）
        chart.timeScale().applyOptions({
          minBarSpacing: 0.1,
        })

        // Handle resize
        const handleResize = () => {
          if (chartContainerRef.current && chart) {
            chart.applyOptions({
              width: chartContainerRef.current.clientWidth,
              height: chartContainerRef.current.clientHeight,
            })
          }
        }

        window.addEventListener('resize', handleResize)

        // Load data (首次加载，使用简单提示)
        loadChartData(false).then(() => {
          hasInitialLoadedRef.current = true
        })

        return () => {
          console.log('🧹 TradingView - Cleaning up')
          window.removeEventListener('resize', handleResize)
          chart.remove()
        }
      } catch (error) {
        console.error('❌ TradingView - Chart init failed:', error)
        setError(`Chart initialization failed: ${error instanceof Error ? error.message : 'Unknown'}`)
        setLoading(false)
      }
    }, 100)

    return () => {
      clearTimeout(initTimer)
    }
  }, [])

  // Reload when timeframes or date range change (用户触发，显示详细进度)
  useEffect(() => {
    // 只有首次加载完成后，日期变化才触发重新加载
    if (chartRef.current && hasInitialLoadedRef.current) {
      loadChartData(true) // 用户触发的加载，显示详细进度
    }
  }, [timeframes, startDate, endDate])

  // 订阅图表事件
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    const chart = chartRef.current
    const series = candlestickSeriesRef.current

    // 十字光标移动事件 - 获取价格和K线数据
    const handleCrosshairMoveEvent = (param: any) => {
      if (!param.point || !param.time) {
        setIsNearPriceLine(false)
        setCrosshairData(null)
        return
      }
      
      // 从坐标转换为价格
      const price = series.coordinateToPrice(param.point.y)
      if (price !== null) {
        handleCrosshairMove(price)
      }

      // 获取当前K线的OHLC数据
      const seriesData = param.seriesData.get(series)
      if (seriesData) {
        const timestamp = (param.time as number) * 1000 // 转换为毫秒
        const date = new Date(timestamp)
        
        // 格式化时间显示
        const timeStr = date.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          weekday: 'short',
        })
        
        // 计算涨跌
        const change = seriesData.close - seriesData.open
        const changePercent = (change / seriesData.open) * 100
        
        // 从原始数据中查找成交量
        const klineData = oneMinData.find(d => d.timestamp === timestamp)
        const volume = klineData?.volume || 0
        
        setCrosshairData({
          time: timeStr,
          open: seriesData.open,
          high: seriesData.high,
          low: seriesData.low,
          close: seriesData.close,
          volume,
          change,
          changePercent,
        })
      }

      // 检查是否靠近可拖拽的价格线
      if (!isDrawing && priceLineManager) {
        const nearLine = findNearestDraggableLine(param.point.y)
        setIsNearPriceLine(!!nearLine)
      }
    }

    // 点击事件
    const handleClickEvent = (param: any) => {
      if (!param.point) return
      
      // 如果正在拖拽，不处理点击
      if (isPriceLineDragging) return
      
      handleClick()
    }

    chart.subscribeCrosshairMove(handleCrosshairMoveEvent)
    chart.subscribeClick(handleClickEvent)

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMoveEvent)
      chart.unsubscribeClick(handleClickEvent)
    }
  }, [handleCrosshairMove, handleClick, priceLineManager, isDrawing, findNearestDraggableLine, isPriceLineDragging])

  // 鼠标事件处理（用于拖拽和双击删除）
  useEffect(() => {
    const container = chartContainerRef.current
    if (!container || !candlestickSeriesRef.current) return

    const series = candlestickSeriesRef.current

    const handleMouseDown = (e: MouseEvent) => {
      if (isDrawing) return // 画线模式下不处理拖拽

      const rect = container.getBoundingClientRect()
      const y = e.clientY - rect.top

      // 首先检查是否点击了可拖拽的线
      const nearDraggableLine = findNearestDraggableLine(y)
      if (nearDraggableLine) {
        e.preventDefault()
        startDrag(nearDraggableLine)
        
        // 如果是止损线，激活双止损保护
        if (nearDraggableLine.type === PriceLineType.STOP_LOSS && nearDraggableLine.orderId) {
          const order = orderService.getOrder(nearDraggableLine.orderId)
          if (order) {
            startDragStopLoss(nearDraggableLine, order.side)
          }
        }
        return
      }

      // 检查是否点击了入场线（成本线）- 用于创建止损/止盈
      const nearEntryLine = findNearestEntryLine(y)
      if (nearEntryLine) {
        e.preventDefault()
        startCreateFromEntry(nearEntryLine, y) // 传入起始Y坐标
      }
    }

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      const y = e.clientY - rect.top

      // 处理价格线拖拽
      if (isPriceLineDragging) {
        updateDrag(y)
        
        // 如果正在拖动止损线，更新双止损保护的当前价格
        if (isDraggingStopLoss && series) {
          const price = series.coordinateToPrice(y)
          if (price !== null) {
            updateDragStopLoss(price)
          }
        }
        return
      }

      // 处理从入场线创建止损/止盈
      if (isCreatingFromEntry) {
        updateCreateFromEntry(y)
      }
    }

    const handleMouseUp = () => {
      if (isPriceLineDragging) {
        // 如果正在拖动止损线，确认双止损保护
        if (isDraggingStopLoss) {
          confirmDragStopLoss()
        }
        endDrag()
        return
      }

      // 确认从入场线创建止损/止盈
      if (isCreatingFromEntry) {
        confirmCreateFromEntry()
      }
    }

    const handleMouseLeave = () => {
      if (isPriceLineDragging) {
        // 如果正在拖动止损线，取消双止损保护
        if (isDraggingStopLoss) {
          cancelDragStopLoss()
        }
        cancelDrag()
        return
      }

      // 取消从入场线创建
      if (isCreatingFromEntry) {
        cancelCreateFromEntry()
      }
    }

    // 双击处理：挂单删除 / 已成交订单平仓 / 删除止损止盈线
    const handleDoubleClick = (e: MouseEvent) => {
      if (isDrawing) return

      const rect = container.getBoundingClientRect()
      const y = e.clientY - rect.top

      console.log('🖱️ Double click at y:', y)
      // 使用 findNearestOrderLine 查找所有订单相关的线（包括入场线）
      const nearLine = findNearestOrderLine(y)
      console.log('🖱️ Near order line:', nearLine)
      
      if (nearLine && nearLine.orderId) {
        e.preventDefault()
        
        // 获取订单信息
        const order = orderService.getOrder(nearLine.orderId)
        if (!order) {
          console.log('⚠️ Order not found:', nearLine.orderId)
          return
        }

        // 根据订单状态和线类型执行不同操作
        if (order.status === OrderStatus.PENDING) {
          // 挂单状态 → 删除整个挂单
          console.log('🗑️ Deleting pending order:', nearLine.orderId)
          handleDeleteOrder(nearLine.orderId)
        } else if (order.status === OrderStatus.FILLED) {
          // 已成交状态 → 根据线类型执行不同操作
          if (nearLine.type === PriceLineType.ENTRY) {
            // 双击入场线（成本线）→ 平仓
            console.log('📤 Closing position:', nearLine.orderId)
            handleClosePosition(nearLine.orderId)
          } else if (nearLine.type === PriceLineType.STOP_LOSS) {
            // 双击止损线 → 删除止损线
            console.log('🗑️ Deleting stop loss line:', nearLine.id)
            handleDeleteStopLossLine(nearLine.orderId, nearLine.id)
          } else if (nearLine.type === PriceLineType.TAKE_PROFIT) {
            // 双击止盈线 → 删除止盈线
            console.log('🗑️ Deleting take profit line:', nearLine.id)
            handleDeleteTakeProfitLine(nearLine.orderId, nearLine.id)
          }
        }
      } else {
        console.log('⚠️ No order line found near click position')
      }
    }

    container.addEventListener('mousedown', handleMouseDown)
    container.addEventListener('dblclick', handleDoubleClick)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    container.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      container.removeEventListener('mousedown', handleMouseDown)
      container.removeEventListener('dblclick', handleDoubleClick)
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      container.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [isDrawing, isPriceLineDragging, findNearestDraggableLine, findNearestOrderLine, findNearestEntryLine, startDrag, updateDrag, endDrag, cancelDrag, handleDeleteOrder, handleClosePosition, handleDeleteStopLossLine, handleDeleteTakeProfitLine, isDraggingStopLoss, startDragStopLoss, updateDragStopLoss, confirmDragStopLoss, cancelDragStopLoss, isCreatingFromEntry, startCreateFromEntry, updateCreateFromEntry, confirmCreateFromEntry, cancelCreateFromEntry])

  // 键盘事件处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // 如果正在从入场线创建，取消
        if (isCreatingFromEntry) {
          cancelCreateFromEntry()
          return
        }
        // 如果正在拖拽，取消拖拽
        if (isPriceLineDragging) {
          // 如果正在拖动止损线，取消双止损保护
          if (isDraggingStopLoss) {
            cancelDragStopLoss()
          }
          cancelDrag()
          return
        }
        // 否则处理画线模式的ESC
        handleEscape()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleEscape, isPriceLineDragging, cancelDrag, isDraggingStopLoss, cancelDragStopLoss, isCreatingFromEntry, cancelCreateFromEntry])

  // 订阅订单事件更新列表
  useEffect(() => {
    const updateOrders = () => {
      setPendingOrders(orderService.getPendingOrders())
      setFilledOrders(orderService.getFilledOrders())
    }

    orderService.onOrderCreated(updateOrders)
    orderService.onOrderFilled(updateOrders)
    orderService.onOrderCancelled(updateOrders)
    orderService.onOrderUpdated(updateOrders)

    return () => {
      orderService.offOrderCreated(updateOrders)
      orderService.offOrderFilled(updateOrders)
      orderService.offOrderCancelled(updateOrders)
      orderService.offOrderUpdated(updateOrders)
    }
  }, [])

  // 模拟成交订单
  const simulateFillOrder = useCallback((orderId: string) => {
    const order = orderService.getOrder(orderId)
    if (!order) return

    // 成交订单
    const filledOrder = orderService.fillOrder(orderId, order.price)
    if (!filledOrder) return

    // 更新价格线：移除挂单线，添加成交线
    if (priceLineManager) {
      priceLineManager.removeLinesByOrderId(orderId)
      
      // 创建成交入场线
      priceLineManager.createEntryLine({
        orderId: filledOrder.id,
        price: filledOrder.filledPrice!,
        side: filledOrder.side,
        quantity: filledOrder.quantity,
      })

      // 如果有止损，创建止损线
      if (filledOrder.stopLoss) {
        priceLineManager.createStopLossLine({
          orderId: filledOrder.id,
          price: filledOrder.stopLoss,
          side: filledOrder.side,
        })
      }

      // 如果有止盈，创建止盈线
      if (filledOrder.takeProfit) {
        priceLineManager.createTakeProfitLine({
          orderId: filledOrder.id,
          price: filledOrder.takeProfit,
          side: filledOrder.side,
        })
      }
    }

    // 添加成交标记
    if (markerManager) {
      markerManager.addFilledOrderMarker(filledOrder)
    }
  }, [priceLineManager, markerManager])

  // Filter data by time range
  const filterDataByTimeRange = (data: ChartKLineData[]): ChartKLineData[] => {
    if (!startDate && !endDate) return data

    const startTimestamp = startDate ? new Date(startDate).getTime() : 0
    const endTimestamp = endDate ? new Date(endDate).getTime() + 24 * 60 * 60 * 1000 : Infinity

    return data.filter(item => {
      return item.timestamp >= startTimestamp && item.timestamp < endTimestamp
    })
  }

  /**
   * Draw 4-hour candlesticks using line primitives
   * D12: 使用精确的时间边界绘制4小时K线
   * 
   * 精确边界:
   * 1. 17:15-21:14 (第一根4H)
   * 2. 21:15-01:14 (第二根4H，跨午夜)
   * 3. 01:15-11:29 (第三根4H，跨休市)
   * 4. 11:30-16:29 (第四根4H，跨午休)
   */
  const draw4HourCandlesticks = (fourHourData: ChartKLineData[], oneMinData: ChartKLineData[]) => {
    if (!chartRef.current) return

    console.log('🎨 Drawing 4-hour candlesticks using line primitives (D12 精确边界)...')

    // Create a map of 1-minute data by timestamp for fast lookup
    const oneMinMap = new Map<number, ChartKLineData>()
    oneMinData.forEach(bar => {
      oneMinMap.set(bar.timestamp, bar)
    })

    let lineCounter = 0

    // For each 4-hour bar, draw the box and wicks
    fourHourData.forEach((bar4h, index) => {
      const startTime = bar4h.timestamp / 1000  // Convert to seconds for TradingView
      const isBullish = bar4h.close >= bar4h.open
      const color = isBullish ? fourHourColors.upColor : fourHourColors.downColor

      // D12: 使用 calculateEndTimestamp 计算精确结束时间
      const endTimestamp = calculateEndTimestamp(bar4h.timestamp)
      const endTime = endTimestamp / 1000

      try {
        // Draw horizontal line for open price (from start to end)
        const openLineSeries = chartRef.current!.addSeries(LineSeries, {
          color: color,
          lineWidth: fourHourColors.lineWidth,
          priceScaleId: 'right',
          lastValueVisible: false,
          priceLineVisible: false,
        })
        openLineSeries.setData([
          { time: startTime as Time, value: bar4h.open },
          { time: endTime as Time, value: bar4h.open },
        ])
        lineSeriesRef.current.set(`4h-open-${index}-${lineCounter++}`, openLineSeries)

        // Draw horizontal line for close price (from start to end)
        const closeLineSeries = chartRef.current!.addSeries(LineSeries, {
          color: color,
          lineWidth: fourHourColors.lineWidth,
          priceScaleId: 'right',
          lastValueVisible: false,
          priceLineVisible: false,
        })
        closeLineSeries.setData([
          { time: startTime as Time, value: bar4h.close },
          { time: endTime as Time, value: bar4h.close },
        ])
        lineSeriesRef.current.set(`4h-close-${index}-${lineCounter++}`, closeLineSeries)

        // Draw vertical line at start connecting open and close
        // Use a tiny time offset to create a vertical line effect
        const startVerticalSeries = chartRef.current!.addSeries(LineSeries, {
          color: color,
          lineWidth: fourHourColors.lineWidth,
          priceScaleId: 'right',
          lastValueVisible: false,
          priceLineVisible: false,
        })
        startVerticalSeries.setData([
          { time: startTime as Time, value: Math.min(bar4h.open, bar4h.close) },
          { time: (startTime + 1) as Time, value: Math.max(bar4h.open, bar4h.close) },
        ])
        lineSeriesRef.current.set(`4h-start-vert-${index}-${lineCounter++}`, startVerticalSeries)

        // Draw vertical line at end connecting open and close
        const endVerticalSeries = chartRef.current!.addSeries(LineSeries, {
          color: color,
          lineWidth: fourHourColors.lineWidth,
          priceScaleId: 'right',
          lastValueVisible: false,
          priceLineVisible: false,
        })
        endVerticalSeries.setData([
          { time: (endTime - 1) as Time, value: Math.min(bar4h.open, bar4h.close) },
          { time: endTime as Time, value: Math.max(bar4h.open, bar4h.close) },
        ])
        lineSeriesRef.current.set(`4h-end-vert-${index}-${lineCounter++}`, endVerticalSeries)

        // 使用K线数量中点的时间戳来绘制影线（避免落在休市区间）
        // 如果没有 midpointTimestamp，回退到时间中点计算
        const midTime = bar4h.midpointTimestamp 
          ? bar4h.midpointTimestamp / 1000 
          : (startTime + endTime) / 2

        // Draw high/low wicks at the midpoint position
        // High wick: from the higher of open/close to high
        // Low wick: from the lower of open/close to low
        const bodyTop = Math.max(bar4h.open, bar4h.close)
        const bodyBottom = Math.min(bar4h.open, bar4h.close)

        // Draw high wick if high is above the body
        if (bar4h.high > bodyTop) {
          const highWickSeries = chartRef.current!.addSeries(LineSeries, {
            color: color,
            lineWidth: Math.max(1, fourHourColors.lineWidth - 1),
            priceScaleId: 'right',
            lastValueVisible: false,
            priceLineVisible: false,
          })
          highWickSeries.setData([
            { time: midTime as Time, value: bodyTop },
            { time: (midTime + 1) as Time, value: bar4h.high },
          ])
          lineSeriesRef.current.set(`4h-high-wick-${index}-${lineCounter++}`, highWickSeries)
        }

        // Draw low wick if low is below the body
        if (bar4h.low < bodyBottom) {
          const lowWickSeries = chartRef.current!.addSeries(LineSeries, {
            color: color,
            lineWidth: Math.max(1, fourHourColors.lineWidth - 1),
            priceScaleId: 'right',
            lastValueVisible: false,
            priceLineVisible: false,
          })
          lowWickSeries.setData([
            { time: (midTime - 1) as Time, value: bar4h.low },
            { time: midTime as Time, value: bodyBottom },
          ])
          lineSeriesRef.current.set(`4h-low-wick-${index}-${lineCounter++}`, lowWickSeries)
        }

        // Draw diagonal hatch lines for bearish candles (close < open)
        // Add sparse diagonal lines to create a shadow effect
        if (!isBullish && bodyTop > bodyBottom) {
          const bodyHeight = bodyTop - bodyBottom
          const numHatchLines = Math.min(5, Math.floor(bodyHeight / 20))  // Limit to 5 lines max

          for (let i = 1; i <= numHatchLines; i++) {
            const priceLevel = bodyBottom + (bodyHeight * i / (numHatchLines + 1))
            const timeOffset = (endTime - startTime) * 0.15  // 15% of time width

            const hatchSeries = chartRef.current!.addSeries(LineSeries, {
              color: color,
              lineWidth: 1,
              priceScaleId: 'right',
              lastValueVisible: false,
              priceLineVisible: false,
            })
            hatchSeries.setData([
              { time: (startTime + timeOffset) as Time, value: priceLevel - (bodyHeight * 0.1) },
              { time: (endTime - timeOffset) as Time, value: priceLevel + (bodyHeight * 0.1) },
            ])
            lineSeriesRef.current.set(`4h-hatch-${index}-${i}-${lineCounter++}`, hatchSeries)
          }
        }
      } catch (err) {
        console.error(`Error drawing 4-hour bar ${index}:`, err)
      }
    })

    console.log(`✅ Drew ${fourHourData.length} 4-hour candlesticks using ${lineCounter} line series`)
  }

  const loadChartData = async (showDetailedProgress = true) => {
    const startTime = Date.now()
    
    // 首次加载使用简单提示，用户触发的加载显示详细进度
    setLoading(true)
    if (showDetailedProgress) {
      setLoadingStage('准备加载数据...')
    } else {
      setLoadingStage('初始化图表...')
    }

    try {
      setError(null)

      if (!chartRef.current) {
        setLoading(false)
        return
      }

      console.log(`🔍 TradingView - Loading data`)
      console.log(`Time range: ${startDate} to ${endDate}`)

      // Load all data (no limit)
      const originalLimit = dataService.getDataLimit()
      dataService.setDataLimit(-1)

      // 阶段1：加载1分钟数据
      if (showDetailedProgress) {
        setLoadingStage('正在加载1分钟K线数据...')
        await new Promise(resolve => setTimeout(resolve, 50)) // 让UI更新
      }
      const oneMinRawData = await dataService.getData(Timeframe.ONE_MINUTE)

      // Restore original limit
      dataService.setDataLimit(originalLimit)

      // 阶段2：筛选日期范围
      if (showDetailedProgress) {
        setLoadingStage(`筛选 ${startDate} 至 ${endDate} 的数据...`)
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      const oneMinFiltered = filterDataByTimeRange(oneMinRawData)

      // 阶段3：聚合4小时K线 (D12 精确边界)
      if (showDetailedProgress) {
        setLoadingStage(`聚合计算4小时K线 (${oneMinFiltered.length}根1分钟K线，D12精确边界)...`)
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      const fourHourFiltered = aggregateTo4Hours(oneMinFiltered)

      if (oneMinFiltered.length === 0) {
        setError('选定时间范围内没有1分钟数据')
        setLoading(false)
        setLoadingStage('')
        return
      }

      setOneMinData(oneMinFiltered)
      setFourHourData(fourHourFiltered)

      console.log(`📊 Loaded ${oneMinFiltered.length} 1-min candles, ${fourHourFiltered.length} 4-hour candles`)

      // 阶段4：渲染图表
      if (showDetailedProgress) {
        setLoadingStage(`渲染图表 (${fourHourFiltered.length}根4小时K线)...`)
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      
      // Clear existing series
      lineSeriesRef.current.forEach((series, key) => {
        if (series && chartRef.current) {
          try {
            chartRef.current.removeSeries(series)
          } catch (err) {
            // Silently ignore if series was already removed
            console.debug(`Series ${key} already removed or invalid`)
          }
        }
      })
      lineSeriesRef.current.clear()

      // Remove candlestick series if it exists and is valid
      if (candlestickSeriesRef.current) {
        try {
          if (chartRef.current) {
            chartRef.current.removeSeries(candlestickSeriesRef.current)
          }
        } catch (err) {
          // Silently ignore if series was already removed
          console.debug('Candlestick series already removed or invalid')
        } finally {
          candlestickSeriesRef.current = null
        }
      }

      // 1. Draw 1-minute candlesticks as base layer
      const candlestickData: CandlestickData[] = oneMinFiltered.map((item) => ({
        time: Math.floor(item.timestamp / 1000) as Time,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      }))

      const candlestickSeries = chartRef.current.addSeries(CandlestickSeries, {
        upColor: chartColors.upColor,
        downColor: chartColors.downColor,
        borderUpColor: chartColors.borderUpColor,
        borderDownColor: chartColors.borderDownColor,
        wickUpColor: chartColors.wickUpColor,
        wickDownColor: chartColors.wickDownColor,
        priceScaleId: 'right',
        // 禁用默认的最后价格线（红色虚线）
        lastValueVisible: false,
        priceLineVisible: false,
      })

      candlestickSeries.setData(candlestickData)
      candlestickSeriesRef.current = candlestickSeries

      // 3. 添加成交量柱状图（显示在下方区域）
      const volumeData: HistogramData[] = oneMinFiltered.map((item) => ({
        time: Math.floor(item.timestamp / 1000) as Time,
        value: item.volume,
        // 根据K线涨跌设置颜色
        color: item.close >= item.open 
          ? 'rgba(255, 71, 87, 0.5)'   // 涨 - 红色半透明
          : 'rgba(0, 217, 255, 0.5)', // 跌 - 青色半透明
      }))

      const volumeSeries = chartRef.current.addSeries(HistogramSeries, {
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume', // 使用单独的价格轴
      })

      // 配置成交量价格轴（显示在左侧，占图表下方20%区域）
      chartRef.current.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.8,    // 成交量区域从80%位置开始
          bottom: 0,   // 到底部
        },
        borderVisible: false,
      })

      volumeSeries.setData(volumeData)
      volumeSeriesRef.current = volumeSeries
      console.log(`📊 Volume bars: ${volumeData.length} bars`)
      
      // 初始化或更新PriceLineManager
      if (priceLineManager) {
        priceLineManager.setSeries(candlestickSeries)
      } else {
        setPriceLineManager(new PriceLineManager(candlestickSeries))
      }
      
      // 初始化或更新OrderMarkerManager
      if (markerManager) {
        markerManager.setSeries(candlestickSeries)
      } else {
        setMarkerManager(new OrderMarkerManager(candlestickSeries))
      }

      console.log(`📈 1-min candlesticks: ${candlestickData.length} candles`)

      // 2. Draw 4-hour candlesticks using line primitives
      // 限制只绘制最近50个4小时K线以避免性能问题
      if (fourHourFiltered.length > 0) {
        const maxFourHourBars = 50
        const limitedFourHourData = fourHourFiltered.slice(-maxFourHourBars)
        console.log(`📊 Limiting 4-hour candles: ${fourHourFiltered.length} -> ${limitedFourHourData.length}`)
        draw4HourCandlesticks(limitedFourHourData, oneMinFiltered)
      }

      // Fit content
      chartRef.current.timeScale().fitContent()

      // 隐藏加载状态
      setLoading(false)
      setLoadingStage('')
      
      console.log(`✅ Chart loaded in ${Date.now() - startTime}ms`)
    } catch (err) {
      console.error('Error loading chart:', err)
      setError(err instanceof Error ? err.message : 'Failed to load chart data')
      setLoading(false)
      setLoadingStage('')
    }
  }

  if (error) {
    return (
      <div className="chart-error">
        <p>⚠️ Error loading chart</p>
        <p className="error-message">{error}</p>
        <button onClick={loadChartData}>Retry</button>
      </div>
    )
  }

  return (
    <div className="tradingview-chart" style={{ position: 'relative', width: '100%', height }}>
      {/* 工具栏 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        zIndex: 10,
        display: 'flex',
        gap: '8px',
        alignItems: 'center',
      }}>
        {/* 自动追踪止损设置 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 12px',
          backgroundColor: '#2a2a2a',
          borderRadius: '6px',
          border: '1px solid #404040',
        }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: '#fff',
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}>
            <input
              type="checkbox"
              checked={autoTrailingEnabled}
              onChange={(e) => setAutoTrailingEnabled(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            自动止损
          </label>
          {autoTrailingEnabled && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <input
                type="number"
                value={stopLossOffset}
                onChange={(e) => setStopLossOffset(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  width: '60px',
                  padding: '4px 6px',
                  backgroundColor: '#1e1e1e',
                  border: '1px solid #404040',
                  borderRadius: '4px',
                  color: '#fff',
                  fontSize: '0.85rem',
                  textAlign: 'center',
                }}
                min="1"
              />
              <span style={{ color: '#888', fontSize: '0.8rem' }}>点</span>
            </div>
          )}
        </div>

        <button
          onClick={() => isDrawing ? disableDrawingMode() : enableDrawingMode(DrawingMode.ORDER_LINE)}
          style={{
            padding: '8px 16px',
            backgroundColor: isDrawing ? '#ff4757' : '#2a2a2a',
            color: '#fff',
            border: isDrawing ? '2px solid #ff4757' : '1px solid #404040',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: isDrawing ? '600' : '400',
            transition: 'all 0.2s',
          }}
        >
          {isDrawing ? '✕ 取消画线' : '✏️ 画线下单'}
        </button>

        {/* 调试按钮 - 查看所有价格线 */}
        <button
          onClick={() => {
            if (priceLineManager) {
              const lines = priceLineManager.getAllLines();
              console.log('📊 All price lines in manager:', lines);
              alert(`价格线管理器中有 ${lines.length} 条线`);
            }
            if (candlestickSeriesRef.current) {
              const seriesLines = candlestickSeriesRef.current.priceLines();
              console.log('📊 All price lines in series:', seriesLines);
              alert(`图表系列中有 ${seriesLines.length} 条价格线`);
            }
          }}
          style={{
            padding: '8px 12px',
            backgroundColor: '#2a2a2a',
            color: '#888',
            border: '1px solid #404040',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem',
          }}
        >
          🔍 调试
        </button>
      </div>

      {/* 画线模式提示 */}
      {isDrawing && (
        <div style={{
          position: 'absolute',
          top: '50px',
          right: '10px',
          zIndex: 10,
          backgroundColor: 'rgba(255, 71, 87, 0.9)',
          color: '#fff',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.85rem',
        }}>
          <div>画线下单模式</div>
          {previewPrice && (
            <div style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
              价格: {previewPrice.toFixed(0)}
            </div>
          )}
          <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
            点击图表下单 | ESC取消
          </div>
        </div>
      )}

      {/* 拖拽提示 */}
      {isPriceLineDragging && draggingLine && (
        <div style={{
          position: 'absolute',
          top: '50px',
          right: '10px',
          zIndex: 10,
          backgroundColor: isProtectionActive ? 'rgba(255, 165, 2, 0.95)' : 'rgba(30, 144, 255, 0.9)',
          color: '#fff',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.85rem',
          boxShadow: isProtectionActive ? '0 0 20px rgba(255, 165, 2, 0.5)' : 'none',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isProtectionActive && <span>🛡️</span>}
            <span>{isProtectionActive ? '双止损保护' : '拖拽调整价格'}</span>
          </div>
          <div style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
            {draggingLine.title}
          </div>
          {isProtectionActive && dualStopLossOriginalPrice && dualStopLossCurrentPrice && (
            <div style={{ 
              marginTop: '6px', 
              padding: '6px 8px', 
              backgroundColor: 'rgba(0,0,0,0.3)', 
              borderRadius: '4px',
              fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>原止损:</span>
                <span style={{ fontFamily: 'monospace' }}>{dualStopLossOriginalPrice.toFixed(0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>保护线:</span>
                <span style={{ fontFamily: 'monospace', color: '#ffa502' }}>
                  {dualStopLossShadowPrice?.toFixed(0) || '-'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>新止损:</span>
                <span style={{ fontFamily: 'monospace', color: '#90EE90' }}>{dualStopLossCurrentPrice.toFixed(0)}</span>
              </div>
            </div>
          )}
          <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
            {isProtectionActive ? '原止损线保护中 | 释放鼠标确认' : '释放鼠标确认 | ESC取消'}
          </div>
        </div>
      )}

      {/* 从入场线创建止损/止盈提示 */}
      {isCreatingFromEntry && (
        <div style={{
          position: 'absolute',
          top: '50px',
          right: '10px',
          zIndex: 10,
          backgroundColor: creatingLineType === 'stop_loss' 
            ? 'rgba(255, 165, 2, 0.95)' 
            : 'rgba(30, 144, 255, 0.95)',
          color: '#fff',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.85rem',
          boxShadow: '0 0 20px rgba(0,0,0,0.3)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{creatingLineType === 'stop_loss' ? '🛡️' : '🎯'}</span>
            <span>创建{creatingLineType === 'stop_loss' ? '止损线' : '止盈线'}</span>
          </div>
          {creatingEntryPrice && creatingCurrentPrice && (
            <div style={{ 
              marginTop: '6px', 
              padding: '6px 8px', 
              backgroundColor: 'rgba(0,0,0,0.3)', 
              borderRadius: '4px',
              fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>成本价:</span>
                <span style={{ fontFamily: 'monospace' }}>{creatingEntryPrice.toFixed(0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>{creatingLineType === 'stop_loss' ? '止损:' : '止盈:'}</span>
                <span style={{ fontFamily: 'monospace', color: '#90EE90' }}>
                  {creatingCurrentPrice.toFixed(0)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <span style={{ opacity: 0.8 }}>点差:</span>
                <span style={{ fontFamily: 'monospace' }}>
                  {Math.abs(creatingCurrentPrice - creatingEntryPrice).toFixed(0)}
                </span>
              </div>
            </div>
          )}
          <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
            释放鼠标确认 | ESC取消
          </div>
        </div>
      )}

      {/* 价格线操作提示 */}
      {!isDrawing && !isPriceLineDragging && !isCreatingFromEntry && isNearPriceLine && (
        <div style={{
          position: 'absolute',
          top: '50px',
          right: '10px',
          zIndex: 10,
          backgroundColor: 'rgba(100, 100, 100, 0.9)',
          color: '#fff',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.8rem',
        }}>
          <div>拖拽移动 | 双击删除</div>
        </div>
      )}

      {/* Legend 和 K线信息 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        zIndex: 10,
        backgroundColor: 'rgba(30, 30, 30, 0.9)',
        padding: '10px',
        borderRadius: '6px',
        fontSize: '0.85rem',
        minWidth: '220px',
      }}>
        {/* K线数据显示 */}
        {crosshairData ? (
          <div style={{ marginBottom: '10px' }}>
            <div style={{ 
              color: '#888', 
              fontSize: '0.75rem', 
              marginBottom: '6px',
              borderBottom: '1px solid #404040',
              paddingBottom: '4px',
            }}>
              {crosshairData.time}
            </div>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr 1fr', 
              gap: '4px 12px',
              fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>开:</span>
                <span style={{ color: '#fff', fontFamily: 'monospace' }}>{crosshairData.open.toFixed(0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>高:</span>
                <span style={{ color: '#ff4757', fontFamily: 'monospace' }}>{crosshairData.high.toFixed(0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>收:</span>
                <span style={{ color: '#fff', fontFamily: 'monospace' }}>{crosshairData.close.toFixed(0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>低:</span>
                <span style={{ color: '#00d9ff', fontFamily: 'monospace' }}>{crosshairData.low.toFixed(0)}</span>
              </div>
            </div>
            <div style={{ 
              marginTop: '6px', 
              paddingTop: '6px', 
              borderTop: '1px solid #404040',
              fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ color: '#888' }}>涨跌:</span>
                <span style={{ 
                  color: crosshairData.change >= 0 ? '#ff4757' : '#00d9ff',
                  fontFamily: 'monospace',
                  fontWeight: '600',
                }}>
                  {crosshairData.change >= 0 ? '+' : ''}{crosshairData.change.toFixed(0)} 
                  ({crosshairData.changePercent >= 0 ? '+' : ''}{crosshairData.changePercent.toFixed(2)}%)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>成交量:</span>
                <span style={{ 
                  color: crosshairData.change >= 0 ? '#ff4757' : '#00d9ff',
                  fontFamily: 'monospace',
                }}>
                  {crosshairData.volume.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ 
            color: '#666', 
            fontSize: '0.75rem', 
            marginBottom: '10px',
            fontStyle: 'italic',
          }}>
            移动光标查看K线数据
          </div>
        )}
        
        {/* 图层图例 */}
        <div style={{ 
          borderTop: crosshairData ? '1px solid #404040' : 'none',
          paddingTop: crosshairData ? '8px' : '0',
        }}>
          <div style={{ marginBottom: '6px', fontWeight: 'bold', color: '#ffffff', fontSize: '0.8rem' }}>图层</div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '4px',
          }}>
            <div style={{
              width: '16px',
              height: '8px',
              backgroundColor: chartColors.upColor,
              borderRadius: '2px',
            }} />
            <span style={{ color: '#aaa', fontSize: '0.75rem' }}>1分钟</span>
          </div>
          {fourHourData.length > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <div style={{
                width: '16px',
                height: '8px',
                backgroundColor: fourHourColors.upColor,
                borderRadius: '2px',
                border: `1px solid ${fourHourColors.upColor}`,
              }} />
              <span style={{ color: '#aaa', fontSize: '0.75rem' }}>4小时</span>
            </div>
          )}
        </div>
      </div>

      {/* 订单列表 */}
      {(pendingOrders.length > 0 || filledOrders.length > 0) && (
        <div style={{
          position: 'absolute',
          bottom: '60px',
          left: '10px',
          zIndex: 10,
          backgroundColor: 'rgba(30, 30, 30, 0.95)',
          padding: '10px',
          borderRadius: '6px',
          fontSize: '0.8rem',
          maxHeight: '300px',
          overflowY: 'auto',
          minWidth: '200px',
        }}>
          {/* 挂单列表 */}
          {pendingOrders.length > 0 && (
            <>
              <div style={{ marginBottom: '8px', fontWeight: 'bold', color: '#ffffff' }}>
                挂单 ({pendingOrders.length})
              </div>
              {pendingOrders.map(order => (
                <div key={order.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 8px',
                  backgroundColor: '#2a2a2a',
                  borderRadius: '4px',
                  marginBottom: '4px',
                  borderLeft: `3px solid ${order.side === 'buy' ? '#ff4757' : '#00d9ff'}`,
                }}>
                  <span style={{ 
                    color: order.side === 'buy' ? '#ff4757' : '#00d9ff',
                    fontWeight: '600',
                  }}>
                    {order.side === 'buy' ? '买' : '卖'}
                  </span>
                  <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                    {order.price.toFixed(0)}
                  </span>
                  <span style={{ color: '#888' }}>×{order.quantity}</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
                    <button
                      onClick={() => simulateFillOrder(order.id)}
                      style={{
                        padding: '2px 6px',
                        backgroundColor: '#00d9ff',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '3px',
                        cursor: 'pointer',
                        fontSize: '0.7rem',
                      }}
                      title="模拟成交"
                    >
                      成交
                    </button>
                    <button
                      onClick={() => cancelPendingOrder(order.id)}
                      style={{
                        padding: '2px 6px',
                        backgroundColor: 'transparent',
                        color: '#ff4757',
                        border: '1px solid #ff4757',
                        borderRadius: '3px',
                        cursor: 'pointer',
                        fontSize: '0.7rem',
                      }}
                    >
                      撤单
                    </button>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* 成交订单列表 */}
          {filledOrders.length > 0 && (
            <>
              <div style={{ 
                marginTop: pendingOrders.length > 0 ? '12px' : '0',
                marginBottom: '8px', 
                fontWeight: 'bold', 
                color: '#ffffff',
                borderTop: pendingOrders.length > 0 ? '1px solid #404040' : 'none',
                paddingTop: pendingOrders.length > 0 ? '12px' : '0',
              }}>
                持仓 ({filledOrders.length})
              </div>
              {filledOrders.map(order => (
                <div key={order.id} style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  padding: '8px',
                  backgroundColor: '#2a2a2a',
                  borderRadius: '4px',
                  marginBottom: '4px',
                  borderLeft: `3px solid ${order.side === 'buy' ? '#ff4757' : '#00d9ff'}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ 
                      color: order.side === 'buy' ? '#ff4757' : '#00d9ff',
                      fontWeight: '600',
                    }}>
                      {order.side === 'buy' ? '买入' : '卖出'}
                    </span>
                    <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                      {order.filledPrice?.toFixed(0)}
                    </span>
                    <span style={{ color: '#888' }}>×{order.quantity}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem' }}>
                    {order.stopLoss && (
                      <span style={{ color: '#ffa502' }}>
                        止损: {order.stopLoss.toFixed(0)}
                      </span>
                    )}
                    {order.takeProfit && (
                      <span style={{ color: '#1e90ff' }}>
                        止盈: {order.takeProfit.toFixed(0)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      <div 
        ref={chartContainerRef} 
        style={{ 
          width: '100%', 
          height,
          cursor: isDrawing ? 'crosshair' : getCursorStyle(isNearPriceLine, isPriceLineDragging),
        }} 
      />

      {loading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          color: '#ffffff',
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          padding: '1.5rem 2rem',
          borderRadius: '12px',
          zIndex: 20,
          minWidth: '200px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        }}>
          <div className="loading-spinner"></div>
          <p style={{ marginTop: '12px', marginBottom: '4px', fontSize: '0.95rem' }}>
            {loadingStage || '加载中...'}
          </p>
          <p style={{ margin: 0, fontSize: '0.75rem', color: '#888' }}>
            请稍候
          </p>
        </div>
      )}

      {/* 下单确认弹窗 */}
      <OrderDialog
        isOpen={isOrderDialogOpen}
        price={pendingOrderPrice || 0}
        onConfirm={confirmOrder}
        onCancel={closeOrderDialog}
      />
    </div>
  )
}
