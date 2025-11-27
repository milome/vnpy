import { ChartPriceLine, PriceLineType, OrderSide } from '../types'
import type { MarkLineComponentOption } from 'echarts'

/**
 * ECharts 价格线管理器
 * 负责在ECharts图表上创建和管理各种价格线（入场、止损、止盈等）
 * 
 * 与TradingView版本的主要区别：
 * - TradingView使用series.createPriceLine()直接操作图表
 * - ECharts需要通过markLine配置来绑制价格线
 * - ECharts需要在线条变化时通知组件更新图表配置
 */

// 颜色配置（中国惯例：红涨绿跌）
export const PRICE_LINE_COLORS = {
  BUY: '#ff4757',        // 红色 - 买入
  SELL: '#00d9ff',       // 青色 - 卖出
  STOP_LOSS: '#ffa502',  // 橙色 - 止损
  TAKE_PROFIT: '#1e90ff', // 蓝色 - 止盈
  PREVIEW: '#ffffff80',  // 半透明白色 - 预览
  SHADOW: '#ffa50280',   // 半透明橙色 - 影子止损线
}

// 线条样式映射
const LINE_STYLE_MAP: Record<'solid' | 'dashed' | 'dotted', string> = {
  solid: 'solid',
  dashed: 'dashed',
  dotted: 'dotted',
}

// 创建入场线选项
export interface CreateEntryLineOptions {
  orderId: string
  price: number
  side: OrderSide
  quantity: number
}

// 创建止损线选项
export interface CreateStopLossLineOptions {
  orderId: string
  price: number
  side: OrderSide
}

// 创建止盈线选项
export interface CreateTakeProfitLineOptions {
  orderId: string
  price: number
  side: OrderSide
}

// 创建挂单线选项
export interface CreatePendingLineOptions {
  orderId: string
  price: number
  side: OrderSide
  quantity: number
}

// 线条变化回调类型
export type OnLinesChangeCallback = (lines: ChartPriceLine[]) => void

/**
 * ECharts 价格线管理器
 */
export class EChartsPriceLineManager {
  private lines: Map<string, ChartPriceLine> = new Map()
  private lineIdCounter = 0
  private onChangeCallback: OnLinesChangeCallback | null = null

  constructor() {
    // ECharts版本不需要series引用，通过回调通知变化
  }

  /**
   * 设置线条变化回调
   * 当线条增删改时会调用此回调，组件可以据此更新图表配置
   */
  setOnChangeCallback(callback: OnLinesChangeCallback): void {
    this.onChangeCallback = callback
  }

  /**
   * 通知线条变化
   */
  private notifyChange(): void {
    if (this.onChangeCallback) {
      this.onChangeCallback(this.getAllLines())
    }
  }

  /**
   * 生成唯一线条ID
   */
  private generateLineId(): string {
    this.lineIdCounter++
    return `eline_${Date.now()}_${this.lineIdCounter}`
  }

  /**
   * 创建价格线（内部方法）
   */
  private createLine(config: ChartPriceLine): ChartPriceLine {
    this.lines.set(config.id, config)
    this.notifyChange()
    return config
  }

  /**
   * 创建通用价格线（公共方法）
   * 用于创建自定义配置的价格线，如影子止损线
   */
  createPriceLine(config: ChartPriceLine): ChartPriceLine {
    return this.createLine(config)
  }

  /**
   * 创建入场价格线
   */
  createEntryLine(options: CreateEntryLineOptions): ChartPriceLine {
    const color = options.side === OrderSide.BUY ? PRICE_LINE_COLORS.BUY : PRICE_LINE_COLORS.SELL
    const sideText = options.side === OrderSide.BUY ? '买入' : '卖出'
    
    const config: ChartPriceLine = {
      id: this.generateLineId(),
      orderId: options.orderId,
      type: PriceLineType.ENTRY,
      price: options.price,
      color,
      lineWidth: 2,
      lineStyle: 'solid',
      title: `${sideText} ${options.quantity}手 @ ${options.price}`,
      draggable: false,
    }

    return this.createLine(config)
  }

