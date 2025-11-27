import { ChartKLineData, TimeframeConfig } from '../types'
import { CHART_COLORS } from './chartConfig'
import type { EChartsOption, CustomSeriesOption, CustomSeriesRenderItem } from 'echarts'

/**
 * D12: 4小时K线画线渲染器
 * 
 * 使用画线方式绘制4小时K线，而不是传统K线API
 * 
 * 绘制方式：
 * 1. 从结束时间向起始时间分别画出开盘价和收盘价的水平线
 * 2. 在起始时间和结束时间分别画出竖线连接开盘价和收盘价
 * 3. 在K线实体的中点位置绘制上下影线
 * 4. 根据涨跌确定颜色（阳线红色，阴线青色）
 */

/**
 * 4小时K线的扩展数据结构
 * 包含绘制所需的起止时间和OHLC数据
 */
export interface FourHourCandleData {
  startTimestamp: number    // 开始时间戳 (如 17:15)
  endTimestamp: number      // 结束时间戳 (如 21:14)
  midpointTimestamp?: number // K线数量中点时间戳（用于绘制影线，避免休市区间）
  open: number              // 开盘价
  high: number              // 最高价
  low: number               // 最低价
  close: number             // 收盘价
  volume: number            // 成交量
  isBullish: boolean        // 是否为阳线
}

/**
 * 4小时时段的精确结束时间定义
 * 根据 D12 决策文档
 */
const PERIOD_END_OFFSETS: Record<number, { endHour: number; endMinute: number }> = {
  1: { endHour: 21, endMinute: 14 },   // 17:15 -> 21:14
  2: { endHour: 1, endMinute: 14 },    // 21:15 -> 01:14 (次日)
  3: { endHour: 11, endMinute: 29 },   // 01:15 -> 11:29
  4: { endHour: 16, endMinute: 29 },   // 11:30 -> 16:29
}

/**
 * 根据开始时间戳计算周期ID
 */
function getPeriodIdFromStartTime(timestamp: number): number {
  const date = new Date(timestamp)
  const hour = date.getHours()
  const minute = date.getMinutes()

  if (hour === 17 && minute === 15) return 1
  if (hour === 21 && minute === 15) return 2
  if (hour === 1 && minute === 15) return 3
  if (hour === 11 && minute === 30) return 4

  return 0 // Unknown period
}

/**
 * 计算4小时K线的结束时间戳
 */
export function calculateEndTimestamp(startTimestamp: number): number {
  const periodId = getPeriodIdFromStartTime(startTimestamp)
  if (periodId === 0) return startTimestamp

  const endOffset = PERIOD_END_OFFSETS[periodId]
  const date = new Date(startTimestamp)

  // 设置结束时间
  if (periodId === 2) {
    // 第二根K线跨午夜，结束时间在次日
    date.setDate(date.getDate() + 1)
  }

  date.setHours(endOffset.endHour, endOffset.endMinute, 0, 0)
  return date.getTime()
}

/**
 * 将 ChartKLineData 转换为 FourHourCandleData
 * 支持 midpointTimestamp（K线数量中点时间戳，用于绘制影线）
 */
export function convertToFourHourCandleData(data: ChartKLineData): FourHourCandleData {
  const endTimestamp = calculateEndTimestamp(data.timestamp)
  
  return {
    startTimestamp: data.timestamp,
    endTimestamp,
    midpointTimestamp: data.midpointTimestamp, // 从聚合数据传递中点时间戳
    open: data.open,
    high: data.high,
    low: data.low,
    close: data.close,
    volume: data.volume,
    isBullish: data.close >= data.open,
  }
}

/**
 * 批量转换数据
 */
export function convertAllToFourHourCandleData(dataArray: ChartKLineData[]): FourHourCandleData[] {
  return dataArray.map(convertToFourHourCandleData)
}

/**
 * 获取K线颜色
 */
export function getCandleColor(isBullish: boolean): string {
  return isBullish ? CHART_COLORS.bullish : CHART_COLORS.bearish
}

/**
 * 创建4小时K线画线系列的 ECharts 自定义渲染函数
 * 
 * 绘制元素：
 * 1. 实体顶部水平线 (开盘价或收盘价，取较高者)
 * 2. 实体底部水平线 (开盘价或收盘价，取较低者)
 * 3. 左侧竖线 (连接开盘价和收盘价，在起始时间位置)
 * 4. 右侧竖线 (连接开盘价和收盘价，在结束时间位置)
 * 5. 上影线 (从实体顶部到最高价)
 * 6. 下影线 (从实体底部到最低价)
 */
