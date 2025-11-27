import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EChartsMarkerManager } from '../utils/echartsMarkerManager'
import { OrderSide, OrderStatus, TradingOrder } from '../types'

/**
 * ECharts订单标记管理器单元测试
 */

describe('EChartsMarkerManager', () => {
  let manager: EChartsMarkerManager

  beforeEach(() => {
    manager = new EChartsMarkerManager()
  })

  // 创建模拟已成交订单
  const createFilledOrder = (overrides?: Partial<TradingOrder>): TradingOrder => ({
    id: 'order1',
    side: OrderSide.BUY,
    price: 25000,
    quantity: 1,
    status: OrderStatus.FILLED,
    filledPrice: 25000,
    filledTime: Date.now(),
    createdTime: Date.now() - 1000,
    ...overrides,
  })

  describe('基础功能', () => {
    it('应该初始化为空', () => {
      expect(manager.getAllMarkers()).toHaveLength(0)
    })
  })

  describe('添加成交标记', () => {
    it('应该添加买入成交标记', () => {
      const order = createFilledOrder({
        side: OrderSide.BUY,
        filledPrice: 25000,
        quantity: 2,
      })

      const marker = manager.addFilledOrderMarker(order)

      expect(marker).toBeDefined()
      expect(marker!.orderId).toBe(order.id)
      expect(marker!.price).toBe(25000)
      expect(marker!.side).toBe(OrderSide.BUY)
      expect(marker!.quantity).toBe(2)
      expect(marker!.text).toContain('买入')
      expect(marker!.text).toContain('2手')
    })

    it('应该添加卖出成交标记', () => {
      const order = createFilledOrder({
        side: OrderSide.SELL,
        filledPrice: 25100,
        quantity: 3,
      })

      const marker = manager.addFilledOrderMarker(order)

      expect(marker).toBeDefined()
      expect(marker!.side).toBe(OrderSide.SELL)
      expect(marker!.text).toContain('卖出')
      expect(marker!.text).toContain('3手')
    })

    it('未成交订单应返回null', () => {
      const order: TradingOrder = {
        id: 'order1',
        side: OrderSide.BUY,
        price: 25000,
        quantity: 1,
        status: OrderStatus.PENDING,
        createdTime: Date.now(),
        // 没有 filledPrice 和 filledTime
      }

      const marker = manager.addFilledOrderMarker(order)

      expect(marker).toBeNull()
      expect(manager.getAllMarkers()).toHaveLength(0)
    })

    it('应该生成唯一的标记ID', () => {
      const order1 = createFilledOrder({ id: 'order1' })
      const order2 = createFilledOrder({ id: 'order2' })

      const marker1 = manager.addFilledOrderMarker(order1)
      const marker2 = manager.addFilledOrderMarker(order2)

      expect(marker1!.id).not.toBe(marker2!.id)
    })
  })

  describe('移除标记', () => {
    it('应该移除指定订单的标记', () => {
      const order = createFilledOrder({ id: 'order1' })
      manager.addFilledOrderMarker(order)

      expect(manager.getAllMarkers()).toHaveLength(1)

      const result = manager.removeOrderMarker('order1')

      expect(result).toBe(true)
      expect(manager.getAllMarkers()).toHaveLength(0)
    })

    it('移除不存在的标记应返回false', () => {
      const result = manager.removeOrderMarker('nonexistent')
      expect(result).toBe(false)
    })
  })

  describe('清除所有标记', () => {
    it('应该清除所有标记', () => {
      const order1 = createFilledOrder({ id: 'order1' })
      const order2 = createFilledOrder({ id: 'order2' })

      manager.addFilledOrderMarker(order1)
      manager.addFilledOrderMarker(order2)

      expect(manager.getAllMarkers()).toHaveLength(2)

      manager.clearAllMarkers()

      expect(manager.getAllMarkers()).toHaveLength(0)
    })
  })

  describe('变化回调', () => {
    it('应该在添加标记时触发回调', () => {
      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      const order = createFilledOrder()
      manager.addFilledOrderMarker(order)

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith(expect.arrayContaining([
        expect.objectContaining({ orderId: order.id })
      ]))
    })

    it('应该在移除标记时触发回调', () => {
      const order = createFilledOrder({ id: 'order1' })
      manager.addFilledOrderMarker(order)

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.removeOrderMarker('order1')

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith([])
    })

    it('应该在清除所有标记时触发回调', () => {
      const order = createFilledOrder()
      manager.addFilledOrderMarker(order)

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.clearAllMarkers()

      expect(callback).toHaveBeenCalledTimes(1)
    })
  })

  describe('ECharts配置生成', () => {
    it('应该生成正确的markPoint数据', () => {
      const order = createFilledOrder({
        side: OrderSide.BUY,
        filledPrice: 25000,
        filledTime: 1700000000000,
      })
      manager.addFilledOrderMarker(order)

      const markPointData = manager.toEChartsMarkPointData()

      expect(markPointData).toHaveLength(1)
      expect(markPointData[0]).toMatchObject({
        coord: [1700000000000, 25000],
        symbolRotate: 0, // 买入向上
      })
      expect(markPointData[0].itemStyle).toMatchObject({
        color: '#ff4757', // 红色
      })
    })

    it('应该为卖出标记旋转箭头', () => {
      const order = createFilledOrder({
        side: OrderSide.SELL,
        filledPrice: 25100,
      })
      manager.addFilledOrderMarker(order)

      const markPointData = manager.toEChartsMarkPointData()

      expect(markPointData[0].symbolRotate).toBe(180) // 卖出向下
      expect(markPointData[0].itemStyle).toMatchObject({
        color: '#00d9ff', // 青色
      })
    })

    it('应该生成完整的markPoint配置', () => {
      const order = createFilledOrder()
      manager.addFilledOrderMarker(order)

      const markPointOption = manager.toEChartsMarkPointOption()

      expect(markPointOption).toHaveProperty('silent', true)
      expect(markPointOption).toHaveProperty('animation', true)
      expect(markPointOption.data).toHaveLength(1)
    })

    it('空标记应生成空数据', () => {
      const markPointOption = manager.toEChartsMarkPointOption()

      expect(markPointOption.data).toHaveLength(0)
    })
  })

  describe('销毁', () => {
    it('应该清除所有状态', () => {
      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      const order = createFilledOrder()
      manager.addFilledOrderMarker(order)

      manager.destroy()

      expect(manager.getAllMarkers()).toHaveLength(0)
      
      // 销毁后添加标记不应触发回调
      const order2 = createFilledOrder({ id: 'order2' })
      manager.addFilledOrderMarker(order2)
      // 回调只被之前的addFilledOrderMarker调用过一次
      expect(callback).toHaveBeenCalledTimes(1)
    })
  })
})

