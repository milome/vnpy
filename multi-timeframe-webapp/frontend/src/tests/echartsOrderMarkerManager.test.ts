import { describe, it, expect, vi, beforeEach } from 'vitest'
import { EChartsOrderMarkerManager } from '../utils/echartsOrderMarkerManager'
import { OrderSide, OrderStatus, TradingOrder } from '../types'

/**
 * ECharts订单标记管理器单元测试
 */

describe('EChartsOrderMarkerManager', () => {
  let manager: EChartsOrderMarkerManager

  // 模拟已成交订单
  const createFilledOrder = (overrides: Partial<TradingOrder> = {}): TradingOrder => ({
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

  beforeEach(() => {
    manager = new EChartsOrderMarkerManager()
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

      expect(marker).not.toBeNull()
      expect(marker!.side).toBe(OrderSide.BUY)
      expect(marker!.price).toBe(25000)
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

      expect(marker).not.toBeNull()
      expect(marker!.side).toBe(OrderSide.SELL)
      expect(marker!.text).toContain('卖出')
      expect(marker!.text).toContain('3手')
    })

    it('未成交订单不应添加标记', () => {
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

  describe('删除标记', () => {
    it('应该删除指定订单的标记', () => {
      const order = createFilledOrder({ id: 'order1' })
      manager.addFilledOrderMarker(order)

      expect(manager.getAllMarkers()).toHaveLength(1)

      const result = manager.removeOrderMarker('order1')

      expect(result).toBe(true)
      expect(manager.getAllMarkers()).toHaveLength(0)
    })

    it('删除不存在的标记应返回false', () => {
      const result = manager.removeOrderMarker('nonexistent')
      expect(result).toBe(false)
    })
  })

  describe('查询标记', () => {
    it('应该获取指定订单的标记', () => {
      const order = createFilledOrder({ id: 'order1', filledPrice: 25000 })
      manager.addFilledOrderMarker(order)

      const marker = manager.getOrderMarker('order1')

      expect(marker).toBeDefined()
      expect(marker!.price).toBe(25000)
    })

    it('查询不存在的标记应返回undefined', () => {
      const marker = manager.getOrderMarker('nonexistent')
      expect(marker).toBeUndefined()
    })

    it('应该获取所有标记', () => {
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order1' }))
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order2' }))
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order3' }))

      const markers = manager.getAllMarkers()

      expect(markers).toHaveLength(3)
    })
  })

  describe('清除标记', () => {
    it('应该清除所有标记', () => {
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order1' }))
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order2' }))

      expect(manager.getAllMarkers()).toHaveLength(2)

      manager.clearAllMarkers()

      expect(manager.getAllMarkers()).toHaveLength(0)
    })
  })

  describe('变化回调', () => {
    it('应该在添加标记时触发回调', () => {
      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.addFilledOrderMarker(createFilledOrder())

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith(expect.arrayContaining([
        expect.objectContaining({ orderId: 'order1' })
      ]))
    })

    it('应该在删除标记时触发回调', () => {
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order1' }))

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.removeOrderMarker('order1')

      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith([])
    })

    it('应该在清除所有标记时触发回调', () => {
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order1' }))

      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.clearAllMarkers()

      expect(callback).toHaveBeenCalledTimes(1)
    })
  })

  describe('ECharts配置生成', () => {
    it('应该生成正确的markPoint数据', () => {
      const filledTime = Date.now()
      const order = createFilledOrder({
        id: 'order1',
        side: OrderSide.BUY,
        filledPrice: 25000,
        filledTime,
        quantity: 2,
      })
      manager.addFilledOrderMarker(order)

      const markPointData = manager.toEChartsMarkPointData()

      expect(markPointData).toHaveLength(1)
      expect(markPointData[0]).toMatchObject({
        coord: [filledTime, 25000],
        symbolRotate: 0, // 买入向上
      })
      expect(markPointData[0].itemStyle).toMatchObject({
        color: '#ff4757', // 买入红色
      })
    })

    it('卖出标记应该向下', () => {
      const order = createFilledOrder({
        side: OrderSide.SELL,
        filledPrice: 25100,
      })
      manager.addFilledOrderMarker(order)

      const markPointData = manager.toEChartsMarkPointData()

      expect(markPointData[0]).toMatchObject({
        symbolRotate: 180, // 卖出向下
      })
      expect(markPointData[0].itemStyle).toMatchObject({
        color: '#00d9ff', // 卖出青色
      })
    })

    it('应该生成完整的markPoint配置', () => {
      manager.addFilledOrderMarker(createFilledOrder())

      const markPointOption = manager.toEChartsMarkPointOption()

      expect(markPointOption).toHaveProperty('silent', true)
      expect(markPointOption).toHaveProperty('animation', true)
      expect(markPointOption.data).toHaveLength(1)
    })
  })

  describe('销毁', () => {
    it('应该清理所有数据', () => {
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order1' }))
      const callback = vi.fn()
      manager.setOnChangeCallback(callback)

      manager.destroy()

      expect(manager.getAllMarkers()).toHaveLength(0)
      
      // 销毁后回调不应被调用
      manager.addFilledOrderMarker(createFilledOrder({ id: 'order2' }))
      expect(callback).not.toHaveBeenCalled()
    })
  })
})

