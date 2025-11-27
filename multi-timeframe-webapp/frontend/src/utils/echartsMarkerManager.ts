import { OrderSide, TradingOrder, OrderMarker } from '../types'
import type { MarkPointComponentOption } from 'echarts'

/**
 * ECharts 订单标记管理器
 * 负责在ECharts图表上显示成交标记（箭头）
 * 
 * 使用ECharts的markPoint来实现标记功能
 */

// 颜色配置（中国惯例：红涨绿跌）
const MARKER_COLORS = {
  BUY: '#ff4757',   // 红色 - 买入
  SELL: '#00d9ff',  // 青色 - 卖出
}

// 标记变化回调类型
export type OnMarkersChangeCallback = (markers: OrderMarker[]) => void

/**
 * ECharts 订单标记管理器
 */
export class EChartsMarkerManager {
  private markers: OrderMarker[] = []
  private onChangeCallback: OnMarkersChangeCallback | null = null

  constructor() {
    // ECharts版本通过回调通知变化
  }

  /**
   * 设置标记变化回调
   */
  setOnChangeCallback(callback: OnMarkersChangeCallback): void {
    this.onChangeCallback = callback
  }

  /**
   * 通知标记变化
   */
  private notifyChange(): void {
    if (this.onChangeCallback) {
      this.onChangeCallback(this.getAllMarkers())
    }
  }

  /**
   * 添加成交标记
   */
  addFilledOrderMarker(order: TradingOrder): OrderMarker | null {
    if (!order.filledTime || !order.filledPrice) {
      console.warn('Order is not filled, cannot add marker')
      return null
    }

    const marker: OrderMarker = {
      id: `marker_${order.id}`,
      orderId: order.id,
      time: order.filledTime,
      price: order.filledPrice,
      side: order.side,
      quantity: order.quantity,
      text: `${order.side === OrderSide.BUY ? '买入' : '卖出'} ${order.quantity}手`,
    }

    this.markers.push(marker)
    this.notifyChange()

    return marker
  }

  /**
   * 移除订单的标记
   */
  removeOrderMarker(orderId: string): boolean {
    const index = this.markers.findIndex(m => m.orderId === orderId)
    if (index === -1) return false

    this.markers.splice(index, 1)
    this.notifyChange()
    return true
  }

  /**
   * 获取所有标记
   */
  getAllMarkers(): OrderMarker[] {
    return [...this.markers]
  }

  /**
   * 清除所有标记
   */
  clearAllMarkers(): void {
    this.markers = []
    this.notifyChange()
  }

  /**
   * 将标记转换为ECharts markPoint数据
   */
  toEChartsMarkPointData(): MarkPointComponentOption['data'] {
    return this.markers.map(marker => ({
      name: marker.id,
      coord: [marker.time, marker.price],
      value: marker.text || '',
      symbol: marker.side === OrderSide.BUY ? 'arrow' : 'arrow',
      symbolRotate: marker.side === OrderSide.BUY ? 0 : 180, // 买入向上，卖出向下
      symbolSize: 16,
      itemStyle: {
        color: marker.side === OrderSide.BUY ? MARKER_COLORS.BUY : MARKER_COLORS.SELL,
      },
      label: {
        show: true,
        formatter: marker.text || '',
        position: marker.side === OrderSide.BUY ? 'bottom' : 'top',
        color: marker.side === OrderSide.BUY ? MARKER_COLORS.BUY : MARKER_COLORS.SELL,
        fontSize: 10,
        backgroundColor: 'rgba(30, 30, 30, 0.9)',
        padding: [2, 4],
        borderRadius: 2,
      },
    }))
  }

  /**
   * 生成完整的ECharts markPoint配置
   */
  toEChartsMarkPointOption(): MarkPointComponentOption {
    return {
      silent: true, // 标记不需要交互
      animation: true,
      data: this.toEChartsMarkPointData(),
    }
  }

  /**
   * 销毁
   */
  destroy(): void {
    this.markers = []
    this.onChangeCallback = null
  }
}

