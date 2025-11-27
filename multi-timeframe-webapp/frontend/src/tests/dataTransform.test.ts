import { describe, it, expect } from 'vitest'
import {
  convertToChartData,
  convertArrayToChartData,
  filterByDateRange,
  sortByTimestamp,
  getDataRange,
  validateKLineData,
} from '../utils/dataTransform'
import { KLineData, ChartKLineData } from '../types'

describe('dataTransform', () => {
  const mockKLineData: KLineData = {
    symbol: 'MHImain',
    exchange: 'HKFE',
    datetime: '2024-01-01 09:00:00',
    open: 25000,
    high: 25100,
    low: 24900,
    close: 25050,
    volume: 1000,
    turnover: 25000000,
    open_interest: 0,
  }

  describe('convertToChartData', () => {
    it('should convert KLineData to ChartKLineData', () => {
      const result = convertToChartData(mockKLineData)

      expect(result).toHaveProperty('timestamp')
      expect(result).toHaveProperty('open', 25000)
      expect(result).toHaveProperty('high', 25100)
      expect(result).toHaveProperty('low', 24900)
      expect(result).toHaveProperty('close', 25050)
      expect(result).toHaveProperty('volume', 1000)
      expect(typeof result.timestamp).toBe('number')
    })

    it('should convert datetime string to Unix timestamp', () => {
      const result = convertToChartData(mockKLineData)
      const expectedTimestamp = new Date('2024-01-01 09:00:00').getTime()
      expect(result.timestamp).toBe(expectedTimestamp)
    })
  })

  describe('convertArrayToChartData', () => {
    it('should convert array of KLineData', () => {
      const dataArray: KLineData[] = [mockKLineData, { ...mockKLineData, datetime: '2024-01-01 10:00:00' }]
      const result = convertArrayToChartData(dataArray)

      expect(result).toHaveLength(2)
      expect(result[0]).toHaveProperty('timestamp')
      expect(result[1]).toHaveProperty('timestamp')
    })
  })

  describe('filterByDateRange', () => {
    const chartData: ChartKLineData[] = [
      { timestamp: 1000, open: 100, high: 110, low: 90, close: 105, volume: 1000 },
      { timestamp: 2000, open: 105, high: 115, low: 95, close: 110, volume: 1500 },
      { timestamp: 3000, open: 110, high: 120, low: 100, close: 115, volume: 2000 },
    ]

    it('should filter by start time', () => {
      const result = filterByDateRange(chartData, 2000)
      expect(result).toHaveLength(2)
      expect(result[0].timestamp).toBe(2000)
    })

    it('should filter by end time', () => {
      const result = filterByDateRange(chartData, undefined, 2000)
      expect(result).toHaveLength(2)
      expect(result[1].timestamp).toBe(2000)
    })

    it('should filter by both start and end time', () => {
      const result = filterByDateRange(chartData, 1500, 2500)
      expect(result).toHaveLength(1)
      expect(result[0].timestamp).toBe(2000)
    })
  })

  describe('sortByTimestamp', () => {
    it('should sort data by timestamp ascending', () => {
      const unsortedData: ChartKLineData[] = [
        { timestamp: 3000, open: 110, high: 120, low: 100, close: 115, volume: 2000 },
        { timestamp: 1000, open: 100, high: 110, low: 90, close: 105, volume: 1000 },
        { timestamp: 2000, open: 105, high: 115, low: 95, close: 110, volume: 1500 },
      ]

      const result = sortByTimestamp(unsortedData)
      expect(result[0].timestamp).toBe(1000)
      expect(result[1].timestamp).toBe(2000)
      expect(result[2].timestamp).toBe(3000)
    })

    it('should not mutate original array', () => {
      const original: ChartKLineData[] = [
        { timestamp: 3000, open: 110, high: 120, low: 100, close: 115, volume: 2000 },
        { timestamp: 1000, open: 100, high: 110, low: 90, close: 105, volume: 1000 },
      ]

      sortByTimestamp(original)
      expect(original[0].timestamp).toBe(3000)
    })
  })

  describe('getDataRange', () => {
    it('should return min and max timestamps', () => {
      const data: ChartKLineData[] = [
        { timestamp: 2000, open: 105, high: 115, low: 95, close: 110, volume: 1500 },
        { timestamp: 1000, open: 100, high: 110, low: 90, close: 105, volume: 1000 },
        { timestamp: 3000, open: 110, high: 120, low: 100, close: 115, volume: 2000 },
      ]

      const result = getDataRange(data)
      expect(result).toEqual({ start: 1000, end: 3000 })
    })

    it('should return null for empty array', () => {
      const result = getDataRange([])
      expect(result).toBeNull()
    })
  })

  describe('validateKLineData', () => {
    it('should validate correct data', () => {
      expect(validateKLineData(mockKLineData)).toBe(true)
    })

    it('should reject data with missing datetime', () => {
      const invalidData = { ...mockKLineData, datetime: '' }
      expect(validateKLineData(invalidData)).toBe(false)
    })

    it('should reject data with invalid high < low', () => {
      const invalidData = { ...mockKLineData, high: 24800, low: 24900 }
      expect(validateKLineData(invalidData)).toBe(false)
    })

    it('should reject data with high < open', () => {
      const invalidData = { ...mockKLineData, high: 24900, open: 25000 }
      expect(validateKLineData(invalidData)).toBe(false)
    })

    it('should reject data with low > close', () => {
      const invalidData = { ...mockKLineData, low: 25100, close: 25050 }
      expect(validateKLineData(invalidData)).toBe(false)
    })
  })
})
