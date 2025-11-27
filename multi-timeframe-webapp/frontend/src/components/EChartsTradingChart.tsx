/**
 * ECharts交易图表组件
 * 集成了所有交易功能：画线下单、价格线拖拽、自动止损等
 */
import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption, EChartsType } from 'echarts'
import { Timeframe, ChartKLineData, TradingOrder, PriceLineType, OrderSide } from '../types'
import { dataService } from '../services/dataService'
import { OrderService } from '../services/orderService'
import {
  createBaseChartOption,
  createCategoryCandlestickSeries,
  TIMEFRAME_CONFIGS,
  formatTimeLabel,
} from '../utils/chartConfig'
import { aggregateTo4Hours } from '../utils/timeframeAggregator'
import { createFourHourCandleLineSeriesForCategoryAxis, convertAllToFourHourCandleData } from '../utils/fourHourCandleRenderer'

// ECharts交易功能
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { EChartsOrderMarkerManager } from '../utils/echartsOrderMarkerManager'
import { useEChartsDrawingOrder } from '../hooks/useEChartsDrawingOrder'
import { useEChartsPriceLineDrag } from '../hooks/useEChartsPriceLineDrag'
import { useEChartsAutoTrailingStopLoss } from '../hooks/useEChartsAutoTrailingStopLoss'
import { useEChartsDualStopLoss } from '../hooks/useEChartsDualStopLoss'
import { useEChartsEntryLineDrag } from '../hooks/useEChartsEntryLineDrag'
import { pixelYToPrice } from '../utils/echartsCrosshairHelper'

// UI组件
import CrosshairDataPanel, { CrosshairData } from './CrosshairDataPanel'
import TradingToolbar from './TradingToolbar'
import OrderListPanel from './OrderListPanel'
import StatusIndicator from './StatusIndicator'
import OrderDialog from './OrderDialog'
import './MultiTimeframeChart.css'

interface EChartsTradingChartProps {
  timeframes: Timeframe[]
  height?: string
  startDate?: string
  endDate?: string
}

// 全局订单服务实例
const orderService = new OrderService()

/**
 * ECharts交易图表组件
 * 完整集成TradingView的所有交易功能
 */
