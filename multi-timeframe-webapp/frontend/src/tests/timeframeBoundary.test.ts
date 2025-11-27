import { describe, it, expect } from 'vitest'
import { getTradingPeriod, TRADING_PERIODS, aggregateTo4Hours } from '../utils/timeframeAggregator'
import { ChartKLineData } from '../types'

/**
 * D12 时间边界判断单元测试
 * 验证精确的4小时K线时间边界划分
 * 
 * 精确边界定义:
 * 1. 17:15-21:14 (第一根4H，时间戳 17:15)
 * 2. 21:15-01:14 (第二根4H，时间戳 21:15，跨午夜)
 * 3. 01:15-03:00 + 09:15-11:29 (第三根4H，时间戳 01:15，跨休市)
 * 4. 11:30-12:00 + 13:00-16:29 (第四根4H，时间戳 11:30，跨午休)
 */

// 辅助函数：创建指定时间的时间戳
function createTimestamp(year: number, month: number, day: number, hour: number, minute: number): number {
  return new Date(year, month - 1, day, hour, minute, 0, 0).getTime()
}

// 使用固定日期 2025-11-27 进行测试
const TEST_YEAR = 2025
const TEST_MONTH = 11
const TEST_DAY = 27

describe('D12 时间边界判断', () => {
  describe('TRADING_PERIODS 配置验证', () => {
    it('应该有4个交易时段', () => {
      expect(TRADING_PERIODS).toHaveLength(4)
    })

    it('第一根4H配置正确: 17:15-21:14', () => {
      const period1 = TRADING_PERIODS[0]
      expect(period1.id).toBe(1)
      expect(period1.startTime).toEqual({ hour: 17, minute: 15 })
      expect(period1.sessions[0].start).toEqual({ hour: 17, minute: 15 })
      expect(period1.sessions[0].end).toEqual({ hour: 21, minute: 14 })
    })

    it('第二根4H配置正确: 21:15-01:14 (跨午夜)', () => {
      const period2 = TRADING_PERIODS[1]
      expect(period2.id).toBe(2)
      expect(period2.startTime).toEqual({ hour: 21, minute: 15 })
      expect(period2.sessions[0].start).toEqual({ hour: 21, minute: 15 })
      expect(period2.sessions[0].end).toEqual({ hour: 1, minute: 14 })
      expect(period2.sessions[0].crossesMidnight).toBe(true)
    })

    it('第三根4H配置正确: 01:15-03:00 + 09:15-11:29 (跨休市)', () => {
      const period3 = TRADING_PERIODS[2]
      expect(period3.id).toBe(3)
      expect(period3.startTime).toEqual({ hour: 1, minute: 15 })
      expect(period3.sessions).toHaveLength(2)
      expect(period3.sessions[0].start).toEqual({ hour: 1, minute: 15 })
      expect(period3.sessions[0].end).toEqual({ hour: 3, minute: 0 })
      expect(period3.sessions[1].start).toEqual({ hour: 9, minute: 15 })
      expect(period3.sessions[1].end).toEqual({ hour: 11, minute: 29 })
    })

    it('第四根4H配置正确: 11:30-12:00 + 13:00-16:29 (跨午休)', () => {
      const period4 = TRADING_PERIODS[3]
      expect(period4.id).toBe(4)
      expect(period4.startTime).toEqual({ hour: 11, minute: 30 })
      expect(period4.sessions).toHaveLength(2)
      expect(period4.sessions[0].start).toEqual({ hour: 11, minute: 30 })
      expect(period4.sessions[0].end).toEqual({ hour: 12, minute: 0 })
      expect(period4.sessions[1].start).toEqual({ hour: 13, minute: 0 })
      expect(period4.sessions[1].end).toEqual({ hour: 16, minute: 29 })
    })
  })

  describe('第一根4H边界判断 (17:15-21:14)', () => {
    it('17:15 应属于第一根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(1)
    })

    it('21:14 应属于第一根4H (边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 14)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(1)
    })

    it('21:15 应属于第二根4H (边界切换)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(2)
    })

    it('17:14 应为非交易时间', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 14)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })

    it('19:30 应属于第一根4H (中间时间)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 19, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(1)
    })
  })

  describe('第二根4H边界判断 (21:15-01:14 跨午夜)', () => {
    it('21:15 应属于第二根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(2)
    })

    it('23:59 应属于第二根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 23, 59)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(2)
    })

    it('00:00 (次日) 应属于第二根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY + 1, 0, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(2)
    })

    it('01:14 (次日) 应属于第二根4H (边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY + 1, 1, 14)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(2)
    })

    it('01:15 (次日) 应属于第三根4H (边界切换)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY + 1, 1, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(3)
    })
  })

  describe('第三根4H边界判断 (01:15-03:00 + 09:15-11:29 跨休市)', () => {
    it('01:15 应属于第三根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 1, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(3)
    })

    it('03:00 应属于第三根4H (夜盘尾段边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 3, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(3)
    })

    it('03:01 应为非交易时间 (休市)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 3, 1)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })

    it('09:14 应为非交易时间 (早盘前)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 9, 14)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })

    it('09:15 应属于第三根4H (早盘开始)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 9, 15)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(3)
    })

    it('11:29 应属于第三根4H (早盘边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 29)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(3)
    })

    it('11:30 应属于第四根4H (边界切换)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(4)
    })
  })

  describe('第四根4H边界判断 (11:30-12:00 + 13:00-16:29 跨午休)', () => {
    it('11:30 应属于第四根4H', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(4)
    })

    it('12:00 应属于第四根4H (午休前边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 12, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(4)
    })

    it('12:01 应为非交易时间 (午休)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 12, 1)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })

    it('12:59 应为非交易时间 (午休)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 12, 59)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })

    it('13:00 应属于第四根4H (午盘后段开始)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 13, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(4)
    })

    it('16:29 应属于第四根4H (收盘边界)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 16, 29)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      expect(result!.period.id).toBe(4)
    })

    it('16:30 应为非交易时间 (收盘后)', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 16, 30)
      const result = getTradingPeriod(ts)
      expect(result).toBeNull()
    })
  })

  describe('时间戳生成验证', () => {
    it('第一根4H的时间戳应为 17:15', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 19, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      
      const expectedTimestamp = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 17, 15)
      expect(result!.periodStart).toBe(expectedTimestamp)
    })

    it('第二根4H的时间戳应为 21:15', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 22, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      
      const expectedTimestamp = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15)
      expect(result!.periodStart).toBe(expectedTimestamp)
    })

    it('第二根4H跨午夜后的时间戳应指向前一天21:15', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY + 1, 0, 30)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      
      const expectedTimestamp = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 21, 15)
      expect(result!.periodStart).toBe(expectedTimestamp)
    })

    it('第三根4H的时间戳应为 01:15', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 10, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      
      const expectedTimestamp = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 1, 15)
      expect(result!.periodStart).toBe(expectedTimestamp)
    })

    it('第四根4H的时间戳应为 11:30', () => {
      const ts = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 15, 0)
      const result = getTradingPeriod(ts)
      expect(result).not.toBeNull()
      
      const expectedTimestamp = createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30)
      expect(result!.periodStart).toBe(expectedTimestamp)
    })
  })

  describe('聚合功能验证', () => {
    it('应正确聚合跨休市的第三根4H数据', () => {
      // 模拟 01:15-03:00 + 09:15-11:29 的数据
      const mockData: ChartKLineData[] = [
        // 夜盘尾段
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 1, 15), open: 25000, high: 25100, low: 24900, close: 25050, volume: 100 },
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 2, 0), open: 25050, high: 25150, low: 25000, close: 25100, volume: 150 },
        // 早盘
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 9, 15), open: 25100, high: 25200, low: 25050, close: 25150, volume: 200 },
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 29), open: 25150, high: 25250, low: 25100, close: 25200, volume: 250 },
      ]

      const result = aggregateTo4Hours(mockData)
      expect(result).toHaveLength(1)
      expect(result[0].open).toBe(25000)  // 01:15 的开盘价
      expect(result[0].close).toBe(25200) // 11:29 的收盘价
      expect(result[0].high).toBe(25250)  // 最高价
      expect(result[0].low).toBe(24900)   // 最低价
      expect(result[0].volume).toBe(700)  // 总成交量
    })

    it('应正确聚合跨午休的第四根4H数据', () => {
      // 模拟 11:30-12:00 + 13:00-16:29 的数据
      const mockData: ChartKLineData[] = [
        // 午盘前段
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 11, 30), open: 25200, high: 25300, low: 25150, close: 25250, volume: 100 },
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 12, 0), open: 25250, high: 25350, low: 25200, close: 25300, volume: 150 },
        // 午盘后段
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 13, 0), open: 25300, high: 25400, low: 25250, close: 25350, volume: 200 },
        { timestamp: createTimestamp(TEST_YEAR, TEST_MONTH, TEST_DAY, 16, 29), open: 25350, high: 25450, low: 25300, close: 25400, volume: 250 },
      ]

      const result = aggregateTo4Hours(mockData)
      expect(result).toHaveLength(1)
      expect(result[0].open).toBe(25200)  // 11:30 的开盘价
      expect(result[0].close).toBe(25400) // 16:29 的收盘价
      expect(result[0].high).toBe(25450)  // 最高价
      expect(result[0].low).toBe(25150)   // 最低价
      expect(result[0].volume).toBe(700)  // 总成交量
    })
  })
})

