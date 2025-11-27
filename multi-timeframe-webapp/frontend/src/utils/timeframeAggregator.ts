import { ChartKLineData } from '../types'

/**
 * Frontend K-line aggregator for HKFE trading sessions
 * Aggregates 1-minute data into correct 4-hour periods
 * 
 * D12 Decision: 精确的4小时时间边界划分
 * 参见 .speckit.clarify D12: 4小时K线时间边界划分与画线绘制方式
 */

/**
 * HKFE Trading Sessions with PRECISE boundaries (D12 更新):
 * - Night Session: 17:15-03:00 (crosses midnight)
 * - Day Session Morning: 09:15-12:00
 * - Day Session Afternoon: 13:00-16:30
 *
 * 4-Hour Periods (D12 精确边界):
 * 1. 17:15-21:14 (第一根4小时K线，时间戳：17:15)
 *    - 开盘价：17:15的1分钟开盘价
 *    - 收盘价：21:14的1分钟收盘价
 * 
 * 2. 21:15-01:14 (第二根4小时K线，时间戳：21:15，跨午夜)
 *    - 开盘价：21:15的1分钟开盘价
 *    - 收盘价：01:14的1分钟收盘价
 * 
 * 3. 01:15-03:00 + 09:15-11:29 (第三根4小时K线，时间戳：01:15，跨休市)
 *    - 开盘价：01:15的1分钟开盘价
 *    - 收盘价：11:29的1分钟收盘价
 * 
 * 4. 11:30-12:00 + 13:00-16:29 (第四根4小时K线，时间戳：11:30，跨午休)
 *    - 开盘价：11:30的1分钟开盘价
 *    - 收盘价：16:29的1分钟收盘价
 */

export interface TradingPeriod {
  id: number
  name: string
  startTime: { hour: number; minute: number }
  sessions: Array<{
    start: { hour: number; minute: number }
    end: { hour: number; minute: number }
    crossesMidnight?: boolean
  }>
}

/**
 * D12 精确时间边界配置
 * 边界规则：结束时间包含在当前周期内（闭区间）
 */
export const TRADING_PERIODS: TradingPeriod[] = [
  {
    id: 1,
    name: '第一根4H (夜盘前段)',
    startTime: { hour: 17, minute: 15 },
    sessions: [
      // 17:15-21:14 (包含21:14)
      { start: { hour: 17, minute: 15 }, end: { hour: 21, minute: 14 } }
    ]
  },
  {
    id: 2,
    name: '第二根4H (夜盘中段)',
    startTime: { hour: 21, minute: 15 },
    sessions: [
      // 21:15-01:14 (跨午夜，包含01:14)
      { start: { hour: 21, minute: 15 }, end: { hour: 1, minute: 14 }, crossesMidnight: true }
    ]
  },
  {
    id: 3,
    name: '第三根4H (夜盘尾段+早盘)',
    startTime: { hour: 1, minute: 15 },
    sessions: [
      // 01:15-03:00 (夜盘尾段)
      { start: { hour: 1, minute: 15 }, end: { hour: 3, minute: 0 } },
      // 09:15-11:29 (早盘，包含11:29)
      { start: { hour: 9, minute: 15 }, end: { hour: 11, minute: 29 } }
    ]
  },
  {
    id: 4,
    name: '第四根4H (午盘)',
    startTime: { hour: 11, minute: 30 },
    sessions: [
      // 11:30-12:00 (午盘前段)
      { start: { hour: 11, minute: 30 }, end: { hour: 12, minute: 0 } },
      // 13:00-16:29 (午盘后段，包含16:29)
      { start: { hour: 13, minute: 0 }, end: { hour: 16, minute: 29 } }
    ]
  }
]

/**
 * Get the 4-hour period start time for a given timestamp
 * D12: 使用精确的时间边界
 */