export default function EChartsTradingChart({
  timeframes,
  height = '100%',
  startDate,
  endDate,
}: EChartsTradingChartProps) {
  // 图表状态
  const [chartOption, setChartOption] = useState<EChartsOption>(createBaseChartOption())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<ReactECharts>(null)
  const chartInstanceRef = useRef<EChartsType | null>(null)

  // 数据
  const [oneMinData, setOneMinData] = useState<ChartKLineData[]>([])
  const [fourHourData, setFourHourData] = useState<ChartKLineData[]>([])

  // 交易管理器
  const [priceLineManager] = useState(() => new EChartsPriceLineManager())
  const [markerManager] = useState(() => new EChartsOrderMarkerManager())
  
  // 价格线状态（用于触发图表更新）
  const [priceLines, setPriceLines] = useState<import('../types').ChartPriceLine[]>([])

  // 订单状态
  const [pendingOrders, setPendingOrders] = useState<TradingOrder[]>([])
  const [filledOrders, setFilledOrders] = useState<TradingOrder[]>([])

  // 十字光标数据
  const [crosshairData, setCrosshairData] = useState<CrosshairData | null>(null)

  // 鼠标状态
  const [isNearPriceLine, setIsNearPriceLine] = useState(false)

  // 获取ECharts实例
  const getChartInstance = useCallback((): EChartsType | null => {
    if (chartInstanceRef.current) return chartInstanceRef.current
    if (chartRef.current) {
      chartInstanceRef.current = chartRef.current.getEchartsInstance()
      return chartInstanceRef.current
    }
    return null
  }, [])

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
    handleClick: handleDrawingClick,
    handleEscape,
    confirmOrder,
    closeOrderDialog,
    cancelPendingOrder,
  } = useEChartsDrawingOrder({
    priceLineManager,
    orderService,
  })

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
  } = useEChartsPriceLineDrag({
    priceLineManager,
    getChart: getChartInstance,
    onPriceChange: (lineId, orderId, newPrice, lineType, originalPrice) => {
      // 更新订单
      if (lineType === PriceLineType.STOP_LOSS) {
        orderService.updateOrder({ id: orderId, stopLoss: newPrice })
      } else if (lineType === PriceLineType.TAKE_PROFIT) {
        orderService.updateOrder({ id: orderId, takeProfit: newPrice })
      } else if (lineType === PriceLineType.PENDING) {
        orderService.updateOrder({ id: orderId, price: newPrice })
        
        // 挂单线移动时，同步移动止损线和止盈线
        const priceDiff = newPrice - originalPrice
        const orderLines = priceLineManager.getLinesByOrderId(orderId)
        
        orderLines.forEach(line => {
          if (line.type === PriceLineType.STOP_LOSS) {
            const newStopLoss = line.price + priceDiff
            priceLineManager.updateLine(line.id, {
              price: newStopLoss,
              title: `止损 @ ${newStopLoss.toFixed(0)}`,
            })
            orderService.updateOrder({ id: orderId, stopLoss: newStopLoss })
          } else if (line.type === PriceLineType.TAKE_PROFIT) {
            const newTakeProfit = line.price + priceDiff
            priceLineManager.updateLine(line.id, {
              price: newTakeProfit,
              title: `止盈 @ ${newTakeProfit.toFixed(0)}`,
            })
            orderService.updateOrder({ id: orderId, takeProfit: newTakeProfit })
          }
        })
      }
    },
  })

  // 自动追踪止损Hook
  const {
    stopLossOffset,
    autoTrailingEnabled,
    setStopLossOffset,
    setAutoTrailingEnabled,
    updateStopLossOnPendingDrag,
  } = useEChartsAutoTrailingStopLoss({
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
    checkShadowStopLossBreached,
  } = useEChartsDualStopLoss({
    priceLineManager,
    lagFactor: 0.3,
    onShadowStopLossTriggered: (orderId, triggerPrice) => {
      // 当价格突破影子止损线时，自动平仓
      closePosition(orderId)
    },
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
  } = useEChartsEntryLineDrag({
    priceLineManager,
    orderService,
    getChart: getChartInstance,
  })

  // 更新订单列表
  const refreshOrders = useCallback(() => {
    setPendingOrders(orderService.getPendingOrders())
    setFilledOrders(orderService.getFilledOrders())
  }, [])

  // 设置价格线变化回调
  useEffect(() => {
    priceLineManager.setOnChangeCallback((lines) => {
      // 只保留非预览线用于显示（预览线单独处理）
      const nonPreviewLines = lines.filter(l => l.type !== PriceLineType.PREVIEW)
      setPriceLines(nonPreviewLines)
    })
  }, [priceLineManager])

  // 订阅订单变化
  useEffect(() => {
    // 订阅所有订单事件
    orderService.onOrderCreated(refreshOrders)
    orderService.onOrderFilled(refreshOrders)
    orderService.onOrderCancelled(refreshOrders)
    orderService.onOrderUpdated(refreshOrders)

    // 初始加载
    refreshOrders()

    return () => {
      // 取消订阅
      orderService.offOrderCreated(refreshOrders)
      orderService.offOrderFilled(refreshOrders)
      orderService.offOrderCancelled(refreshOrders)
      orderService.offOrderUpdated(refreshOrders)
    }
  }, [refreshOrders])

  // 当拖拽止损线时，检测市场价格是否突破影子止损
  useEffect(() => {
    if (!isDraggingStopLoss || oneMinData.length === 0) return

    // 获取当前市场价格（最新K线的收盘价）
    const currentMarketPrice = oneMinData[oneMinData.length - 1].close
    
    // 检查是否突破影子止损
    checkShadowStopLossBreached(currentMarketPrice)
  }, [isDraggingStopLoss, oneMinData, checkShadowStopLossBreached])

  // 加载图表数据
  useEffect(() => {
    loadChartData()
  }, [timeframes, startDate, endDate])

  // 键盘事件处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleEscape()
        if (isPriceLineDragging) cancelDrag()
        if (isCreatingFromEntry) cancelCreateFromEntry()
        if (isDraggingStopLoss) cancelDragStopLoss()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleEscape, isPriceLineDragging, cancelDrag, isCreatingFromEntry, cancelCreateFromEntry, isDraggingStopLoss, cancelDragStopLoss])

  // 过滤数据
  const filterDataByTimeRange = (data: ChartKLineData[]): ChartKLineData[] => {
    if (!startDate && !endDate) return data

    const startTimestamp = startDate ? new Date(startDate).getTime() : 0
    const endTimestamp = endDate ? new Date(endDate).getTime() + 24 * 60 * 60 * 1000 : Infinity

    return data.filter(item => item.timestamp >= startTimestamp && item.timestamp < endTimestamp)
  }

  // 加载数据
  const loadChartData = async () => {
    try {
      setLoading(true)
      setError(null)

      dataService.clearCache()
      const originalLimit = dataService.getDataLimit()
      dataService.setDataLimit(-1)

      const oneMinRawData = await dataService.getData(Timeframe.ONE_MINUTE)
      dataService.setDataLimit(originalLimit)

      const filteredOneMinData = filterDataByTimeRange(oneMinRawData)
      const calculated4HourData = aggregateTo4Hours(filteredOneMinData)

      setOneMinData(filteredOneMinData)
      setFourHourData(calculated4HourData)

      console.log(`📊 Loaded ${filteredOneMinData.length} 1-min, ${calculated4HourData.length} 4-hour candles`)

      // 使用1分钟数据作为X轴基准（category轴跳过休市时间）
      let baseData = filteredOneMinData
      if (baseData.length > 5000) {
        // 如果数据太多，进行采样以提高性能
        const step = Math.ceil(baseData.length / 5000)
        baseData = filteredOneMinData.filter((_, index) => index % step === 0)
      }

      // 创建时间标签数组（category轴数据）
      const timeLabels = baseData.map(item => formatTimeLabel(item.timestamp))
      
      // 创建时间戳到索引的映射（用于4小时K线定位）
      const timestampToIndex = new Map<number, number>()
      baseData.forEach((item, index) => {
        timestampToIndex.set(item.timestamp, index)
      })

      // 创建series
      const series: EChartsOption['series'] = []

      // 1分钟K线数据（category轴格式）
      if (timeframes.includes(Timeframe.ONE_MINUTE)) {
        const config = TIMEFRAME_CONFIGS[Timeframe.ONE_MINUTE]
        // ECharts K线格式: [open, close, low, high]
        const chartData: [number, number, number, number][] = baseData.map((item) => [
          item.open,
          item.close,
          item.low,
          item.high,
        ])
        const seriesConfig = createCategoryCandlestickSeries(getTimeframeName(Timeframe.ONE_MINUTE), chartData, config)
        series.push(seriesConfig)
      }

      // 4小时K线数据（使用自定义渲染，category轴版本）
      if (timeframes.includes(Timeframe.FOUR_HOURS) && calculated4HourData.length > 0) {
        const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
        const fourHourData = convertAllToFourHourCandleData(calculated4HourData)
        const lineSeriesConfig = createFourHourCandleLineSeriesForCategoryAxis(
          getTimeframeName(Timeframe.FOUR_HOURS),
          fourHourData,
          config,
          timestampToIndex  // 传入映射用于定位
        )
        series.push(lineSeriesConfig)
      }

      const newOption: EChartsOption = {
        ...createBaseChartOption(),
        xAxis: {
          type: 'category',
          data: timeLabels,
          boundaryGap: true,
          axisLine: { lineStyle: { color: '#404040' } },
          axisLabel: { 
            color: '#ffffff',
            interval: 'auto',
            rotate: 0,
          },
          splitLine: { show: true, lineStyle: { color: '#404040', opacity: 0.3 } },
        },
        legend: {
          data: timeframes.map(getTimeframeName),
          textStyle: { color: '#ffffff' },
          top: 10,
          right: 50,
        },
        series,
      }

      setChartOption(newOption)
      setLoading(false)
    } catch (err) {
      console.error('Error loading chart data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load chart data')
      setLoading(false)
    }
  }

  // 当价格线变化时，更新图表markLine配置
  useEffect(() => {
    const chart = getChartInstance()
    if (!chart) return

    // 将价格线转换为ECharts markLine格式
    const markLineData = priceLines
      .filter(line => line.type !== PriceLineType.PREVIEW) // 排除预览线
      .map(line => ({
        yAxis: line.price,
        name: line.id,
        lineStyle: {
          color: line.color,
          width: line.lineWidth || 2,
          type: line.lineStyle === 'dashed' ? 'dashed' as const : line.lineStyle === 'dotted' ? 'dotted' as const : 'solid' as const,
        },
        label: {
          show: true,
          formatter: () => line.title || `${line.price.toFixed(0)}`,
          position: 'end' as const,
          color: '#fff',
          backgroundColor: line.color,
          padding: [4, 8],
          borderRadius: 4,
          fontSize: 11,
        },
      }))

    // 获取当前option并更新第一个series的markLine
    try {
      const currentOption = chart.getOption()
      const series = currentOption?.series as any[]
      if (series && series.length > 0) {
        // 只更新markLine，不改变其他配置
        chart.setOption({
          series: [{
            markLine: {
              silent: false,
              animation: false,
              symbol: ['none', 'none'],
              data: markLineData,
            }
          }]
        })
      }
    } catch (err) {
      console.warn('Failed to update markLine:', err)
    }
  }, [priceLines, getChartInstance])

  const getTimeframeName = (timeframe: Timeframe): string => {
    const names: Record<Timeframe, string> = {
      [Timeframe.ONE_MINUTE]: '1分钟',
      [Timeframe.FIVE_MINUTES]: '5分钟',
      [Timeframe.ONE_HOUR]: '1小时',
      [Timeframe.FOUR_HOURS]: '4小时',
      [Timeframe.ONE_DAY]: '日线',
    }
    return names[timeframe]
  }

  // 图表容器引用
  const chartContainerRef = useRef<HTMLDivElement>(null)

  // 图表事件处理
  // 图表就绪状态
  const [chartReady, setChartReady] = useState(false)

  const onChartReady = useCallback((chart: EChartsType) => {
    chartInstanceRef.current = chart
    setChartReady(true)
  }, [])

  // 使用ref跟踪状态（避免闭包问题）
  const isDrawingRef = useRef(isDrawing)
  const isPriceLineDraggingRef = useRef(isPriceLineDragging)
  const isDraggingStopLossRef = useRef(isDraggingStopLoss)
  const isCreatingFromEntryRef = useRef(isCreatingFromEntry)
  
  useEffect(() => {
    isDrawingRef.current = isDrawing
  }, [isDrawing])
  
  useEffect(() => {
    isPriceLineDraggingRef.current = isPriceLineDragging
  }, [isPriceLineDragging])
  
  useEffect(() => {
    isDraggingStopLossRef.current = isDraggingStopLoss
  }, [isDraggingStopLoss])
  
  useEffect(() => {
    isCreatingFromEntryRef.current = isCreatingFromEntry
  }, [isCreatingFromEntry])

  // 平仓操作（需要在DOM事件处理之前定义）
  const closePosition = useCallback((orderId: string) => {
    const order = orderService.getOrder(orderId)
    if (!order || order.status !== 'filled') return

    // 使用当前价格作为平仓价格（简化实现）
    const closePrice = oneMinData.length > 0 ? oneMinData[oneMinData.length - 1].close : order.price
    
    // 调用orderService的平仓方法
    const closedOrder = orderService.closePosition(orderId, closePrice)
    
    if (closedOrder) {
      // 移除该订单的所有价格线
      priceLineManager.removeLinesByOrderId(orderId)
      
      // 添加平仓标记
      markerManager.addFilledOrderMarker({
        ...closedOrder,
        price: closePrice,
      })
    }
  }, [oneMinData, priceLineManager, markerManager])

  // 处理画线模式下的DOM点击事件 - 在图表准备好后设置
  useEffect(() => {
    if (!chartReady) return
    
    const container = chartContainerRef.current
    if (!container) return

    const handleContainerClick = (e: MouseEvent) => {
      // 检查点击是否来自对话框或其他overlay
      const target = e.target as HTMLElement
      if (target.closest('.order-dialog-overlay') || target.closest('.order-dialog')) {
        return
      }
      
      if (!isDrawingRef.current) return
      
      const chart = getChartInstance()
      if (!chart) return

      // 获取相对于容器的坐标
      const rect = container.getBoundingClientRect()
      const pixelY = e.clientY - rect.top
      
      // 尝试获取价格，如果失败使用备用方法
      let price = pixelYToPrice(chart, pixelY)
      
      // 如果pixelYToPrice失败，尝试从Y轴范围手动计算
      if (price === null) {
        try {
          const option = chart.getOption()
          const yAxis = option?.yAxis as any[]
          if (yAxis && yAxis[0]) {
            const chartHeight = chart.getHeight()
            const gridTop = 60  // 默认grid top
            const gridBottom = 100 // 默认grid bottom
            const plotHeight = chartHeight - gridTop - gridBottom
            
            if (pixelY >= gridTop && pixelY <= chartHeight - gridBottom) {
              const yMin = yAxis[0].min || 0
              const yMax = yAxis[0].max || 100000
              const ratio = (pixelY - gridTop) / plotHeight
              price = yMax - ratio * (yMax - yMin)
            }
          }
        } catch (err) {
          console.warn('Backup price calculation failed:', err)
        }
      }

      if (price !== null) {
        handleCrosshairMove(price)
        // 使用setTimeout确保previewPrice已更新
        setTimeout(() => {
          handleDrawingClick()
        }, 10)
      }
    }

    const handleContainerMouseMove = (e: MouseEvent) => {
      // 检查是否在对话框内
      const target = e.target as HTMLElement
      if (target.closest('.order-dialog-overlay') || target.closest('.order-dialog')) {
        return
      }
      
      const chart = getChartInstance()
      if (!chart) return

      const rect = container.getBoundingClientRect()
      const pixelY = e.clientY - rect.top
      const price = pixelYToPrice(chart, pixelY)

      // 画线模式处理
      if (isDrawingRef.current && price !== null) {
        handleCrosshairMove(price)
      }
      
      // 拖拽模式处理（使用ref避免闭包问题）
      if (isPriceLineDraggingRef.current) {
        updateDrag(pixelY)
      }
      
      // 双止损拖拽
      if (isDraggingStopLossRef.current && price !== null) {
        updateDragStopLoss(price)
      }
      
      // 从入场线创建止损/止盈
      if (isCreatingFromEntryRef.current) {
        updateCreateFromEntry(pixelY)
      }
    }

    // 处理mousedown用于拖拽
    const handleContainerMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('.order-dialog-overlay') || target.closest('.order-dialog')) {
        return
      }
      
      // 如果在画线模式，不处理拖拽
      if (isDrawingRef.current) return
      
      const chart = getChartInstance()
      if (!chart) return

      const rect = container.getBoundingClientRect()
      const pixelY = e.clientY - rect.top
      
      // 查找可拖拽的线
      const draggableLine = findNearestDraggableLine(pixelY)
      
      if (draggableLine) {
        e.preventDefault() // 阻止默认行为
        if (draggableLine.type === PriceLineType.STOP_LOSS) {
          const order = orderService.getOrder(draggableLine.orderId || '')
          if (order) {
            startDragStopLoss(draggableLine, order.side)
          }
        } else {
          startDrag(draggableLine)
        }
        return
      }

      // 查找入场线
      const entryLine = findNearestEntryLine(pixelY)
      if (entryLine) {
        e.preventDefault()
        startCreateFromEntry(entryLine, pixelY)
      }
    }

    // 处理mouseup用于结束拖拽
    // 注意：直接调用所有confirm函数，让它们内部判断是否需要执行
    // 这样可以避免状态同步延迟导致的问题
    const handleContainerMouseUp = () => {
      if (isPriceLineDraggingRef.current) {
        endDrag()
      }
      // 始终调用confirmDragStopLoss来确保影子线被删除
      confirmDragStopLoss()
      if (isCreatingFromEntryRef.current) {
        confirmCreateFromEntry()
      }
    }

    // 处理双击：挂单删除 / 已成交订单平仓 / 删除止损止盈线
    const handleContainerDoubleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('.order-dialog-overlay') || target.closest('.order-dialog')) {
        return
      }

      const chart = getChartInstance()
      if (!chart) return

      const rect = container.getBoundingClientRect()
      const pixelY = e.clientY - rect.top

      // 查找最近的订单线
      const nearestLine = findNearestOrderLine(pixelY)
      
      if (!nearestLine || !nearestLine.orderId) return

      const order = orderService.getOrder(nearestLine.orderId)
      if (!order) return

      if (order.status === 'pending') {
        // 双击挂单线 → 取消挂单（带确认弹窗）
        if (nearestLine.type === PriceLineType.PENDING) {
          if (confirm('确定要删除这个挂单吗？')) {
            cancelPendingOrder(order.id)
          }
        }
      } else if (order.status === 'filled') {
        // 双击入场线（成本线）→ 平仓（带确认弹窗）
        if (nearestLine.type === PriceLineType.ENTRY) {
          const actionText = order.side === OrderSide.BUY ? '卖出平仓' : '买入平仓'
          const confirmMsg = `确定要${actionText} ${order.quantity}手吗？\n\n持仓方向: ${order.side === OrderSide.BUY ? '多单' : '空单'}\n入场价格: ${order.filledPrice || order.price}\n\n注：平仓将通过对手价快速成交`
          
          if (confirm(confirmMsg)) {
            closePosition(order.id)
            alert(`✅ 平仓成功！\n${actionText} ${order.quantity}手`)
          }
        }
        // 双击止损线 → 删除止损线（带确认弹窗）
        else if (nearestLine.type === PriceLineType.STOP_LOSS) {
          if (confirm('确定要删除此止损线吗？\n\n⚠️ 删除后将失去止损保护')) {
            priceLineManager.removeLine(nearestLine.id)
            orderService.updateOrder({ id: order.id, stopLoss: undefined })
          }
        }
        // 双击止盈线 → 删除止盈线（带确认弹窗）
        else if (nearestLine.type === PriceLineType.TAKE_PROFIT) {
          if (confirm('确定要删除此止盈线吗？')) {
            priceLineManager.removeLine(nearestLine.id)
            orderService.updateOrder({ id: order.id, takeProfit: undefined })
          }
        }
      }
    }

    container.addEventListener('click', handleContainerClick)
    container.addEventListener('mousemove', handleContainerMouseMove)
    container.addEventListener('mousedown', handleContainerMouseDown)
    container.addEventListener('mouseup', handleContainerMouseUp)
    container.addEventListener('dblclick', handleContainerDoubleClick)

    return () => {
      container.removeEventListener('click', handleContainerClick)
      container.removeEventListener('mousemove', handleContainerMouseMove)
      container.removeEventListener('mousedown', handleContainerMouseDown)
      container.removeEventListener('mouseup', handleContainerMouseUp)
      container.removeEventListener('dblclick', handleContainerDoubleClick)
    }
  }, [chartReady, getChartInstance, handleDrawingClick, handleCrosshairMove, findNearestDraggableLine, findNearestEntryLine, findNearestOrderLine, startDrag, startDragStopLoss, startCreateFromEntry, endDrag, confirmDragStopLoss, confirmCreateFromEntry, updateDrag, updateDragStopLoss, updateCreateFromEntry, cancelPendingOrder, priceLineManager, closePosition])

  const onChartEvents = useMemo(() => ({
    mousemove: (params: any) => {
      const chart = getChartInstance()
      if (!chart) return

      const pixelY = params.event?.offsetY
      if (pixelY === undefined) return

      const price = pixelYToPrice(chart, pixelY)
      
      // 更新十字光标数据
      if (params.data && Array.isArray(params.data)) {
        // category轴格式: [open, close, low, high]
        const [open, close, low, high] = params.data
        const prevClose = open // 简化：使用开盘价作为前收
        const timeLabel = params.name || '' // category轴使用name作为时间标签
        setCrosshairData({
          time: timeLabel,
          open,
          high,
          low,
          close,
          volume: 0,
          change: close - prevClose,
          changePercent: ((close - prevClose) / prevClose) * 100,
        })
      }

      // 画线模式处理
      if (isDrawing && price !== null) {
        handleCrosshairMove(price)
      }

      // 拖拽处理
      if (isPriceLineDragging) {
        updateDrag(pixelY)
      }

      // 双止损拖拽
      if (isDraggingStopLoss && price !== null) {
        updateDragStopLoss(price)
      }

      // 创建止损/止盈
      if (isCreatingFromEntry) {
        updateCreateFromEntry(pixelY)
      }

      // 检测是否靠近价格线
      if (!isDrawing && !isPriceLineDragging && !isCreatingFromEntry) {
        const nearLine = findNearestDraggableLine(pixelY)
        setIsNearPriceLine(!!nearLine)
      }
    },
    click: () => {
      if (isDrawing) {
        handleDrawingClick()
      }
    },
    mousedown: (params: any) => {
      const chart = getChartInstance()
      if (!chart || isDrawing) return

      const pixelY = params.event?.offsetY
      if (pixelY === undefined) return

      // 检查是否点击了可拖拽的线
      const draggableLine = findNearestDraggableLine(pixelY)
      if (draggableLine) {
        if (draggableLine.type === PriceLineType.STOP_LOSS) {
          // 止损线使用双止损保护
          const order = orderService.getOrder(draggableLine.orderId || '')
          if (order) {
            startDragStopLoss(draggableLine, order.side)
          }
        } else {
          startDrag(draggableLine)
        }
        return
      }

      // 检查是否点击了入场线
      const entryLine = findNearestEntryLine(pixelY)
      if (entryLine) {
        startCreateFromEntry(entryLine, pixelY)
      }
    },
    mouseup: () => {
      if (isPriceLineDragging) {
        endDrag()
      }
      // 始终调用confirmDragStopLoss来确保影子线被删除
      confirmDragStopLoss()
      if (isCreatingFromEntry) {
        confirmCreateFromEntry()
      }
    },
    globalout: () => {
      setCrosshairData(null)
    },
  }), [
    getChartInstance,
    isDrawing,
    handleCrosshairMove,
    handleDrawingClick,
    isPriceLineDragging,
    updateDrag,
    endDrag,
    isDraggingStopLoss,
    updateDragStopLoss,
    confirmDragStopLoss,
    isCreatingFromEntry,
    updateCreateFromEntry,
    confirmCreateFromEntry,
    findNearestDraggableLine,
    findNearestEntryLine,
    startDrag,
    startDragStopLoss,
    startCreateFromEntry,
  ])

  // 模拟成交
  const simulateFillOrder = useCallback((orderId: string) => {
    const order = orderService.getOrder(orderId)
    if (!order) return

    // 获取当前挂单线的价格（可能已被拖动修改）
    const orderLines = priceLineManager.getLinesByOrderId(orderId)
    const pendingLine = orderLines.find(l => l.type === PriceLineType.PENDING)
    
    // 使用挂单线的当前价格，如果没有则使用订单原始价格
    const fillPrice = pendingLine ? pendingLine.price : order.price

    orderService.fillOrder(orderId, fillPrice)

    // 更新价格线
    if (pendingLine) {
      priceLineManager.removeLine(pendingLine.id)
      priceLineManager.createEntryLine({
        orderId,
        price: fillPrice,
        side: order.side,
        quantity: order.quantity,
      })
    }

    // 添加成交标记
    const filledOrder = orderService.getOrder(orderId)
    if (filledOrder) {
      markerManager.addFilledOrderMarker(filledOrder)
    }
  }, [priceLineManager, markerManager])

  // 图例项
  const legendItems = useMemo(() => [
    { color: '#ff4757', label: '1分钟' },
    { color: '#4a9eff', label: '4小时' },
  ], [])

  // 鼠标样式
  const cursorStyle = getCursorStyle(isNearPriceLine, isPriceLineDragging || isDraggingStopLoss)

  if (loading) {
    return (
      <div className="chart-loading">
        <div className="loading-spinner"></div>
        <p>Loading chart data...</p>
      </div>
    )
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
    <div 
      ref={chartContainerRef}
      className="multi-timeframe-chart" 
      style={{ cursor: cursorStyle }}
    >
      <ReactECharts
        ref={chartRef}
        option={chartOption}
        style={{ height, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        opts={{ renderer: 'canvas' }}
        onChartReady={onChartReady}
        onEvents={onChartEvents}
      />

      {/* K线数据面板 */}
      <CrosshairDataPanel
        data={crosshairData}
        showLegend={true}
        legendItems={legendItems}
      />

      {/* 工具栏 */}
      <TradingToolbar
        drawingMode={drawingMode}
        isDrawing={isDrawing}
        onEnableDrawingMode={enableDrawingMode}
        onDisableDrawingMode={disableDrawingMode}
        autoTrailingEnabled={autoTrailingEnabled}
        stopLossOffset={stopLossOffset}
        onSetAutoTrailingEnabled={setAutoTrailingEnabled}
        onSetStopLossOffset={setStopLossOffset}
      />

      {/* 订单列表 */}
      <OrderListPanel
        orders={[...pendingOrders, ...filledOrders]}
        onSimulateFill={simulateFillOrder}
        onCancelOrder={cancelPendingOrder}
      />

      {/* 状态提示 */}
      <StatusIndicator
        type="drawing"
        visible={isDrawing}
        drawingPrice={previewPrice || undefined}
      />

      <StatusIndicator
        type="dragging"
        visible={isPriceLineDragging && !isDraggingStopLoss}
        draggingInfo={draggingLine ? {
          originalPrice: draggingLine.price,
          currentPrice: draggingLine.price,
        } : undefined}
      />

      <StatusIndicator
        type="dualStopLoss"
        visible={isDraggingStopLoss && isProtectionActive}
        draggingInfo={dualStopLossOriginalPrice !== null ? {
          originalPrice: dualStopLossOriginalPrice,
          currentPrice: dualStopLossCurrentPrice || dualStopLossOriginalPrice,
          shadowPrice: dualStopLossShadowPrice || undefined,
        } : undefined}
      />

      <StatusIndicator
        type="creating"
        visible={isCreatingFromEntry}
        creatingInfo={creatingEntryPrice !== null && creatingCurrentPrice !== null ? {
          lineType: creatingLineType || 'stop_loss',
          entryPrice: creatingEntryPrice,
          currentPrice: creatingCurrentPrice,
        } : undefined}
      />

      <StatusIndicator
        type="nearLine"
        visible={!isDrawing && !isPriceLineDragging && !isCreatingFromEntry && isNearPriceLine}
      />

      {/* 下单对话框 */}
      <OrderDialog
        isOpen={isOrderDialogOpen}
        price={pendingOrderPrice || 0}
        onConfirm={confirmOrder}
        onCancel={closeOrderDialog}
      />
    </div>
  )
}

