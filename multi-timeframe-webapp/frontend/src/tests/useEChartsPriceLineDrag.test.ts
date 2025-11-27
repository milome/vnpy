import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEChartsPriceLineDrag } from '../hooks/useEChartsPriceLineDrag'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { ChartPriceLine, PriceLineType, OrderSide } from '../types'
import type { EChartsType } from 'echarts'

/**
 * ECharts价格线拖拽Hook单元测试
 */

// 模拟价格到像素的转换函数
const mockPriceToPixel = (price: number) => 500 - (price - 25000) * 0.1 // 价格越高，Y越小

describe('useEChartsPriceLineDrag', () => {
  let mockPriceLineManager: EChartsPriceLineManager
  let mockChart: EChartsType
  let onPriceChange: ReturnType<typeof vi.fn>
  let mockLines: ChartPriceLine[]

  beforeEach(() => {
    // 模拟价格线数据
    mockLines = [
      {
        id: 'line1',
        orderId: 'order1',
        type: PriceLineType.STOP_LOSS,
        price: 24900, // pixelY = 510
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        title: '止损 @ 24900',
        draggable: true,
      },
      {
        id: 'line2',
        orderId: 'order1',
        type: PriceLineType.ENTRY,
        price: 25000, // pixelY = 500
        color: '#ff4757',
        lineWidth: 2,
        lineStyle: 'solid',
        title: '入场 @ 25000',
        draggable: false, // 入场线不可拖拽
      },
      {
        id: 'line3',
        orderId: 'order1',
        type: PriceLineType.TAKE_PROFIT,
        price: 25200, // pixelY = 480
        color: '#1e90ff',
        lineWidth: 1,
        lineStyle: 'dashed',
        title: '止盈 @ 25200',
        draggable: true,
      },
    ]

    // Mock ECharts实例
    mockChart = {
      convertToPixel: vi.fn((coordSys: any, value: [number, number]) => {
        // 模拟Y轴转换：价格越高，像素Y越小
        return [0, mockPriceToPixel(value[1])]
      }),
      convertFromPixel: vi.fn((coordSys: any, value: [number, number]) => {
        // 逆转换：像素Y转价格
        const price = 25000 - (value[1] - 500) / 0.1
        return [0, price]
      }),
    } as unknown as EChartsType

    // Mock价格线管理器
    mockPriceLineManager = {
      getAllLines: vi.fn(() => [...mockLines]),
      updateLine: vi.fn((id: string, updates: Partial<ChartPriceLine>) => {
        const line = mockLines.find(l => l.id === id)
        if (line) {
          Object.assign(line, updates)
        }
        return line
      }),
    } as unknown as EChartsPriceLineManager

    onPriceChange = vi.fn()
  })

  describe('初始状态', () => {
    it('应该初始化为非拖拽状态', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      expect(result.current.isDragging).toBe(false)
      expect(result.current.draggingLine).toBeNull()
    })
  })

  describe('查找最近的可拖拽线', () => {
    it('应该找到最近的可拖拽线', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      // pixelY = 512，最接近line1(止损线, pixelY=510)
      const nearestLine = result.current.findNearestDraggableLine(512)
      expect(nearestLine).toBeDefined()
      expect(nearestLine!.id).toBe('line1')
    })

    it('应该只找到可拖拽的线', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      // pixelY = 500，最接近line2(入场线)但入场线不可拖拽
      // 应该找不到线（阈值内没有可拖拽的线）
      const nearestLine = result.current.findNearestDraggableLine(500)
      expect(nearestLine).toBeUndefined()
    })

    it('超出阈值时应该返回undefined', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
          dragThreshold: 5,
        })
      )

      // pixelY = 450，离所有线都很远
      const nearestLine = result.current.findNearestDraggableLine(450)
      expect(nearestLine).toBeUndefined()
    })
  })

  describe('查找最近的订单线', () => {
    it('应该找到最近的订单线（包括不可拖拽的）', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      // pixelY = 502，非常接近line2(入场线, pixelY=500)
      const nearestLine = result.current.findNearestOrderLine(502)
      expect(nearestLine).toBeDefined()
      expect(nearestLine!.id).toBe('line2')
    })

    it('距离相近时应优先返回入场线', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      // pixelY = 504，与line1(510)距离6，与line2(500)距离4
      // 由于line2距离<5，直接返回line2(入场线)
      const nearestLine = result.current.findNearestOrderLine(504)
      expect(nearestLine).toBeDefined()
      expect(nearestLine!.type).toBe(PriceLineType.ENTRY)
    })
  })

  describe('拖拽流程', () => {
    it('应该正确开始拖拽', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      const lineToDown = mockLines[0] // 止损线

      act(() => {
        result.current.startDrag(lineToDown)
      })

      expect(result.current.isDragging).toBe(true)
      expect(result.current.draggingLine).toEqual(lineToDown)
    })

    it('应该正确更新拖拽位置', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      const lineToDown = mockLines[0] // 止损线

      act(() => {
        result.current.startDrag(lineToDown)
      })

      // 拖动到新位置 (pixelY = 520 对应价格 24800)
      act(() => {
        result.current.updateDrag(520)
      })

      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('line1', {
        price: expect.any(Number),
        title: expect.stringContaining('止损'),
      })
    })

    it('应该正确结束拖拽并触发回调', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      const lineToDown = mockLines[0] // 止损线

      act(() => {
        result.current.startDrag(lineToDown)
      })

      act(() => {
        result.current.updateDrag(520)
      })

      act(() => {
        result.current.endDrag()
      })

      expect(result.current.isDragging).toBe(false)
      expect(result.current.draggingLine).toBeNull()
      expect(onPriceChange).toHaveBeenCalledWith(
        'line1',
        'order1',
        expect.any(Number),
        PriceLineType.STOP_LOSS
      )
    })

    it('应该正确取消拖拽并恢复原始价格', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      const lineToDown = mockLines[0] // 止损线
      const originalPrice = lineToDown.price

      act(() => {
        result.current.startDrag(lineToDown)
      })

      act(() => {
        result.current.updateDrag(520) // 拖动到新位置
      })

      act(() => {
        result.current.cancelDrag()
      })

      expect(result.current.isDragging).toBe(false)
      expect(result.current.draggingLine).toBeNull()
      expect(onPriceChange).not.toHaveBeenCalled() // 取消时不应触发回调

      // 应该恢复原始价格
      expect(mockPriceLineManager.updateLine).toHaveBeenLastCalledWith('line1', {
        price: originalPrice,
        title: expect.stringContaining('止损'),
      })
    })
  })

  describe('鼠标样式', () => {
    it('拖拽时应返回grabbing', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      expect(result.current.getCursorStyle(false, true)).toBe('grabbing')
    })

    it('靠近线时应返回ns-resize', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      expect(result.current.getCursorStyle(true, false)).toBe('ns-resize')
    })

    it('默认应返回default', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      expect(result.current.getCursorStyle(false, false)).toBe('default')
    })
  })

  describe('边界情况', () => {
    it('无priceLineManager时应安全返回', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: null,
          chart: mockChart,
          onPriceChange,
        })
      )

      expect(result.current.findNearestDraggableLine(500)).toBeUndefined()
      expect(result.current.findNearestOrderLine(500)).toBeUndefined()
    })

    it('无chart时应安全返回', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: null,
          onPriceChange,
        })
      )

      expect(result.current.findNearestDraggableLine(500)).toBeUndefined()
    })

    it('非拖拽状态时updateDrag不应执行', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      act(() => {
        result.current.updateDrag(500)
      })

      expect(mockPriceLineManager.updateLine).not.toHaveBeenCalled()
    })

    it('非拖拽状态时endDrag不应执行', () => {
      const { result } = renderHook(() =>
        useEChartsPriceLineDrag({
          priceLineManager: mockPriceLineManager,
          chart: mockChart,
          onPriceChange,
        })
      )

      act(() => {
        result.current.endDrag()
      })

      expect(onPriceChange).not.toHaveBeenCalled()
    })
  })
})

