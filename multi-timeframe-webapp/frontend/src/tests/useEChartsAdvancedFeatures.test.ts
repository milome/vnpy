import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEChartsAutoTrailingStopLoss } from '../hooks/useEChartsAutoTrailingStopLoss'
import { useEChartsDualStopLoss } from '../hooks/useEChartsDualStopLoss'
import { useEChartsEntryLineDrag } from '../hooks/useEChartsEntryLineDrag'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { OrderService } from '../services/orderService'
import { ChartPriceLine, PriceLineType, OrderSide, OrderStatus } from '../types'
import type { EChartsType } from 'echarts'

/**
 * ECharts高级功能Hook单元测试
 * E5: 自动追踪止损
 * E6: 双止损保护
 * E7: 从入场线拖拽创建止损/止盈
 */

describe('E5: useEChartsAutoTrailingStopLoss', () => {
  let mockPriceLineManager: EChartsPriceLineManager
  let orderService: OrderService

  beforeEach(() => {
    mockPriceLineManager = {
      getLinesByOrderId: vi.fn().mockReturnValue([]),
      updateLine: vi.fn(),
      createStopLossLine: vi.fn().mockReturnValue({ id: 'sl-new', type: PriceLineType.STOP_LOSS }),
    } as unknown as EChartsPriceLineManager

    orderService = new OrderService()
  })

  it('应该初始化默认值', () => {
    const { result } = renderHook(() =>
      useEChartsAutoTrailingStopLoss({
        priceLineManager: mockPriceLineManager,
        orderService,
        defaultStopLossOffset: 50,
      })
    )

    expect(result.current.stopLossOffset).toBe(50)
    expect(result.current.autoTrailingEnabled).toBe(true)
  })

  it('应该计算买入订单的止损价', () => {
    const { result } = renderHook(() =>
      useEChartsAutoTrailingStopLoss({
        priceLineManager: mockPriceLineManager,
        orderService,
        defaultStopLossOffset: 50,
      })
    )

    const stopLossPrice = result.current.calculateStopLossPrice(25000, OrderSide.BUY)
    expect(stopLossPrice).toBe(24950) // 25000 - 50
  })

  it('应该计算卖出订单的止损价', () => {
    const { result } = renderHook(() =>
      useEChartsAutoTrailingStopLoss({
        priceLineManager: mockPriceLineManager,
        orderService,
        defaultStopLossOffset: 50,
      })
    )

    const stopLossPrice = result.current.calculateStopLossPrice(25000, OrderSide.SELL)
    expect(stopLossPrice).toBe(25050) // 25000 + 50
  })

  it('应该更新止损点数', () => {
    const { result } = renderHook(() =>
      useEChartsAutoTrailingStopLoss({
        priceLineManager: mockPriceLineManager,
        orderService,
      })
    )

    act(() => {
      result.current.setStopLossOffset(100)
    })

    expect(result.current.stopLossOffset).toBe(100)
  })

  it('禁用自动追踪时不应更新止损', () => {
    // 先创建订单
    const order = orderService.createOrder({
      side: OrderSide.BUY,
      price: 25000,
      quantity: 1,
    })

    const { result } = renderHook(() =>
      useEChartsAutoTrailingStopLoss({
        priceLineManager: mockPriceLineManager,
        orderService,
      })
    )

    // 禁用自动追踪
    act(() => {
      result.current.setAutoTrailingEnabled(false)
    })

    // 尝试更新止损
    act(() => {
      result.current.updateStopLossOnPendingDrag(order.id, 25100)
    })

    expect(mockPriceLineManager.updateLine).not.toHaveBeenCalled()
    expect(mockPriceLineManager.createStopLossLine).not.toHaveBeenCalled()
  })
})

