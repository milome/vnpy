import { ISeriesApi, SeriesType, Time } from 'lightweight-charts';
import { createSeriesMarkers, ISeriesMarkersPluginApi } from 'lightweight-charts';
import { OrderSide, TradingOrder, OrderMarker } from '../types';

// 颜色配置
const COLORS = {
  BUY: '#ff4757',
  SELL: '#00d9ff',
};

/**
 * 订单标记管理器
 * 负责在图表上显示成交标记
 */
export class OrderMarkerManager {
  private series: ISeriesApi<SeriesType>;
  private markersPlugin: ISeriesMarkersPluginApi<Time> | null = null;
  private markers: OrderMarker[] = [];

  constructor(series: ISeriesApi<SeriesType>) {
    this.series = series;
    this.initMarkersPlugin();
  }

  /**
   * 初始化标记插件
   */
  private initMarkersPlugin(): void {
    try {
      this.markersPlugin = createSeriesMarkers(this.series, []);
    } catch (err) {
      console.error('Failed to create series markers:', err);
    }
  }

  /**
   * 添加成交标记
   */
  addFilledOrderMarker(order: TradingOrder): OrderMarker | null {
    if (!order.filledTime || !order.filledPrice) {
      console.warn('Order is not filled, cannot add marker');
      return null;
    }

    const marker: OrderMarker = {
      id: `marker_${order.id}`,
      orderId: order.id,
      time: order.filledTime,
      price: order.filledPrice,
      side: order.side,
      quantity: order.quantity,
      text: `${order.side === OrderSide.BUY ? '买入' : '卖出'} ${order.quantity}手`,
    };

    this.markers.push(marker);
    this.updateChartMarkers();

    return marker;
  }

  /**
   * 移除订单的标记
   */
  removeOrderMarker(orderId: string): boolean {
    const index = this.markers.findIndex(m => m.orderId === orderId);
    if (index === -1) return false;

    this.markers.splice(index, 1);
    this.updateChartMarkers();
    return true;
  }

  /**
   * 更新图表上的标记
   */
  private updateChartMarkers(): void {
    if (!this.markersPlugin) return;

    const chartMarkers = this.markers.map(marker => ({
      time: Math.floor(marker.time / 1000) as Time,
      position: marker.side === OrderSide.BUY ? 'belowBar' as const : 'aboveBar' as const,
      color: marker.side === OrderSide.BUY ? COLORS.BUY : COLORS.SELL,
      shape: marker.side === OrderSide.BUY ? 'arrowUp' as const : 'arrowDown' as const,
      text: marker.text || '',
      size: 2,
    }));

    this.markersPlugin.setMarkers(chartMarkers);
  }

  /**
   * 获取所有标记
   */
  getAllMarkers(): OrderMarker[] {
    return [...this.markers];
  }

  /**
   * 清除所有标记
   */
  clearAllMarkers(): void {
    this.markers = [];
    if (this.markersPlugin) {
      this.markersPlugin.setMarkers([]);
    }
  }

  /**
   * 更新关联的series
   */
  setSeries(series: ISeriesApi<SeriesType>): void {
    this.series = series;
    // 重新初始化标记插件
    if (this.markersPlugin) {
      this.markersPlugin.detach();
    }
    this.initMarkersPlugin();
    this.updateChartMarkers();
  }

  /**
   * 销毁
   */
  destroy(): void {
    if (this.markersPlugin) {
      this.markersPlugin.detach();
      this.markersPlugin = null;
    }
    this.markers = [];
  }
}