export const fourHourCandleRenderItem: CustomSeriesRenderItem = (params, api) => {
  // 获取数据值
  const startTimestamp = api.value(0) as number
  const endTimestamp = api.value(1) as number
  const open = api.value(2) as number
  const high = api.value(3) as number
  const low = api.value(4) as number
  const close = api.value(5) as number
  const midpointTimestamp = api.value(6) as number | undefined  // K线数量中点时间戳

  // 判断涨跌
  const isBullish = close >= open
  const color = getCandleColor(isBullish)

  // 计算实体的上下边界
  const bodyTop = Math.max(open, close)
  const bodyBottom = Math.min(open, close)

  // 转换为像素坐标
  const startPoint = api.coord([startTimestamp, 0])
  const endPoint = api.coord([endTimestamp, 0])

  // 获取X坐标
  const x1 = startPoint[0]  // 起始时间X坐标
  const x2 = endPoint[0]    // 结束时间X坐标
  
  // 计算影线X坐标：优先使用K线数量中点时间戳，否则使用时间中点
  let midX: number
  if (midpointTimestamp && midpointTimestamp > 0) {
    const midPoint = api.coord([midpointTimestamp, 0])
    midX = midPoint[0]
  } else {
    midX = (x1 + x2) / 2
  }

  // 获取Y坐标 (注意：ECharts Y轴是从下到上，但像素坐标是从上到下)
  const yTop = api.coord([0, bodyTop])[1]
  const yBottom = api.coord([0, bodyBottom])[1]
  const yHigh = api.coord([0, high])[1]
  const yLow = api.coord([0, low])[1]

  // 线宽配置
  const lineWidth = 2

  // 创建绘制元素组
  const children: any[] = []

  // 1. 实体顶部水平线 (从 x1 到 x2)
  children.push({
    type: 'line',
    shape: {
      x1: x1,
      y1: yTop,
      x2: x2,
      y2: yTop,
    },
    style: {
      stroke: color,
      lineWidth: lineWidth,
    },
  })

  // 2. 实体底部水平线 (从 x1 到 x2)
  children.push({
    type: 'line',
    shape: {
      x1: x1,
      y1: yBottom,
      x2: x2,
      y2: yBottom,
    },
    style: {
      stroke: color,
      lineWidth: lineWidth,
    },
  })

  // 3. 左侧竖线 (在起始时间位置，连接顶部和底部)
  children.push({
    type: 'line',
    shape: {
      x1: x1,
      y1: yTop,
      x2: x1,
      y2: yBottom,
    },
    style: {
      stroke: color,
      lineWidth: lineWidth,
    },
  })

  // 4. 右侧竖线 (在结束时间位置，连接顶部和底部)
  children.push({
    type: 'line',
    shape: {
      x1: x2,
      y1: yTop,
      x2: x2,
      y2: yBottom,
    },
    style: {
      stroke: color,
      lineWidth: lineWidth,
    },
  })

  // 5. 上影线 (从实体顶部到最高价，在中点位置)
  if (high > bodyTop) {
    children.push({
      type: 'line',
      shape: {
        x1: midX,
        y1: yTop,
        x2: midX,
        y2: yHigh,
      },
      style: {
        stroke: color,
        lineWidth: lineWidth,
      },
    })
  }

  // 6. 下影线 (从实体底部到最低价，在中点位置)
  if (low < bodyBottom) {
    children.push({
      type: 'line',
      shape: {
        x1: midX,
        y1: yBottom,
        x2: midX,
        y2: yLow,
      },
      style: {
        stroke: color,
        lineWidth: lineWidth,
      },
    })
  }

  return {
    type: 'group',
    children,
  }
}

/**
 * 创建4小时K线画线系列配置
 * 
 * @param name 系列名称
 * @param data 4小时K线数据数组
 * @param config 时间周期配置
 * @returns ECharts custom series 配置
 */
export function createFourHourCandleLineSeries(
  name: string,
  data: FourHourCandleData[],
  config: TimeframeConfig
): CustomSeriesOption {
  // 转换为 ECharts custom series 需要的数据格式
  // [startTimestamp, endTimestamp, open, high, low, close, midpointTimestamp]
  const seriesData = data.map(item => [
    item.startTimestamp,
    item.endTimestamp,
    item.open,
    item.high,
    item.low,
    item.close,
    item.midpointTimestamp || 0,  // K线数量中点时间戳
  ])

  return {
    name,
    type: 'custom',
    renderItem: fourHourCandleRenderItem,
    encode: {
      x: [0, 1],  // 使用 startTimestamp 和 endTimestamp 作为 x 轴范围
      y: [2, 3, 4, 5],  // 使用 open, high, low, close 作为 y 轴范围
    },
    data: seriesData,
    z: config.zIndex,
    clip: true,
  }
}

/**
 * 从 ChartKLineData 数组直接创建系列配置
 */
export function createFourHourCandleLineSeriesFromChartData(
  name: string,
  data: ChartKLineData[],
  config: TimeframeConfig
): CustomSeriesOption {
  const fourHourData = convertAllToFourHourCandleData(data)
  return createFourHourCandleLineSeries(name, fourHourData, config)
}

/**
 * 创建适用于category轴的4小时K线画线系列配置
 * 使用索引而不是时间戳来定位X坐标
 * 
 * @param name 系列名称
 * @param data 4小时K线数据数组
 * @param config 时间周期配置
 * @param timestampToIndex 时间戳到索引的映射
 * @returns ECharts custom series 配置
 */
