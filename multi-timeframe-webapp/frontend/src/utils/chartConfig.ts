import { Timeframe, TimeframeConfig } from '../types'
import type { EChartsOption } from 'echarts'

/**
 * Timeframe visual configurations
 * Larger timeframes have thicker lines and lower z-index (rendered behind)
 */
export const TIMEFRAME_CONFIGS: Record<Timeframe, TimeframeConfig> = {
  [Timeframe.FOUR_HOURS]: {
    timeframe: Timeframe.FOUR_HOURS,
    lineWidth: 6,
    opacity: 0.6,
    zIndex: 1,
  },
  [Timeframe.ONE_HOUR]: {
    timeframe: Timeframe.ONE_HOUR,
    lineWidth: 4,
    opacity: 0.7,
    zIndex: 2,
  },
  [Timeframe.FIVE_MINUTES]: {
    timeframe: Timeframe.FIVE_MINUTES,
    lineWidth: 2,
    opacity: 0.85,
    zIndex: 3,
  },
  [Timeframe.ONE_MINUTE]: {
    timeframe: Timeframe.ONE_MINUTE,
    lineWidth: 1,
    opacity: 1.0,
    zIndex: 4,
  },
  [Timeframe.ONE_DAY]: {
    timeframe: Timeframe.ONE_DAY,
    lineWidth: 8,
    opacity: 0.5,
    zIndex: 0,
  },
}

/**
 * Color scheme for candlesticks
 * Chinese convention: Red for bullish (阳线), Cyan for bearish (阴线)
 */
export const CHART_COLORS = {
  bullish: '#ff4757', // Red for bullish (close > open) - Chinese convention
  bearish: '#00d9ff', // Cyan for bearish (close < open) - Chinese convention
  background: '#1e1e1e',
  grid: '#404040',
  text: '#ffffff',
  axisLine: '#404040',
}

/**
 * Create ECharts candlestick series configuration
 */
export function createCandlestickSeries(
  name: string,
  data: [number, number, number, number, number][], // [timestamp, open, high, low, close]
  config: TimeframeConfig
): EChartsOption['series'] {
  return {
    name,
    type: 'candlestick',
    data,
    itemStyle: {
      color: CHART_COLORS.bullish,
      color0: CHART_COLORS.bearish,
      borderColor: CHART_COLORS.bullish,
      borderColor0: CHART_COLORS.bearish,
      borderWidth: config.lineWidth,
      opacity: config.opacity,
    },
    z: config.zIndex,
  }
}

/**
 * 格式化时间戳为显示标签
 */
export function formatTimeLabel(timestamp: number): string {
  const date = new Date(timestamp)
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = date.getHours()
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${hours}:${minutes}`
}

/**
 * 格式化时间戳为完整日期时间
 */
export function formatFullDateTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    weekday: 'short',
  })
}

/**
 * Create base ECharts configuration
 * 使用category类型的X轴，跳过休市时间（周末、假期等）
 */
export function createBaseChartOption(): EChartsOption {
  return {
    backgroundColor: CHART_COLORS.background,
    grid: {
      left: '10%',
      right: '10%',
      top: '10%',
      bottom: '15%',
      borderColor: CHART_COLORS.grid,
    },
    xAxis: {
      type: 'category',
      boundaryGap: true,
      data: [], // 将由数据填充
      axisLine: {
        lineStyle: {
          color: CHART_COLORS.axisLine,
        },
      },
      axisLabel: {
        color: CHART_COLORS.text,
        // 每隔一定数量显示标签，避免拥挤
        interval: 'auto',
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: CHART_COLORS.grid,
          opacity: 0.3,
        },
      },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: {
        lineStyle: {
          color: CHART_COLORS.axisLine,
        },
      },
      axisLabel: {
        color: CHART_COLORS.text,
      },
      splitLine: {
        lineStyle: {
          color: CHART_COLORS.grid,
          opacity: 0.3,
        },
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: CHART_COLORS.text,
          opacity: 0.5,
        },
      },
      backgroundColor: 'rgba(50, 50, 50, 0.9)',
      borderColor: CHART_COLORS.grid,
      textStyle: {
        color: CHART_COLORS.text,
      },
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        minValueSpan: 10, // Minimum visible range
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        backgroundColor: CHART_COLORS.background,
        dataBackground: {
          lineStyle: {
            color: CHART_COLORS.grid,
          },
          areaStyle: {
            color: CHART_COLORS.grid,
            opacity: 0.3,
          },
        },
        fillerColor: 'rgba(38, 166, 154, 0.2)',
        handleStyle: {
          color: CHART_COLORS.bullish,
        },
        textStyle: {
          color: CHART_COLORS.text,
        },
        height: 30,
      },
    ],
    series: [],
  }
}

/**
 * Create ECharts candlestick series configuration for category axis
 * 数据格式: [open, close, low, high] （ECharts K线格式）
 */
export function createCategoryCandlestickSeries(
  name: string,
  data: [number, number, number, number][], // [open, close, low, high]
  config: TimeframeConfig
): EChartsOption['series'] {
  return {
    name,
    type: 'candlestick',
    data,
    itemStyle: {
      color: CHART_COLORS.bullish,
      color0: CHART_COLORS.bearish,
      borderColor: CHART_COLORS.bullish,
      borderColor0: CHART_COLORS.bearish,
      borderWidth: config.lineWidth,
      opacity: config.opacity,
    },
    z: config.zIndex,
  }
}
