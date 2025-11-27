import { ISeriesApi, SeriesType, IPriceLine, LineStyle } from 'lightweight-charts';
import { ChartPriceLine, PriceLineType, OrderSide } from '../types';

// 颜色配置（中国惯例：红涨绿跌）
const COLORS = {
  BUY: '#ff4757',      // 红色 - 买入
  SELL: '#00d9ff',     // 青色 - 卖出
  STOP_LOSS: '#ffa502', // 橙色 - 止损
  TAKE_PROFIT: '#1e90ff', // 蓝色 - 止盈
  PREVIEW: '#ffffff80', // 半透明白色 - 预览
};

interface CreateEntryLineOptions {
  orderId: string;
  price: number;
  side: OrderSide;
  quantity: number;
}

interface CreateStopLossLineOptions {
  orderId: string;
  price: number;
  side: OrderSide;
}

interface CreateTakeProfitLineOptions {
  orderId: string;
  price: number;
  side: OrderSide;
}

interface CreatePendingLineOptions {
  orderId: string;
  price: number;
  side: OrderSide;
  quantity: number;
}

/**
 * 价格线管理器
 * 负责在图表上创建和管理各种价格线（入场、止损、止盈等）
 */
export class PriceLineManager {
  private series: ISeriesApi<SeriesType>;
  private lines: Map<string, ChartPriceLine> = new Map();
  private chartLines: Map<string, IPriceLine> = new Map();
  private lineIdCounter = 0;

  constructor(series: ISeriesApi<SeriesType>) {
    this.series = series;
  }

  /**
   * 生成唯一线条ID
   */
  private generateLineId(): string {
    this.lineIdCounter++;
    return `line_${Date.now()}_${this.lineIdCounter}`;
  }

  /**
   * 将内部线条样式转换为lightweight-charts的LineStyle
   */
  private getLineStyle(style: 'solid' | 'dashed' | 'dotted'): LineStyle {
    switch (style) {
      case 'solid':
        return LineStyle.Solid;
      case 'dashed':
        return LineStyle.Dashed;
      case 'dotted':
        return LineStyle.Dotted;
      default:
        return LineStyle.Solid;
    }
  }

  /**
   * 创建通用价格线（公共方法）
   * 用于创建自定义配置的价格线，如影子止损线
   */
  createPriceLine(config: ChartPriceLine): ChartPriceLine {
    return this.createLine(config);
  }

  /**
   * 创建价格线
   */
  private createLine(config: ChartPriceLine): ChartPriceLine {
    // 存储配置
    this.lines.set(config.id, config);

    // 在图表上创建价格线
    const chartLine = this.series.createPriceLine({
      id: config.id,
      price: config.price,
      color: config.color,
      lineWidth: config.lineWidth as 1 | 2 | 3 | 4,
      lineStyle: this.getLineStyle(config.lineStyle),
      title: config.title || '',
      axisLabelVisible: true,
      lineVisible: true,
    });

    this.chartLines.set(config.id, chartLine);

    return config;
  }

  /**
   * 创建入场价格线
   */
  createEntryLine(options: CreateEntryLineOptions): ChartPriceLine {
    const color = options.side === OrderSide.BUY ? COLORS.BUY : COLORS.SELL;
    const sideText = options.side === OrderSide.BUY ? '买入' : '卖出';
    
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
    };