describe('E6: useEChartsDualStopLoss', () => {
  let mockPriceLineManager: EChartsPriceLineManager

  const mockStopLossLine: ChartPriceLine = {
    id: 'sl-1',
    orderId: 'order1',
    type: PriceLineType.STOP_LOSS,
    price: 24900,
    color: '#ffa502',
    lineWidth: 1,
    lineStyle: 'dashed',
    title: '止损 @ 24900',
    draggable: true,
  }

  beforeEach(() => {
    mockPriceLineManager = {
      createPriceLine: vi.fn((config) => ({ ...config })),
      updateLine: vi.fn(),
      removeLine: vi.fn().mockReturnValue(true),
    } as unknown as EChartsPriceLineManager
  })

  it('应该初始化为非拖动状态', () => {
    const { result } = renderHook(() =>
      useEChartsDualStopLoss({
        priceLineManager: mockPriceLineManager,
      })
    )

    expect(result.current.isDraggingStopLoss).toBe(false)
    expect(result.current.isProtectionActive).toBe(false)
  })

  it('开始拖动时应创建影子线', () => {
    const { result } = renderHook(() =>
      useEChartsDualStopLoss({
        priceLineManager: mockPriceLineManager,
      })
    )

    act(() => {
      result.current.startDragStopLoss(mockStopLossLine, OrderSide.BUY)
    })

    expect(result.current.isDraggingStopLoss).toBe(true)
    expect(result.current.isProtectionActive).toBe(true)
    expect(result.current.originalPrice).toBe(24900)
    expect(mockPriceLineManager.createPriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        type: PriceLineType.SHADOW,
        price: 24900,
        draggable: false,
      })
    )
  })

  it('更新拖动时影子线应滞后跟随', () => {
    const { result } = renderHook(() =>
      useEChartsDualStopLoss({
        priceLineManager: mockPriceLineManager,
        lagFactor: 0.3,
      })
    )

    act(() => {
      result.current.startDragStopLoss(mockStopLossLine, OrderSide.BUY)
    })

    // 第一次更新：拖到24800
    act(() => {
      result.current.updateDragStopLoss(24800)
    })

    // 影子线应该滞后：24900 + (24800-24900)*0.3 = 24900 - 30 = 24870
    expect(result.current.shadowPrice).toBeCloseTo(24870)
  })

  it('确认拖动时应删除影子线', () => {
    const { result } = renderHook(() =>
      useEChartsDualStopLoss({
        priceLineManager: mockPriceLineManager,
      })
    )

    act(() => {
      result.current.startDragStopLoss(mockStopLossLine, OrderSide.BUY)
    })

    act(() => {
      result.current.updateDragStopLoss(24800)
    })

    let confirmedPrice: number | null = null
    act(() => {
      confirmedPrice = result.current.confirmDragStopLoss()
    })

    expect(confirmedPrice).toBe(24800)
    expect(result.current.isDraggingStopLoss).toBe(false)
    expect(mockPriceLineManager.removeLine).toHaveBeenCalled()
  })

  it('取消拖动时应恢复原始价格并删除影子线', () => {
    const { result } = renderHook(() =>
      useEChartsDualStopLoss({
        priceLineManager: mockPriceLineManager,
      })
    )

    act(() => {
      result.current.startDragStopLoss(mockStopLossLine, OrderSide.BUY)
    })

    act(() => {
      result.current.updateDragStopLoss(24800)
    })

    act(() => {
      result.current.cancelDragStopLoss()
    })

    expect(result.current.isDraggingStopLoss).toBe(false)
    expect(mockPriceLineManager.removeLine).toHaveBeenCalled()
    expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith(
      'sl-1',
      expect.objectContaining({ price: 24900 })
    )
  })
})

