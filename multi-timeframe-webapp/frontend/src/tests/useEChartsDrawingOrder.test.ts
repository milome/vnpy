import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEChartsDrawingOrder } from '../hooks/useEChartsDrawingOrder'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { OrderService } from '../services/orderService'
import { DrawingMode, OrderSide, PriceLineType } from '../types'

/**
 * ECharts画线下单Hook单元测试
 */

describe('useEChartsDrawingOrder', () => {
  let mockPriceLineManager: EChartsPriceLineManager
  let orderService: OrderService

  beforeEach(() => {
    // 创建mock的价格线管理器
    mockPriceLineManager = {
      createPreviewLine: vi.fn(),
      removePreviewLine: vi.fn(),
      createPendingLine: vi.fn().mockReturnValue({ id: 'pending-1', type: PriceLineType.PENDING }),
      createStopLossLine: vi.fn().mockReturnValue({ id: 'sl-1', type: PriceLineType.STOP_LOSS }),
      createTakeProfitLine: vi.fn().mockReturnValue({ id: 'tp-1', type: PriceLineType.TAKE_PROFIT }),
      removeLinesByOrderId: vi.fn(),
      getAllLines: vi.fn().mockReturnValue([]),
    } as unknown as EChartsPriceLineManager

    orderService = new OrderService()
  })

  describe('初始状态', () => {
    it('应该初始化为非画线模式', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      expect(result.current.drawingMode).toBe(DrawingMode.NONE)
      expect(result.current.isDrawing).toBe(false)
      expect(result.current.previewPrice).toBeNull()
      expect(result.current.isOrderDialogOpen).toBe(false)
      expect(result.current.pendingOrderPrice).toBeNull()
    })
  })

  describe('画线模式控制', () => {
    it('应该启用画线模式', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      expect(result.current.drawingMode).toBe(DrawingMode.PENDING)
      expect(result.current.isDrawing).toBe(true)
    })

    it('应该禁用画线模式并移除预览线', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      act(() => {
        result.current.disableDrawingMode()
      })

      expect(result.current.drawingMode).toBe(DrawingMode.NONE)
      expect(result.current.isDrawing).toBe(false)
      expect(mockPriceLineManager.removePreviewLine).toHaveBeenCalled()
    })
  })

  describe('十字光标移动', () => {
    it('画线模式下移动十字光标应更新预览价格', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      act(() => {
        result.current.handleCrosshairMove(25000)
      })

      expect(result.current.previewPrice).toBe(25000)
      expect(mockPriceLineManager.createPreviewLine).toHaveBeenCalledWith(25000)
    })

    it('非画线模式下移动十字光标不应更新预览价格', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.handleCrosshairMove(25000)
      })

      expect(result.current.previewPrice).toBeNull()
      expect(mockPriceLineManager.createPreviewLine).not.toHaveBeenCalled()
    })

    it('价格为null时不应更新预览价格', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      act(() => {
        result.current.handleCrosshairMove(null)
      })

      expect(result.current.previewPrice).toBeNull()
    })
  })

  describe('点击下单', () => {
    it('画线模式下点击应打开下单对话框', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      act(() => {
        result.current.handleCrosshairMove(25000)
      })

      act(() => {
        result.current.handleClick()
      })

      expect(result.current.isOrderDialogOpen).toBe(true)
      expect(result.current.pendingOrderPrice).toBe(25000)
    })

    it('非画线模式下点击不应打开下单对话框', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.handleClick()
      })

      expect(result.current.isOrderDialogOpen).toBe(false)
    })
  })

  describe('ESC键处理', () => {
    it('对话框打开时ESC应关闭对话框', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      // 打开对话框
      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })

      expect(result.current.isOrderDialogOpen).toBe(true)

      // 按ESC
      act(() => {
        result.current.handleEscape()
      })

      expect(result.current.isOrderDialogOpen).toBe(false)
      expect(result.current.drawingMode).toBe(DrawingMode.PENDING) // 仍在画线模式
    })

    it('画线模式下ESC应退出画线模式', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })

      act(() => {
        result.current.handleEscape()
      })

      expect(result.current.drawingMode).toBe(DrawingMode.NONE)
      expect(result.current.isDrawing).toBe(false)
    })
  })

  describe('确认下单', () => {
    it('应该创建订单和价格线', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      // 打开对话框
      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })

      // 确认下单
      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 2,
          stopLoss: 24900,
          takeProfit: 25200,
        })
      })

      // 验证价格线创建
      expect(mockPriceLineManager.createPendingLine).toHaveBeenCalledWith({
        orderId: expect.any(String),
        price: 25000,
        side: OrderSide.BUY,
        quantity: 2,
      })

      expect(mockPriceLineManager.createStopLossLine).toHaveBeenCalledWith({
        orderId: expect.any(String),
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(mockPriceLineManager.createTakeProfitLine).toHaveBeenCalledWith({
        orderId: expect.any(String),
        price: 25200,
        side: OrderSide.BUY,
      })

      // 验证状态重置
      expect(result.current.isOrderDialogOpen).toBe(false)
      expect(result.current.drawingMode).toBe(DrawingMode.NONE)
    })

    it('没有止损止盈时不应创建对应价格线', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      // 打开对话框
      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })

      // 确认下单（不设置止损止盈）
      act(() => {
        result.current.confirmOrder({
          side: OrderSide.SELL,
          quantity: 1,
        })
      })

      expect(mockPriceLineManager.createPendingLine).toHaveBeenCalled()
      expect(mockPriceLineManager.createStopLossLine).not.toHaveBeenCalled()
      expect(mockPriceLineManager.createTakeProfitLine).not.toHaveBeenCalled()
    })
  })

  describe('关闭对话框', () => {
    it('应该关闭下单对话框', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      // 打开对话框
      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })

      expect(result.current.isOrderDialogOpen).toBe(true)

      act(() => {
        result.current.closeOrderDialog()
      })

      expect(result.current.isOrderDialogOpen).toBe(false)
      expect(result.current.pendingOrderPrice).toBeNull()
    })
  })

  describe('取消挂单', () => {
    it('应该取消订单并移除价格线', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: mockPriceLineManager,
          orderService,
        })
      )

      // 先创建一个订单
      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })
      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 1,
        })
      })

      // 获取订单ID
      const orders = orderService.getPendingOrders()
      expect(orders.length).toBeGreaterThan(0)
      const orderId = orders[0].id

      // 取消订单
      act(() => {
        result.current.cancelPendingOrder(orderId)
      })

      expect(mockPriceLineManager.removeLinesByOrderId).toHaveBeenCalledWith(orderId)
    })
  })

  describe('无价格线管理器时', () => {
    it('应该正常工作但不调用价格线方法', () => {
      const { result } = renderHook(() =>
        useEChartsDrawingOrder({
          priceLineManager: null,
          orderService,
        })
      )

      act(() => {
        result.current.enableDrawingMode(DrawingMode.PENDING)
      })
      act(() => {
        result.current.handleCrosshairMove(25000)
      })
      act(() => {
        result.current.handleClick()
      })
      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 1,
        })
      })

      // 应该没有错误，订单应该被创建
      const orders = orderService.getPendingOrders()
      expect(orders.length).toBeGreaterThan(0)
    })
  })
})