    return this.createLine(config);
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
      color: COLORS.STOP_LOSS,
      lineWidth: 1,
      lineStyle: 'dashed',
      title: `止损 @ ${options.price}`,
      draggable: true,
    };

    return this.createLine(config);
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
      color: COLORS.TAKE_PROFIT,
      lineWidth: 1,
      lineStyle: 'dashed',
      title: `止盈 @ ${options.price}`,
      draggable: true,
    };

    return this.createLine(config);
  }

  /**
   * 创建挂单线
   */
  createPendingLine(options: CreatePendingLineOptions): ChartPriceLine {
    const color = options.side === OrderSide.BUY ? COLORS.BUY : COLORS.SELL;
    const sideText = options.side === OrderSide.BUY ? '买入' : '卖出';

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
    };

    return this.createLine(config);
  }

  /**
   * 创建预览线（画线模式时显示）
   */
  createPreviewLine(price: number): ChartPriceLine {
    // 如果已存在预览线，更新价格
    const existingPreview = this.getLinesByType(PriceLineType.PREVIEW)[0];
    if (existingPreview) {
      return this.updateLine(existingPreview.id, { price }) || existingPreview;
    }

    const config: ChartPriceLine = {
      id: this.generateLineId(),
      type: PriceLineType.PREVIEW,
      price,
      color: COLORS.PREVIEW,
      lineWidth: 1,
      lineStyle: 'dotted',
      title: `${price}`,
      draggable: false,
    };

    return this.createLine(config);
  }

  /**
   * 移除预览线
   */
  removePreviewLine(): boolean {
    const previewLines = this.getLinesByType(PriceLineType.PREVIEW);
    if (previewLines.length > 0) {
      return this.removeLine(previewLines[0].id);
    }
    return false;
  }

  /**
   * 获取指定ID的线条
   */
  getLine(id: string): ChartPriceLine | undefined {
    return this.lines.get(id);
  }

  /**
   * 更新线条
   */
  updateLine(id: string, updates: Partial<ChartPriceLine>): ChartPriceLine | undefined {
    const line = this.lines.get(id);
    if (!line) return undefined;

    // 更新配置
    Object.assign(line, updates);

    // 更新图表上的线条
    const chartLine = this.chartLines.get(id);
    if (chartLine) {
      const updateOptions: any = {};
      if (updates.price !== undefined) updateOptions.price = updates.price;
      if (updates.color !== undefined) updateOptions.color = updates.color;
      if (updates.lineWidth !== undefined) updateOptions.lineWidth = updates.lineWidth;
      if (updates.lineStyle !== undefined) updateOptions.lineStyle = this.getLineStyle(updates.lineStyle);
      if (updates.title !== undefined) updateOptions.title = updates.title;

      chartLine.applyOptions(updateOptions);
    }

    return line;
  }

  /**
   * 移除指定ID的线条
   */
  removeLine(id: string): boolean {
    const line = this.lines.get(id);
    if (!line) return false;

    // 从图表移除
    const chartLine = this.chartLines.get(id);
    if (chartLine) {
      this.series.removePriceLine(chartLine);
      this.chartLines.delete(id);
    }

    // 从存储移除
    this.lines.delete(id);

    return true;
  }

  /**
   * 移除指定订单的所有线条
   */
  removeLinesByOrderId(orderId: string): number {
    const linesToRemove = this.getLinesByOrderId(orderId);
    linesToRemove.forEach(line => this.removeLine(line.id));
    return linesToRemove.length;
  }

  /**
   * 获取指定订单的所有线条
   */
  getLinesByOrderId(orderId: string): ChartPriceLine[] {
    return Array.from(this.lines.values()).filter(line => line.orderId === orderId);
  }

  /**
   * 获取指定类型的所有线条
   */
  getLinesByType(type: PriceLineType): ChartPriceLine[] {
    return Array.from(this.lines.values()).filter(line => line.type === type);
  }

  /**
   * 获取所有线条
   */
  getAllLines(): ChartPriceLine[] {
    return Array.from(this.lines.values());
  }

  /**
   * 清除所有线条
   */
  clearAllLines(): void {
    // 从图表移除所有线条
    this.chartLines.forEach(chartLine => {
      this.series.removePriceLine(chartLine);
    });

    // 清空存储
    this.lines.clear();
    this.chartLines.clear();
  }

  /**
   * 更新关联的series（当图表重建时调用）
   */
  setSeries(series: ISeriesApi<SeriesType>): void {
    this.series = series;
    // 重新创建所有图表线条
    const allLines = Array.from(this.lines.values());
    this.chartLines.clear();
    
    allLines.forEach(line => {
      const chartLine = this.series.createPriceLine({
        id: line.id,
        price: line.price,
        color: line.color,
        lineWidth: line.lineWidth as 1 | 2 | 3 | 4,
        lineStyle: this.getLineStyle(line.lineStyle),
        title: line.title || '',
        axisLabelVisible: true,
        lineVisible: true,
      });
      this.chartLines.set(line.id, chartLine);
    });
  }
}