  /**
   * 创建止损线
   */
  createStopLossLine(options: CreateStopLossLineOptions): ChartPriceLine {
    const config: ChartPriceLine = {
      id: this.generateLineId(),
      orderId: options.orderId,
      type: PriceLineType.STOP_LOSS,
      price: options.price,
      color: PRICE_LINE_COLORS.STOP_LOSS,
      lineWidth: 1,
      lineStyle: 'dashed',
      title: `止损 @ ${options.price}`,
      draggable: true,
    }

    return this.createLine(config)
  }

  /**
   * 创建止盈线
   */
  createTakeProfitLine(options: CreateTakeProfitLineOptions): ChartPriceLine {
    const config: ChartPriceLine = {
      id: this.generateLineId(),
      orderId: options.orderId,
      type: PriceLineType.TAKE_PROFIT,
      price: options.price,
      color: PRICE_LINE_COLORS.TAKE_PROFIT,
      lineWidth: 1,
      lineStyle: 'dashed',
      title: `止盈 @ ${options.price}`,
      draggable: true,
    }

    return this.createLine(config)
  }

  /**
   * 创建挂单线
   */
  createPendingLine(options: CreatePendingLineOptions): ChartPriceLine {
    const color = options.side === OrderSide.BUY ? PRICE_LINE_COLORS.BUY : PRICE_LINE_COLORS.SELL
    const sideText = options.side === OrderSide.BUY ? '买入' : '卖出'

    const config: ChartPriceLine = {
      id: this.generateLineId(),
      orderId: options.orderId,
      type: PriceLineType.PENDING,
      price: options.price,
      color,
      lineWidth: 1,
      lineStyle: 'dotted',
      title: `挂单 ${sideText} ${options.quantity}手 @ ${options.price}`,
      draggable: true,
    }

    return this.createLine(config)
  }

  /**
   * 创建预览线（画线模式时显示）
   */
  createPreviewLine(price: number): ChartPriceLine {
    // 如果已存在预览线，更新价格
    const existingPreview = this.getLinesByType(PriceLineType.PREVIEW)[0]
    if (existingPreview) {
      return this.updateLine(existingPreview.id, { price, title: `${price.toFixed(0)}` }) || existingPreview
    }

    const config: ChartPriceLine = {
      id: this.generateLineId(),
      type: PriceLineType.PREVIEW,
      price,
      color: PRICE_LINE_COLORS.PREVIEW,
      lineWidth: 1,
      lineStyle: 'dotted',
      title: `${price.toFixed(0)}`,
      draggable: false,
    }

    return this.createLine(config)
  }

  /**
   * 移除预览线
   */
  removePreviewLine(): boolean {
    const previewLines = this.getLinesByType(PriceLineType.PREVIEW)
    let removed = false
    // 移除所有预览线（防止累积）
    for (const line of previewLines) {
      if (this.removeLine(line.id)) {
        removed = true
      }
    }
    return removed
  }

  /**
   * 清理无效线条（用于调试和维护）
   */
  cleanup(): number {
    const before = this.lines.size
    // 移除所有预览线
    const previewLines = this.getLinesByType(PriceLineType.PREVIEW)
    for (const line of previewLines) {
      this.lines.delete(line.id)
    }
    const after = this.lines.size
    const removed = before - after
    if (removed > 0) {
      console.log(`🧹 Cleaned up ${removed} preview lines`)
      this.notifyChange()
    }
    return removed
  }

  /**
   * 获取指定ID的线条
   */
  getLine(id: string): ChartPriceLine | undefined {
    return this.lines.get(id)
  }

  /**
   * 更新线条
   */
  updateLine(id: string, updates: Partial<ChartPriceLine>): ChartPriceLine | undefined {
    const line = this.lines.get(id)
    if (!line) return undefined

    // 更新配置
    Object.assign(line, updates)
    
    // 更新标题（如果价格变化）
    if (updates.price !== undefined && !updates.title) {
      // 根据线条类型更新标题
      if (line.type === PriceLineType.STOP_LOSS) {
        line.title = `止损 @ ${updates.price}`
      } else if (line.type === PriceLineType.TAKE_PROFIT) {
        line.title = `止盈 @ ${updates.price}`
      } else if (line.type === PriceLineType.PREVIEW) {
        line.title = `${updates.price.toFixed(0)}`
      }
    }

    this.notifyChange()
    return line
  }

