import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EChartsPriceLineManager } from '../utils/echartsPriceLineManager'
import { EChartsOrderMarkerManager } from '../utils/echartsOrderMarkerManager'
import { OrderService } from '../services/orderService'
import { PriceLineType, OrderSide, OrderStatus, DrawingMode } from '../types'

/**
 * ECharts交易功能集成测试
 * 验证各组件协同工作
 */

describe('E10: ECharts交易功能集成测试', () => {
  let priceLineManager: EChartsPriceLineManager
  let markerManager: EChartsOrderMarkerManager
  let orderService: OrderService

  beforeEach(() => {
    priceLineManager = new EChartsPriceLineManager()
    markerManager = new EChartsOrderMarkerManager()
    orderService = new OrderService()
  })

  describe('完整交易流程', () => {
    it('画线下单 -> 成交 -> 显示成本线和标记', () => {
      // 1. 创建挂单
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 25000,
        quantity: 2,
        stopLoss: 24900,
      })

      expect(order.status).toBe(OrderStatus.PENDING)

      // 2. 创建挂单线
      const pendingLine = priceLineManager.createPendingLine({
        orderId: order.id,
        price: 25000,
        side: OrderSide.BUY,
        quantity: 2,
      })

      expect(pendingLine.type).toBe(PriceLineType.PENDING)

      // 3. 创建止损线
      const stopLossLine = priceLineManager.createStopLossLine({
        orderId: order.id,
        price: 24900,
        side: OrderSide.BUY,
      })

      expect(stopLossLine.type).toBe(PriceLineType.STOP_LOSS)

      // 4. 成交订单
      orderService.fillOrder(order.id, 25000)
      const filledOrder = orderService.getOrder(order.id)

      expect(filledOrder?.status).toBe(OrderStatus.FILLED)
      expect(filledOrder?.filledPrice).toBe(25000)

      // 5. 移除挂单线，创建入场线
      priceLineManager.removeLine(pendingLine.id)
      const entryLine = priceLineManager.createEntryLine({
        orderId: order.id,
        price: 25000,
        side: OrderSide.BUY,
        quantity: 2,
      })

      expect(entryLine.type).toBe(PriceLineType.ENTRY)

      // 6. 添加成交标记
      const marker = markerManager.addFilledOrderMarker(filledOrder!)

      expect(marker).not.toBeNull()
      expect(marker!.side).toBe(OrderSide.BUY)
      expect(marker!.price).toBe(25000)

      // 验证最终状态
      const orderLines = priceLineManager.getLinesByOrderId(order.id)
      expect(orderLines).toHaveLength(2) // 入场线 + 止损线
      expect(orderLines.find(l => l.type === PriceLineType.ENTRY)).toBeDefined()
      expect(orderLines.find(l => l.type === PriceLineType.STOP_LOSS)).toBeDefined()

      const markers = markerManager.getAllMarkers()
      expect(markers).toHaveLength(1)
    })

    it('撤单流程', () => {
      // 1. 创建挂单
      const order = orderService.createOrder({
        side: OrderSide.SELL,
        price: 25100,
        quantity: 1,
      })

      // 2. 创建价格线
      priceLineManager.createPendingLine({
        orderId: order.id,
        price: 25100,
        side: OrderSide.SELL,
        quantity: 1,
      })

      expect(priceLineManager.getAllLines()).toHaveLength(1)

      // 3. 撤单
      orderService.cancelOrder(order.id)
      const cancelledOrder = orderService.getOrder(order.id)

      expect(cancelledOrder?.status).toBe(OrderStatus.CANCELLED)

      // 4. 移除价格线
      const removedCount = priceLineManager.removeLinesByOrderId(order.id)

      expect(removedCount).toBe(1)
      expect(priceLineManager.getAllLines()).toHaveLength(0)
    })

    it('修改止损价格', () => {
      // 1. 创建已成交订单
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 25000,
        quantity: 1,
        stopLoss: 24900,
      })
      orderService.fillOrder(order.id, 25000)

      // 2. 创建入场线和止损线
      priceLineManager.createEntryLine({
        orderId: order.id,
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })

      const stopLossLine = priceLineManager.createStopLossLine({
        orderId: order.id,
        price: 24900,
        side: OrderSide.BUY,
      })

      // 3. 修改止损价格
      const newStopLossPrice = 24950
      priceLineManager.updateLine(stopLossLine.id, {
        price: newStopLossPrice,
        title: `止损 @ ${newStopLossPrice}`,
      })

      orderService.updateOrder({
        id: order.id,
        stopLoss: newStopLossPrice,
      })

      // 验证
      const updatedLine = priceLineManager.getLine(stopLossLine.id)
      expect(updatedLine?.price).toBe(24950)

      const updatedOrder = orderService.getOrder(order.id)
      expect(updatedOrder?.stopLoss).toBe(24950)
    })
  })

  describe('价格线管理器与订单服务协同', () => {
    it('订单和价格线ID关联正确', () => {
      const order1 = orderService.createOrder({
        side: OrderSide.BUY,
        price: 25000,
        quantity: 1,
      })

      const order2 = orderService.createOrder({
        side: OrderSide.SELL,
        price: 25100,
        quantity: 1,
      })

      // 为每个订单创建价格线
      priceLineManager.createPendingLine({
        orderId: order1.id,
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })

      priceLineManager.createStopLossLine({
        orderId: order1.id,
        price: 24900,
        side: OrderSide.BUY,
      })

      priceLineManager.createPendingLine({
        orderId: order2.id,
        price: 25100,
        side: OrderSide.SELL,
        quantity: 1,
      })

      // 验证按订单ID获取
      const order1Lines = priceLineManager.getLinesByOrderId(order1.id)
      expect(order1Lines).toHaveLength(2)

      const order2Lines = priceLineManager.getLinesByOrderId(order2.id)
      expect(order2Lines).toHaveLength(1)

      // 移除订单1的所有线
      priceLineManager.removeLinesByOrderId(order1.id)

      expect(priceLineManager.getLinesByOrderId(order1.id)).toHaveLength(0)
      expect(priceLineManager.getLinesByOrderId(order2.id)).toHaveLength(1)
    })
  })

  describe('订单标记管理器', () => {
    it('多个成交订单标记管理', () => {
      // 创建多个订单并成交
      const orders = [
        { side: OrderSide.BUY, price: 25000, quantity: 1 },
        { side: OrderSide.SELL, price: 25100, quantity: 2 },
        { side: OrderSide.BUY, price: 24900, quantity: 1 },
      ]

      orders.forEach((orderParams, index) => {
        const order = orderService.createOrder(orderParams)
        orderService.fillOrder(order.id, orderParams.price)

        const filledOrder = orderService.getOrder(order.id)
        markerManager.addFilledOrderMarker(filledOrder!)
      })

      expect(markerManager.getAllMarkers()).toHaveLength(3)

      // 转换为ECharts配置
      const markPointOption = markerManager.toEChartsMarkPointOption()
      expect(markPointOption.data).toHaveLength(3)
    })
  })

  describe('预览线功能', () => {
    it('预览线创建和更新', () => {
      // 创建预览线
      const preview1 = priceLineManager.createPreviewLine(25000)
      expect(preview1.type).toBe(PriceLineType.PREVIEW)
      expect(preview1.price).toBe(25000)

      // 更新预览线（应该复用同一条线）
      const preview2 = priceLineManager.createPreviewLine(25050)
      expect(preview2.id).toBe(preview1.id) // 同一条线
      expect(preview2.price).toBe(25050)

      // 只有一条预览线
      const previewLines = priceLineManager.getLinesByType(PriceLineType.PREVIEW)
      expect(previewLines).toHaveLength(1)

      // 移除预览线
      priceLineManager.removePreviewLine()
      expect(priceLineManager.getLinesByType(PriceLineType.PREVIEW)).toHaveLength(0)
    })
  })

  describe('订单服务功能', () => {
    it('订单CRUD操作', () => {
      // 创建订单
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 25000,
        quantity: 1,
      })
      expect(order.id).toBeDefined()
      expect(order.status).toBe(OrderStatus.PENDING)

      // 获取订单
      const fetchedOrder = orderService.getOrder(order.id)
      expect(fetchedOrder).toEqual(order)

      // 成交订单
      orderService.fillOrder(order.id, 25000)
      const filledOrder = orderService.getOrder(order.id)
      expect(filledOrder?.status).toBe(OrderStatus.FILLED)

      // 获取已成交订单列表
      const filledOrders = orderService.getFilledOrders()
      expect(filledOrders.length).toBeGreaterThan(0)
    })

    it('撤单操作', () => {
      const order = orderService.createOrder({
        side: OrderSide.SELL,
        price: 25100,
        quantity: 1,
      })

      orderService.cancelOrder(order.id)
      const cancelledOrder = orderService.getOrder(order.id)
      expect(cancelledOrder?.status).toBe(OrderStatus.CANCELLED)
    })
  })

  describe('ECharts配置生成', () => {
    it('价格线转换为markLine配置', () => {
      priceLineManager.createPendingLine({
        orderId: 'test-order',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })

      priceLineManager.createStopLossLine({
        orderId: 'test-order',
        price: 24900,
        side: OrderSide.BUY,
      })

      const markLineOption = priceLineManager.toEChartsMarkLineOption()

      expect(markLineOption.data).toHaveLength(2)
      expect(markLineOption.silent).toBe(false)
    })

    it('订单标记转换为markPoint配置', () => {
      const order = orderService.createOrder({
        side: OrderSide.BUY,
        price: 25000,
        quantity: 1,
      })
      orderService.fillOrder(order.id, 25000)

      const filledOrder = orderService.getOrder(order.id)
      markerManager.addFilledOrderMarker(filledOrder!)

      const markPointOption = markerManager.toEChartsMarkPointOption()

      expect(markPointOption.data).toHaveLength(1)
      expect(markPointOption.silent).toBe(true)
      expect(markPointOption.animation).toBe(true)
    })
  })

  describe('边界情况', () => {
    it('空数据处理', () => {
      expect(priceLineManager.getAllLines()).toHaveLength(0)
      expect(priceLineManager.toEChartsMarkLineOption().data).toHaveLength(0)

      expect(markerManager.getAllMarkers()).toHaveLength(0)
      expect(markerManager.toEChartsMarkPointOption().data).toHaveLength(0)
    })

    it('无效订单ID处理', () => {
      const result = priceLineManager.removeLinesByOrderId('non-existent-id')
      expect(result).toBe(0)

      const lines = priceLineManager.getLinesByOrderId('non-existent-id')
      expect(lines).toHaveLength(0)
    })

    it('重复移除处理', () => {
      const line = priceLineManager.createPendingLine({
        orderId: 'test',
        price: 25000,
        side: OrderSide.BUY,
        quantity: 1,
      })

      const result1 = priceLineManager.removeLine(line.id)
      expect(result1).toBe(true)

      const result2 = priceLineManager.removeLine(line.id)
      expect(result2).toBe(false) // 已经移除了
    })
  })
})