describe('E7: useEChartsEntryLineDrag', () => {
  let mockPriceLineManager: EChartsPriceLineManager
  let orderService: OrderService
  let mockChart: EChartsType

  const mockEntryLine: ChartPriceLine = {
    id: 'entry-1',
    orderId: 'order1',
    type: PriceLineType.ENTRY,
    price: 25000,
    color: '#ff4757',
    lineWidth: 2,
    lineStyle: 'solid',
    title: '入场 @ 25000',
    draggable: false,
  }

  // 模拟价格到像素的转换
  const mockPriceToPixel = (price: number) => 500 - (price - 25000) * 0.1

  beforeEach(() => {
    orderService = new OrderService()
    // 创建测试订单
    orderService.createOrder({
      side: OrderSide.BUY,
      price: 25000,
      quantity: 1,
    })

    mockPriceLineManager = {
      getAllLines: vi.fn().mockReturnValue([mockEntryLine]),
      createPriceLine: vi.fn((config) => ({ ...config })),
      createStopLossLine: vi.fn((config) => ({ id: 'sl-new', ...config })),
      createTakeProfitLine: vi.fn((config) => ({ id: 'tp-new', ...config })),
      updateLine: vi.fn(),
      removeLine: vi.fn().mockReturnValue(true),
    } as unknown as EChartsPriceLineManager

    mockChart = {
      convertToPixel: vi.fn((coordSys, value) => [0, mockPriceToPixel(value[1])]),
      convertFromPixel: vi.fn((coordSys, value) => {
        const price = 25000 - (value[1] - 500) / 0.1
        return [0, price]
      }),
    } as unknown as EChartsType
  })

  it('应该初始化为非创建状态', () => {
    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    expect(result.current.isCreatingFromEntry).toBe(false)
    expect(result.current.creatingLineType).toBeNull()
  })

  it('应该找到最近的入场线', () => {
    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    // pixelY = 500 对应 price = 25000
    const nearestLine = result.current.findNearestEntryLine(502)
    expect(nearestLine).toBeDefined()
    expect(nearestLine!.type).toBe(PriceLineType.ENTRY)
  })

  it('开始从入场线创建时应记录状态', () => {
    // 先更新mockEntryLine的orderId为实际订单ID
    const orders = orderService.getPendingOrders()
    mockEntryLine.orderId = orders[0].id

    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    act(() => {
      result.current.startCreateFromEntry(mockEntryLine, 500) // pixelY = 500
    })

    expect(result.current.isCreatingFromEntry).toBe(true)
    expect(result.current.entryPrice).toBe(25000)
  })

  it('买入订单向下拖拽应创建止损线', () => {
    const orders = orderService.getPendingOrders()
    mockEntryLine.orderId = orders[0].id

    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    act(() => {
      result.current.startCreateFromEntry(mockEntryLine, 500)
    })

    // 向下拖拽（pixelY增大 = 价格降低）足够距离
    act(() => {
      result.current.updateCreateFromEntry(520)
    })

    expect(result.current.creatingLineType).toBe('stop_loss')
  })

  it('买入订单向上拖拽应创建止盈线', () => {
    const orders = orderService.getPendingOrders()
    mockEntryLine.orderId = orders[0].id

    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    act(() => {
      result.current.startCreateFromEntry(mockEntryLine, 500)
    })

    // 向上拖拽（pixelY减小 = 价格升高）足够距离
    act(() => {
      result.current.updateCreateFromEntry(480)
    })

    expect(result.current.creatingLineType).toBe('take_profit')
  })

  it('拖拽距离不足时不应创建', () => {
    const orders = orderService.getPendingOrders()
    mockEntryLine.orderId = orders[0].id

    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    act(() => {
      result.current.startCreateFromEntry(mockEntryLine, 500)
    })

    // 只移动5像素（小于最小拖拽距离15像素）
    act(() => {
      result.current.updateCreateFromEntry(505)
    })

    expect(result.current.creatingLineType).toBeNull()
    expect(mockPriceLineManager.createPriceLine).not.toHaveBeenCalled()
  })

  it('取消创建时应删除预览线', () => {
    const orders = orderService.getPendingOrders()
    mockEntryLine.orderId = orders[0].id

    const { result } = renderHook(() =>
      useEChartsEntryLineDrag({
        priceLineManager: mockPriceLineManager,
        orderService,
        chart: mockChart,
      })
    )

    act(() => {
      result.current.startCreateFromEntry(mockEntryLine, 500)
    })

    act(() => {
      result.current.updateCreateFromEntry(520) // 创建预览线
    })

    act(() => {
      result.current.cancelCreateFromEntry()
    })

    expect(result.current.isCreatingFromEntry).toBe(false)
    expect(mockPriceLineManager.removeLine).toHaveBeenCalled()
  })
})

