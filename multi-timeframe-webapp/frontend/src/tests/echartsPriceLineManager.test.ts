import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  EChartsPriceLineManager,
  PRICE_LINE_COLORS,
  findNearestPriceLine,
  findNearestDraggablePriceLine,
} from '../utils/echartsPriceLineManager'
import { PriceLineType, OrderSide, ChartPriceLine } from '../types'

/**
 * ECharts价格线管理器单元测试
 */

describe('EChartsPriceLineManager', () => {
  let manager: EChartsPriceLineManager

  beforeEach(() => {
    manager = new EChartsPriceLineManager()
  })

  describe('基础功能', () => {
    it('应该初始化为空', () => {
      expect(manager.getAllLines()).toHaveLength(0)
    })

    it('应该生成唯一的线条ID', () => {
      const line1 = manager.createEntryLine({
        orderId: 'order1',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })
      const line2 = manager.createEntryLine({
        orderId: 'order2',
        price: 25100,
        side: OrderSide.SELL,
        quantity: 2,
      })
      
      expect(line1.id).not.toBe(line2.id)
      expect(line1.id).toMatch(/^eline_\d+_\d+$/)
    })
  })

  describe('创建入场线', () => {
    it('应该创建买入入场线（红色）', () => {
      const line = manager.createEntryLine({
        orderId: 'order1',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })

      expect(line.type).toBe(PriceLineType.ENTRY)
      expect(line.price).toBe(25000)
      expect(line.color).toBe(PRICE_LINE_COLORS.BUY)
      expect(line.lineStyle).toBe('solid')
      expect(line.lineWidth).toBe(2)
      expect(line.draggable).toBe(false)
      expect(line.title).toContain('买入')
      expect(line.title).toContain('1手')
    })

    it('应该创建卖出入场线（青色）', () => {
      const line = manager.createEntryLine({
        orderId: 'order1',
        price: 25100,
        side: OrderSide.SELL,
        quantity: 2,
      })

      expect(line.color).toBe(PRICE_LINE_COLORS.SELL)
      expect(line.title).toContain('卖出')
      expect(line.title).toContain('2手')
    })
  })

  describe('创建止损线', () => {
    it('应该创建止损线（橙色虚线）', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(line.type).toBe(PriceLineType.STOP_LOSS)
      expect(line.price).toBe(24900)
      expect(line.color).toBe(PRICE_LINE_COLORS.STOP_LOSS)
      expect(line.lineStyle).toBe('dashed')
      expect(line.draggable).toBe(true)
      expect(line.title).toContain('止损')
    })
  })

  describe('创建止盈线', () => {
    it('应该创建止盈线（蓝色虚线）', () => {
      const line = manager.createTakeProfitLine({
        orderId: 'order1',
        price: 25200,
        side: OrderSide.BUY,
      })

      expect(line.type).toBe(PriceLineType.TAKE_PROFIT)
      expect(line.price).toBe(25200)
      expect(line.color).toBe(PRICE_LINE_COLORS.TAKE_PROFIT)
      expect(line.lineStyle).toBe('dashed')
      expect(line.draggable).toBe(true)
      expect(line.title).toContain('止盈')
    })
  })

  describe('创建挂单线', () => {
    it('应该创建买入挂单线（红色点线）', () => {
      const line = manager.createPendingLine({
        orderId: 'order1',
        price: 24800,
        side: OrderSide.BUY,
        quantity: 1,
      })

      expect(line.type).toBe(PriceLineType.PENDING)
      expect(line.color).toBe(PRICE_LINE_COLORS.BUY)
      expect(line.lineStyle).toBe('dotted')
      expect(line.draggable).toBe(true)
      expect(line.title).toContain('挂单')
      expect(line.title).toContain('买入')
    })

    it('应该创建卖出挂单线（青色点线）', () => {
      const line = manager.createPendingLine({
        orderId: 'order1',
        price: 25300,
        side: OrderSide.SELL,
        quantity: 2,
      })

      expect(line.color).toBe(PRICE_LINE_COLORS.SELL)
      expect(line.title).toContain('卖出')
    })
  })

  describe('创建预览线', () => {
    it('应该创建预览线', () => {
      const line = manager.createPreviewLine(25000)

      expect(line.type).toBe(PriceLineType.PREVIEW)
      expect(line.price).toBe(25000)
      expect(line.color).toBe(PRICE_LINE_COLORS.PREVIEW)
      expect(line.lineStyle).toBe('dotted')
      expect(line.draggable).toBe(false)
    })

    it('应该更新已存在的预览线而不是创建新的', () => {
      manager.createPreviewLine(25000)
      manager.createPreviewLine(25100)

      const previewLines = manager.getLinesByType(PriceLineType.PREVIEW)
      expect(previewLines).toHaveLength(1)
      expect(previewLines[0].price).toBe(25100)
    })

    it('应该能移除预览线', () => {
      manager.createPreviewLine(25000)
      expect(manager.getLinesByType(PriceLineType.PREVIEW)).toHaveLength(1)

      const result = manager.removePreviewLine()
      expect(result).toBe(true)
      expect(manager.getLinesByType(PriceLineType.PREVIEW)).toHaveLength(0)
    })
  })

  describe('更新线条', () => {
    it('应该更新线条价格', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const updated = manager.updateLine(line.id, { price: 24800 })
      
      expect(updated).toBeDefined()
      expect(updated!.price).toBe(24800)
      expect(updated!.title).toContain('24800')
    })

    it('应该更新线条颜色', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const updated = manager.updateLine(line.id, { color: '#ff0000' })
      
      expect(updated!.color).toBe('#ff0000')
    })

    it('更新不存在的线条应返回undefined', () => {
      const result = manager.updateLine('nonexistent', { price: 25000 })
      expect(result).toBeUndefined()
    })
  })

  describe('删除线条', () => {
    it('应该删除指定ID的线条', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(manager.getAllLines()).toHaveLength(1)
      
      const result = manager.removeLine(line.id)
      
      expect(result).toBe(true)
      expect(manager.getAllLines()).toHaveLength(0)
    })

    it('删除不存在的线条应返回false', () => {
      const result = manager.removeLine('nonexistent')
      expect(result).toBe(false)
    })

    it('应该按订单ID删除所有相关线条', () => {
      manager.createEntryLine({
        orderId: 'order1',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })
      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })
      manager.createTakeProfitLine({
        orderId: 'order1',
        price: 25200,
        side: OrderSide.BUY,
      })
      manager.createStopLossLine({
        orderId: 'order2',
        price: 24800,
        side: OrderSide.SELL,
      })

      expect(manager.getAllLines()).toHaveLength(4)

      const removedCount = manager.removeLinesByOrderId('order1')

      expect(removedCount).toBe(3)
      expect(manager.getAllLines()).toHaveLength(1)
      expect(manager.getLinesByOrderId('order1')).toHaveLength(0)
      expect(manager.getLinesByOrderId('order2')).toHaveLength(1)
    })
  })

  describe('查询线条', () => {
    beforeEach(() => {
      manager.createEntryLine({
        orderId: 'order1',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })
      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })
      manager.createTakeProfitLine({
        orderId: 'order2',
        price: 25200,
        side: OrderSide.SELL,
      })
    })

    it('应该按ID获取线条', () => {
      const lines = manager.getAllLines()
      const line = manager.getLine(lines[0].id)
      
      expect(line).toBeDefined()
      expect(line!.id).toBe(lines[0].id)
    })

    it('应该按订单ID获取线条', () => {
      const lines = manager.getLinesByOrderId('order1')
      expect(lines).toHaveLength(2)
    })

    it('应该按类型获取线条', () => {
      const entryLines = manager.getLinesByType(PriceLineType.ENTRY)
      const stopLossLines = manager.getLinesByType(PriceLineType.STOP_LOSS)
      const takeProfitLines = manager.getLinesByType(PriceLineType.TAKE_PROFIT)

      expect(entryLines).toHaveLength(1)
      expect(stopLossLines).toHaveLength(1)
      expect(takeProfitLines).toHaveLength(1)
    })

    it('应该获取所有可拖拽线条', () => {
      const draggableLines = manager.getDraggableLines()
      // 止损线和止盈线可拖拽，入场线不可拖拽
      expect(draggableLines).toHaveLength(2)
    })
  })

  describe('变化回调', () => {
    it('应该在创建线条时触发回调', () => {
      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith(expect.arrayContaining([
        expect.objectContaining({ price: 24900 })
      ]))
    })

    it('应该在更新线条时触发回调', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.updateLine(line.id, { price: 24800 })

      expect(callback).toHaveBeenCalledTimes(1)
    })

    it('应该在删除线条时触发回调', () => {
      const line = manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.removeLine(line.id)

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith([])
    })
  })

  describe('ECharts配置生成', () => {
    it('应该生成正确的markLine数据', () => {
      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const markLineData = manager.toEChartsMarkLineData()

      expect(markLineData).toHaveLength(1)
      expect(markLineData[0]).toMatchObject({
        yAxis: 24900,
        lineStyle: {
          color: PRICE_LINE_COLORS.STOP_LOSS,
          width: 1,
          type: 'dashed',
        },
      })
    })

    it('应该生成完整的markLine配置', () => {
      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      const markLineOption = manager.toEChartsMarkLineOption()

      expect(markLineOption).toHaveProperty('silent', false)
      expect(markLineOption).toHaveProperty('symbol', 'none')
      expect(markLineOption).toHaveProperty('animation', false)
      expect(markLineOption.data).toHaveLength(1)
    })
  })

  describe('清除所有线条', () => {
    it('应该清除所有线条', () => {
      manager.createEntryLine({
        orderId: 'order1',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })
      manager.createStopLossLine({
        orderId: 'order1',
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(manager.getAllLines()).toHaveLength(2)

      manager.clearAllLines()

      expect(manager.getAllLines()).toHaveLength(0)
    })
  })
})