export function createFourHourCandleLineSeriesForCategoryAxis(
  name: string,
  data: FourHourCandleData[],
  config: TimeframeConfig,
  timestampToIndex: Map<number, number>
): CustomSeriesOption {
  // 转换为 ECharts custom series 需要的数据格式
  // 对于category轴，使用索引而不是时间戳
  // [startIndex, endIndex, open, high, low, close, midIndex]
  const seriesData = data.map(item => {
    // 查找最接近的索引
    const startIndex = findClosestIndex(item.startTimestamp, timestampToIndex)
    const endIndex = findClosestIndex(item.endTimestamp, timestampToIndex)
    const midIndex = item.midpointTimestamp 
      ? findClosestIndex(item.midpointTimestamp, timestampToIndex)
      : Math.floor((startIndex + endIndex) / 2)
    
    return [
      startIndex,
      endIndex,
      item.open,
      item.high,
      item.low,
      item.close,
      midIndex,
    ]
  }).filter(item => item[0] >= 0 && item[1] >= 0) // 过滤掉无法定位的数据

  return {
    name,
    type: 'custom',
    renderItem: fourHourCandleRenderItemForCategory,
    encode: {
      x: [0, 1],  // 使用 startIndex 和 endIndex 作为 x 轴范围
      y: [2, 3, 4, 5],  // 使用 open, high, low, close 作为 y 轴范围
    },
    data: seriesData,
    z: config.zIndex,
    clip: true,
  }
}

/**
 * 查找最接近的索引
 */
function findClosestIndex(timestamp: number, timestampToIndex: Map<number, number>): number {
  // 精确匹配
  if (timestampToIndex.has(timestamp)) {
    return timestampToIndex.get(timestamp)!
  }
  
  // 查找最接近的时间戳
  let closestTimestamp = -1
  let closestDistance = Infinity
  
  for (const [ts] of timestampToIndex) {
    const distance = Math.abs(ts - timestamp)
    if (distance < closestDistance) {
      closestDistance = distance
      closestTimestamp = ts
    }
  }
  
  return closestTimestamp >= 0 ? timestampToIndex.get(closestTimestamp)! : -1
}

/**
 * 4小时K线画线渲染函数 (category轴版本)
 * 使用索引而不是时间戳
 */
export const fourHourCandleRenderItemForCategory: CustomSeriesRenderItem = (params, api) => {
  // 获取数据值 (索引)
  const startIndex = api.value(0) as number
  const endIndex = api.value(1) as number
  const open = api.value(2) as number
  const high = api.value(3) as number
  const low = api.value(4) as number
  const close = api.value(5) as number
  const midIndex = api.value(6) as number

  // 判断涨跌
  const isBullish = close >= open
  const color = getCandleColor(isBullish)

  // 计算实体的上下边界
  const bodyTop = Math.max(open, close)
  const bodyBottom = Math.min(open, close)

  // 转换为像素坐标 (category轴使用索引)
  const startPoint = api.coord([startIndex, 0])
  const endPoint = api.coord([endIndex, 0])

  // 获取X坐标
  const x1 = startPoint[0]  // 起始索引X坐标
  const x2 = endPoint[0]    // 结束索引X坐标
  
  // 计算影线X坐标：使用中点索引
  const midPoint = api.coord([midIndex, 0])
  const midX = midPoint[0]

  // 获取Y坐标
  const yTop = api.coord([0, bodyTop])[1]
  const yBottom = api.coord([0, bodyBottom])[1]
  const yHigh = api.coord([0, high])[1]
  const yLow = api.coord([0, low])[1]

  // 线宽配置
  const lineWidth = 2

  // 创建绘制元素组
  const children: any[] = []

  // 1. 实体顶部水平线 (从 x1 到 x2)
  children.push({
    type: 'line',
    shape: { x1: x1, y1: yTop, x2: x2, y2: yTop },
    style: { stroke: color, lineWidth: lineWidth },
  })

  // 2. 实体底部水平线 (从 x1 到 x2)
  children.push({
    type: 'line',
    shape: { x1: x1, y1: yBottom, x2: x2, y2: yBottom },
    style: { stroke: color, lineWidth: lineWidth },
  })

  // 3. 左侧竖线 (在起始位置，连接顶部和底部)
  children.push({
    type: 'line',
    shape: { x1: x1, y1: yTop, x2: x1, y2: yBottom },
    style: { stroke: color, lineWidth: lineWidth },
  })

  // 4. 右侧竖线 (在结束位置，连接顶部和底部)
  children.push({
    type: 'line',
    shape: { x1: x2, y1: yTop, x2: x2, y2: yBottom },
    style: { stroke: color, lineWidth: lineWidth },
  })

  // 5. 上影线 (从实体顶部到最高价，在中点位置)
  if (high > bodyTop) {
    children.push({
      type: 'line',
      shape: { x1: midX, y1: yTop, x2: midX, y2: yHigh },
      style: { stroke: color, lineWidth: lineWidth },
    })
  }

  // 6. 下影线 (从实体底部到最低价，在中点位置)
  if (low < bodyBottom) {
    children.push({
      type: 'line',
      shape: { x1: midX, y1: yBottom, x2: midX, y2: yLow },
      style: { stroke: color, lineWidth: lineWidth },
    })
  }

  return {
    type: 'group',
    children,
  }
}

