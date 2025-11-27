import { describe, it, expect } from 'vitest'
import {
  FourHourCandleData,
  convertToFourHourCandleData,
  convertAllToFourHourCandleData,
  calculateEndTimestamp,
  getCandleColor,
  createFourHourCandleLineSeries,
} from '../utils/fourHourCandleRenderer'
import { CHART_COLORS, TIMEFRAME_CONFIGS } from '../utils/chartConfig'
import { ChartKLineData, Timeframe } from '../types'

/**
 * D12.2 4小时K线画线渲染器单元测试
 * 验证画线渲染器的数据转换和颜色判断逻辑
 */

// 辅助函数：创建指定时间的时间戳
function createTimestamp(year: number, month: number, day: number, hour: number, minute: number): number {
  return new Date(year, month - 1, day, hour, minute, 0, 0).getTime()
}

// 测试日期
const TEST_YEAR = 2025
const TEST_MONTH = 11
const TEST_DAY = 27

describe('4小时K线画线渲染器', () => {
  describe('calculateEndTimestamp - 结束时间戳计算', () => {
    it('第一根4H (17:15) 的结束时间应为 21:14', () => {
      const startTs = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15)
      const endTs = calculateEndTimestamp(startTs)
      
      const endDate = new Date(endTs)
      expect(endDate.getHours()).toBe(21)
      expect(endDate.getMinutes()).toBe(14)
      expect(endDate.getDate()).toBe(TEST_DAY) // 同一天
    })

    it('第二根4H (21:15) 的结束时间应为次日 01:14', () => {
      const startTs = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15)
      const endTs = calculateEndTimestamp(startTs)
      
      const endDate = new Date(endTs)
      expect(endDate.getHours()).toBe(1)
      expect(endDate.getMinutes()).toBe(14)
      expect(endDate.getDate()).toBe(TEST_DAY + 1) // 次日
    })

    it('第三根4H (01:15) 的结束时间应为 11:29', () => {
      const startTs = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 1, 15)
      const endTs = calculateEndTimestamp(startTs)
      
      const endDate = new Date(endTs)
      expect(endDate.getHours()).toBe(11)
      expect(endDate.getMinutes()).toBe(29)
      expect(endDate.getDate()).toBe(TEST_DAY) // 同一天
    })

    it('第四根4H (11:30) 的结束时间应为 16:29', () => {
      const startTs = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30)
      const endTs = calculateEndTimestamp(startTs)
      
      const endDate = new Date(endTs)
      expect(endDate.getHours()).toBe(16)
      expect(endDate.getMinutes()).toBe(29)
      expect(endDate.getDate()).toBe(TEST_DAY) // 同一天
    })

    it('未知周期开始时间应返回原时间戳', () => {
      const startTs = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 8, 0) // 非标准开始时间
      const endTs = calculateEndTimestamp(startTs)
      expect(endTs).toBe(startTs)
    })
  })

  describe('convertToFourHourCandleData - 数据转换', () => {
    it('应正确转换阳线数据 (close > open)', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
        open: 25000,
        high: 25200,
        low: 24900,
        close: 25150,
        volume: 1000,
      }

      const result = convertToFourHourCandleData(input)

      expect(result.startTimestamp).toBe(input.timestamp)
      expect(result.open).toBe(25000)
      expect(result.high).toBe(25200)
      expect(result.low).toBe(24900)
      expect(result.close).toBe(25150)
      expect(result.volume).toBe(1000)
      expect(result.isBullish).toBe(true) // close > open
    })

    it('应正确转换阴线数据 (close < open)', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15),
        open: 25150,
        high: 25200,
        low: 24900,
        close: 25000,
        volume: 1500,
      }

      const result = convertToFourHourCandleData(input)

      expect(result.isBullish).toBe(false) // close < open
    })

    it('应正确处理平盘数据 (close = open)', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 1, 15),
        open: 25000,
        high: 25100,
        low: 24900,
        close: 25000,
        volume: 800,
      }

      const result = convertToFourHourCandleData(input)

      expect(result.isBullish).toBe(true) // close >= open 视为阳线
    })

    it('应正确计算结束时间戳', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30),
        open: 25000,
        high: 25200,
        low: 24900,
        close: 25100,
        volume: 1200,
      }

      const result = convertToFourHourCandleData(input)

      const endDate = new Date(result.endTimestamp)
      expect(endDate.getHours()).toBe(16)
      expect(endDate.getMinutes()).toBe(29)
    })
  })

  describe('convertAllToFourHourCandleData - 批量转换', () => {
    it('应正确批量转换数据数组', () => {
      const inputs: ChartKLineData[] = [
        {
          timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
          open: 25000, high: 25200, low: 24900, close: 25150, volume: 1000,
        },
        {
          timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15),
          open: 25150, high: 25300, low: 25000, close: 25250, volume: 1500,
        },
      ]

      const results = convertAllToFourHourCandleData(inputs)

      expect(results).toHaveLength(2)
      expect(results[0].startTimestamp).toBe(inputs[0].timestamp)
      expect(results[1].startTimestamp).toBe(inputs[1].timestamp)
    })

    it('应正确处理空数组', () => {
      const results = convertAllToFourHourCandleData([])
      expect(results).toHaveLength(0)
    })
  })

  describe('getCandleColor - 颜色判断', () => {
    it('阳线应返回红色 (bullish color)', () => {
      const color = getCandleColor(true)
      expect(color).toBe(CHART_COLORS.bullish)
    })

    it('阴线应返回青色 (bearish color)', () => {
      const color = getCandleColor(false)
      expect(color).toBe(CHART_COLORS.bearish)
    })
  })

  describe('createFourHourCandleLineSeries - 系列配置生成', () => {
    const mockData: FourHourCandleData[] = [
      {
        startTimestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
        endTimestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 14),
        open: 25000, high: 25200, low: 24900, close: 25150, volume: 1000, isBullish: true,
      },
      {
        startTimestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15),
        endTimestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY + 1, 1, 14),
        open: 25150, high: 25300, low: 25000, close: 25000, volume: 1500, isBullish: false,
      },
    ]

    it('应创建 custom 类型的系列', () => {
      const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
      const series = createFourHourCandleLineSeries('4小时 (画线)', mockData, config)

      expect(series.type).toBe('custom')
      expect(series.name).toBe('4小时 (画线)')
    })

    it('应包含正确的数据格式', () => {
      const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
      const series = createFourHourCandleLineSeries('4H', mockData, config)

      expect(series.data).toHaveLength(2)
      
      // 验证第一条数据格式: [startTimestamp, endTimestamp, open, high, low, close]
      const firstData = series.data![0] as number[]
      expect(firstData[0]).toBe(mockData[0].startTimestamp)
      expect(firstData[1]).toBe(mockData[0].endTimestamp)
      expect(firstData[2]).toBe(mockData[0].open)
      expect(firstData[3]).toBe(mockData[0].high)
      expect(firstData[4]).toBe(mockData[0].low)
      expect(firstData[5]).toBe(mockData[0].close)
    })

    it('应使用配置中的 zIndex', () => {
      const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
      const series = createFourHourCandleLineSeries('4H', mockData, config)

      expect(series.z).toBe(config.zIndex)
    })

    it('应设置正确的 encode 映射', () => {
      const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
      const series = createFourHourCandleLineSeries('4H', mockData, config)

      expect(series.encode).toEqual({
        x: [0, 1],
        y: [2, 3, 4, 5],
      })
    })

    it('应设置 clip 为 true', () => {
      const config = TIMEFRAME_CONFIGS[Timeframe.FOUR_HOURS]
      const series = createFourHourCandleLineSeries('4H', mockData, config)

      expect(series.clip).toBe(true)
    })
  })

  describe('边界情况测试', () => {
    it('应处理只有上影线的K线 (high > max(open, close))', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
        open: 25000,
        high: 25300, // 高于 open 和 close
        low: 25000,  // 等于 open
        close: 25100,
        volume: 1000,
      }

      const result = convertToFourHourCandleData(input)
      
      expect(result.high).toBeGreaterThan(Math.max(result.open, result.close))
      expect(result.low).toBe(Math.min(result.open, result.close))
    })

    it('应处理只有下影线的K线 (low < min(open, close))', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
        open: 25000,
        high: 25100, // 等于 close
        low: 24800,  // 低于 open 和 close
        close: 25100,
        volume: 1000,
      }

      const result = convertToFourHourCandleData(input)
      
      expect(result.high).toBe(Math.max(result.open, result.close))
      expect(result.low).toBeLessThan(Math.min(result.open, result.close))
    })

    it('应处理无影线的K线 (十字星形态)', () => {
      const input: ChartKLineData = {
        timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15),
        open: 25000,
        high: 25000,
        low: 25000,
        close: 25000,
        volume: 100,
      }

      const result = convertToFourHourCandleData(input)
      
      expect(result.open).toBe(result.high)
      expect(result.open).toBe(result.low)
      expect(result.open).toBe(result.close)
      expect(result.isBullish).toBe(true) // 平盘视为阳线
    })
  })
})