describe('辅助函数', () => {
  describe('findNearestPriceLine', () => {
    const mockPriceToPixel = (price: number) => 500 - (price - 25000) * 0.1

    const mockLines: ChartPriceLine[] = [
      {
        id: 'line1',
        type: PriceLineType.STOP_LOSS,
        price: 24900,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      },
      {
        id: 'line2',
        type: PriceLineType.ENTRY,
        price: 25000,
        color: '#ff4757',
        lineWidth: 2,
        lineStyle: 'solid',
        draggable: false,
      },
      {
        id: 'line3',
        type: PriceLineType.TAKE_PROFIT,
        price: 25200,
        color: '#1e90ff',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      },
    ]

    it('应该找到最近的价格线', () => {
      // 25000对应pixelY = 500
      const nearestLine = findNearestPriceLine(mockLines, 500, mockPriceToPixel, 10)
      expect(nearestLine).toBeDefined()
      expect(nearestLine!.id).toBe('line2')
    })

    it('超出阈值时应返回null', () => {
      const nearestLine = findNearestPriceLine(mockLines, 100, mockPriceToPixel, 10)
      expect(nearestLine).toBeNull()
    })

    it('应该返回距离最近的线', () => {
      // 24950对应pixelY = 505
      // 与line1(24900, pixel=510)的距离: 5
      // 与line2(25000, pixel=500)的距离: 5
      // 距离相同时返回先找到的
      const nearestLine = findNearestPriceLine(mockLines, 503, mockPriceToPixel, 10)
      expect(nearestLine).toBeDefined()
      // pixelY=503更接近line2(pixel=500)
      expect(nearestLine!.id).toBe('line2')
    })
  })

  describe('findNearestDraggablePriceLine', () => {
    const mockPriceToPixel = (price: number) => 500 - (price - 25000) * 0.1

    const mockLines: ChartPriceLine[] = [
      {
        id: 'line1',
        type: PriceLineType.STOP_LOSS,
        price: 24900,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      },
      {
        id: 'line2',
        type: PriceLineType.ENTRY,
        price: 25000,
        color: '#ff4757',
        lineWidth: 2,
        lineStyle: 'solid',
        draggable: false, // 入场线不可拖拽
      },
    ]

    it('应该只找可拖拽的价格线', () => {
      // 25000对应pixelY = 500，但入场线不可拖拽
      const nearestLine = findNearestDraggablePriceLine(mockLines, 500, mockPriceToPixel, 10)
      expect(nearestLine).toBeNull() // 因为最近的线不可拖拽
    })

    it('应该找到可拖拽的止损线', () => {
      // 24900对应pixelY = 510
      const nearestLine = findNearestDraggablePriceLine(mockLines, 510, mockPriceToPixel, 10)
      expect(nearestLine).toBeDefined()
      expect(nearestLine!.id).toBe('line1')
    })
  })
})