function getPeriodStartTime(timestamp: number, periodId: number): number {
  const date = new Date(timestamp)
  const hour = date.getHours()

  // Create base date for the period start time
  let periodDate = new Date(timestamp)
  periodDate.setSeconds(0)
  periodDate.setMilliseconds(0)

  const period = TRADING_PERIODS.find(p => p.id === periodId)
  if (!period) return timestamp

  switch (periodId) {
    case 1: // 第一根4H: 17:15-21:14
      periodDate.setHours(17, 15)
      break

    case 2: // 第二根4H: 21:15-01:14 (跨午夜)
      // 如果在 00:00-01:14 范围内，周期开始于前一天
      if (hour >= 0 && hour < 2) {
        periodDate.setDate(periodDate.getDate() - 1)
      }
      periodDate.setHours(21, 15)
      break

    case 3: // 第三根4H: 01:15-03:00 + 09:15-11:29 (跨休市)
      // 时间戳始终使用 01:15
      if (hour >= 9) {
        // 如果在早盘时段 (09:15-11:29)
        // 需要判断是否跨越周末：周一需要回溯到上周六的01:15
        const dayOfWeek = periodDate.getDay() // 0=Sunday, 1=Monday, ...
        if (dayOfWeek === 1) {
          // 周一：回溯到上周六（2天前）的01:15
          periodDate.setDate(periodDate.getDate() - 2)
        }
        periodDate.setHours(1, 15)
      } else {
        // 如果在夜盘尾段 (01:15-03:00)，周期开始于当天 01:15
        periodDate.setHours(1, 15)
      }
      break

    case 4: // 第四根4H: 11:30-12:00 + 13:00-16:29 (跨午休)
      periodDate.setHours(11, 30)
      break

    default:
      return timestamp
  }

  return periodDate.getTime()
}

/**
 * Determine which trading period a timestamp belongs to
 * D12: 使用精确的时间边界判断
 */
export function getTradingPeriod(timestamp: number): { period: TradingPeriod; periodStart: number } | null {
  const date = new Date(timestamp)
  const hour = date.getHours()
  const minute = date.getMinutes()
  const totalMinutes = hour * 60 + minute

  // 按照 D12 精确边界检查每个时段
  for (const period of TRADING_PERIODS) {
    for (const session of period.sessions) {
      const startMinutes = session.start.hour * 60 + session.start.minute
      const endMinutes = session.end.hour * 60 + session.end.minute

      let isInSession = false

      if (session.crossesMidnight) {
        // 处理跨午夜时段 (21:15-01:14)
        // 21:15-23:59 或 00:00-01:14
        if (totalMinutes >= startMinutes || totalMinutes <= endMinutes) {
          isInSession = true
        }
      } else {
        // 同一天内的时段 (闭区间，包含结束时间)
        if (totalMinutes >= startMinutes && totalMinutes <= endMinutes) {
          isInSession = true
        }
      }

      if (isInSession) {
        const periodStart = getPeriodStartTime(timestamp, period.id)
        return { period, periodStart }
      }
    }
  }

  return null // 非交易时间
}

/**
 * Aggregate 1-minute data into 4-hour periods
 * 包含中点时间戳计算（用于绘制影线，避免休市时间段）
 */
export function aggregateTo4Hours(data1min: ChartKLineData[]): ChartKLineData[] {
  if (!data1min || data1min.length === 0) return []

  // Group data by period
  const periodGroups = new Map<string, ChartKLineData[]>()

  for (const item of data1min) {
    const periodInfo = getTradingPeriod(item.timestamp)

    if (!periodInfo) {
      // Skip data outside trading hours
      continue
    }

    const { periodStart } = periodInfo
    const periodKey = periodStart.toString()

    if (!periodGroups.has(periodKey)) {
      periodGroups.set(periodKey, [])
    }

    periodGroups.get(periodKey)!.push(item)
  }

  // Aggregate each period group
  const aggregatedData: ChartKLineData[] = []

  for (const [periodStartStr, periodData] of periodGroups.entries()) {
    if (periodData.length === 0) continue

    // Sort by timestamp to ensure correct order
    periodData.sort((a, b) => a.timestamp - b.timestamp)

    // 计算K线数量中点的时间戳
    // 这样影线会绑制在实际K线数据的中间位置，而不是时间中点
    // 对于跨休市的时间段（如01:15-03:00 + 09:15-11:29），这避免了影线落在休市区间
    const midIndex = Math.floor(periodData.length / 2)
    const midpointTimestamp = periodData[midIndex].timestamp

    const aggregated: ChartKLineData = {
      timestamp: parseInt(periodStartStr),
      open: periodData[0].open,  // First open
      high: Math.max(...periodData.map(d => d.high)),  // Highest high
      low: Math.min(...periodData.map(d => d.low)),    // Lowest low
      close: periodData[periodData.length - 1].close,  // Last close
      volume: periodData.reduce((sum, d) => sum + d.volume, 0),  // Total volume
      midpointTimestamp,  // K线数量中点时间戳
    }

    aggregatedData.push(aggregated)
  }

  // Sort by timestamp
  aggregatedData.sort((a, b) => a.timestamp - b.timestamp)

  return aggregatedData
}

/**
 * Create display name for aggregated timeframes
 */
export function getAggregatedTimeframeName(originalTimeframe: string): string {
  if (originalTimeframe === '4hour') {
    return '4H (Aggregated)'
  }
  return originalTimeframe
}