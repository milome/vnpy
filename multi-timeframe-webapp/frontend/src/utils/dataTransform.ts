import { KLineData, ChartKLineData } from '../types'

/**
 * Convert CSV K-line data to chart format
 * Normalizes datetime to Unix timestamp and ensures numeric types
 */
export function convertToChartData(data: KLineData): ChartKLineData {
  return {
    timestamp: new Date(data.datetime).getTime(),
    open: Number(data.open),
    high: Number(data.high),
    low: Number(data.low),
    close: Number(data.close),
    volume: Number(data.volume),
  }
}

/**
 * Convert array of CSV data to chart data array
 */
export function convertArrayToChartData(dataArray: KLineData[]): ChartKLineData[] {
  return dataArray.map(convertToChartData)
}

/**
 * Filter data by date range
 */
export function filterByDateRange(
  data: ChartKLineData[],
  startTime?: number,
  endTime?: number
): ChartKLineData[] {
  return data.filter((item) => {
    if (startTime && item.timestamp < startTime) return false
    if (endTime && item.timestamp > endTime) return false
    return true
  })
}

/**
 * Sort data by timestamp ascending
 */
export function sortByTimestamp(data: ChartKLineData[]): ChartKLineData[] {
  return [...data].sort((a, b) => a.timestamp - b.timestamp)
}

/**
 * Get data range (min and max timestamps)
 */
export function getDataRange(data: ChartKLineData[]): { start: number; end: number } | null {
  if (data.length === 0) return null

  const timestamps = data.map((d) => d.timestamp)
  return {
    start: Math.min(...timestamps),
    end: Math.max(...timestamps),
  }
}

/**
 * Validate K-line data integrity
 */
export function validateKLineData(data: KLineData): boolean {
  // Check required fields exist
  if (!data.datetime || !data.symbol || !data.exchange) return false

  // Convert to numbers
  const open = Number(data.open)
  const high = Number(data.high)
  const low = Number(data.low)
  const close = Number(data.close)

  // Check if all values are valid numbers
  if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) return false

  // Check basic OHLC relationships
  // High should be the highest value
  if (high < low) return false
  if (high < Math.max(open, close)) return false
  if (low > Math.min(open, close)) return false

  return true
}