  /**
   * 移除指定ID的线条
   */
  removeLine(id: string): boolean {
    const result = this.lines.delete(id)
    if (result) {
      this.notifyChange()
    }
    return result
  }

  /**
   * 移除指定订单的所有线条
   */
  removeLinesByOrderId(orderId: string): number {
    const linesToRemove = this.getLinesByOrderId(orderId)
    linesToRemove.forEach(line => this.lines.delete(line.id))
    if (linesToRemove.length > 0) {
      this.notifyChange()
    }
    return linesToRemove.length
  }

  /**
   * 获取指定订单的所有线条
   */
  getLinesByOrderId(orderId: string): ChartPriceLine[] {
    return Array.from(this.lines.values()).filter(line => line.orderId === orderId)
  }

  /**
   * 获取指定类型的所有线条
   */
  getLinesByType(type: PriceLineType): ChartPriceLine[] {
    return Array.from(this.lines.values()).filter(line => line.type === type)
  }

  /**
   * 获取所有线条
   */
  getAllLines(): ChartPriceLine[] {
    return Array.from(this.lines.values())
  }

  /**
   * 获取所有可拖拽的线条
   */
  getDraggableLines(): ChartPriceLine[] {
    return Array.from(this.lines.values()).filter(line => line.draggable)
  }

  /**
   * 清除所有线条
   */
  clearAllLines(): void {
    this.lines.clear()
    this.notifyChange()
  }

  /**
   * 将价格线配置转换为ECharts markLine数据
   */
  toEChartsMarkLineData(): MarkLineComponentOption['data'] {
    const data: any[] = []
    
    this.lines.forEach(line => {
      data.push({
        name: line.id,
        yAxis: line.price,
        lineStyle: {
          color: line.color,
          width: line.lineWidth,
          type: LINE_STYLE_MAP[line.lineStyle],
        },
        label: {
          show: true,
          formatter: line.title || `${line.price}`,
          position: 'end',
          color: line.color,
          backgroundColor: 'rgba(30, 30, 30, 0.9)',
          padding: [4, 8],
          borderRadius: 4,
        },
      })
    })

    return data
  }

  /**
   * 生成完整的ECharts markLine配置
   */
  toEChartsMarkLineOption(): MarkLineComponentOption {
    return {
      silent: false, // 允许交互
      symbol: 'none', // 不显示端点符号
      animation: false, // 禁用动画以提高拖拽响应性
      data: this.toEChartsMarkLineData(),
    }
  }
}

/**
 * 辅助函数：根据像素Y坐标查找最近的价格线
 * @param lines 价格线数组
 * @param pixelY 像素Y坐标
 * @param priceToPixel 价格到像素的转换函数
 * @param threshold 检测阈值（像素）
 * @returns 最近的价格线，如果没有在阈值内则返回null
 */
export function findNearestPriceLine(
  lines: ChartPriceLine[],
  pixelY: number,
  priceToPixel: (price: number) => number,
  threshold: number = 10
): ChartPriceLine | null {
  let nearestLine: ChartPriceLine | null = null
  let minDistance = Infinity

  for (const line of lines) {
    const linePixelY = priceToPixel(line.price)
    const distance = Math.abs(pixelY - linePixelY)
    
    if (distance < threshold && distance < minDistance) {
      minDistance = distance
      nearestLine = line
    }
  }

  return nearestLine
}

/**
 * 辅助函数：查找最近的可拖拽价格线
 */
export function findNearestDraggablePriceLine(
  lines: ChartPriceLine[],
  pixelY: number,
  priceToPixel: (price: number) => number,
  threshold: number = 10
): ChartPriceLine | null {
  const draggableLines = lines.filter(line => line.draggable)
  return findNearestPriceLine(draggableLines, pixelY, priceToPixel, threshold)
}

