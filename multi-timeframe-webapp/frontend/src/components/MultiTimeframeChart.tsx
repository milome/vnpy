import { useEffect, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { Timeframe, ChartKLineData } from '../types'
import { dataService } from '../services/dataService'
import {
  createBaseChartOption,
  createCandlestickSeries,
  TIMEFRAME_CONFIGS,
} from '../utils/chartConfig'
import { aggregateTo4Hours } from '../utils/timeframeAggregator'
import { createFourHourCandleLineSeriesFromChartData } from '../utils/fourHourCandleRenderer'
import './MultiTimeframeChart.css'

interface MultiTimeframeChartProps {
  timeframes: Timeframe[]
  height?: string
  startDate?: string
  endDate?: string
}

/**
 * Multi-Timeframe K-Line Chart Component
 * Displays multiple timeframe candlestick charts overlaid on a single view
 */
export default function MultiTimeframeChart({
  timeframes,
  height = '100%',
  startDate,
  endDate,
}: MultiTimeframeChartProps) {
  const [chartOption, setChartOption] = useState<EChartsOption>(createBaseChartOption())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<ReactECharts>(null)

  useEffect(() => {
    loadChartData()
  }, [timeframes, startDate, endDate])

  // Filter data by time range
  const filterDataByTimeRange = (data: ChartKLineData[]): ChartKLineData[] => {
    if (!startDate && !endDate) return data

    const startTimestamp = startDate ? new Date(startDate).getTime() : 0
    const endTimestamp = endDate ? new Date(endDate).getTime() + 24 * 60 * 60 * 1000 : Infinity

    return data.filter(item => {
      return item.timestamp >= startTimestamp && item.timestamp < endTimestamp
    })
  }

  const loadChartData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Clear cache to force fresh data loading
      dataService.clearCache()

      // Load all data (no limit)
      const originalLimit = dataService.getDataLimit()
      dataService.setDataLimit(-1)

      // Load only 1-minute data from CSV
      console.log('🔍 Loading 1-minute data...')
      const oneMinRawData = await dataService.getData(Timeframe.ONE_MINUTE)

      // Restore original limit
      dataService.setDataLimit(originalLimit)

      // Filter by time range
      const oneMinData = filterDataByTimeRange(oneMinRawData)

      // D12: 使用更新后的 timeframeAggregator 计算4小时K线（精确边界）
      const fourHourData = aggregateTo4Hours(oneMinData)

      console.log(`📊 Loaded ${oneMinData.length} 1-min candles, calculated ${fourHourData.length} 4-hour candles (D12 精确边界)`)

      // Create data map
      const dataMap = new Map<Timeframe, ChartKLineData[]>()
      dataMap.set(Timeframe.ONE_MINUTE, oneMinData)
      dataMap.set(Timeframe.FOUR_HOURS, fourHourData)

      // Convert data to ECharts format and create series
      const series: EChartsOption['series'] = []

      timeframes.forEach((timeframe) => {
        const data = dataMap.get(timeframe)
        if (!data || data.length === 0) return

        const config = TIMEFRAME_CONFIGS[timeframe]

        // D12: 4小时K线使用画线渲染器
        if (timeframe === Timeframe.FOUR_HOURS) {
          const lineSeriesConfig = createFourHourCandleLineSeriesFromChartData(
            getTimeframeName(timeframe) + ' (画线)',
            data,
            config
          )
          series.push(lineSeriesConfig)
          console.log(`🎨 使用画线渲染器绑制 ${data.length} 根4小时K线`)
          return
        }

        // Sample data if there are too many points (more than 2000 for 1-minute data)
        let sampledData = data
        if (timeframe === Timeframe.ONE_MINUTE && data.length > 2000) {
          // Sample every Nth point to get around 2000 points
          const step = Math.ceil(data.length / 2000)
          sampledData = data.filter((_, index) => index % step === 0)
          console.log(`📉 Sampled 1-min data: ${data.length} -> ${sampledData.length} (step: ${step})`)
        }

        // Convert to ECharts candlestick format: [timestamp, open, high, low, close]
        // NOTE: ECharts requires the order: open, HIGH, LOW, close (not open, close, low, high)
        const chartData: [number, number, number, number, number][] = sampledData.map((item) => [
          item.timestamp,
          item.open,
          item.high,
          item.low,
          item.close,
        ])

        const seriesConfig = createCandlestickSeries(
          getTimeframeName(timeframe),
          chartData,
          config
        )

        series.push(seriesConfig)
      })

      // Update chart option with new series
      const newOption: EChartsOption = {
        ...createBaseChartOption(),
        legend: {
          data: timeframes.map(getTimeframeName),
          textStyle: {
            color: '#ffffff',
          },
          top: 10,
          right: 50,
        },
        series,
      }

      setChartOption(newOption)
      setLoading(false)
    } catch (err) {
      console.error('Error loading chart data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load chart data')
      setLoading(false)
    }
  }

  const getTimeframeName = (timeframe: Timeframe): string => {
    const names: Record<Timeframe, string> = {
      [Timeframe.ONE_MINUTE]: '1分钟',
      [Timeframe.FIVE_MINUTES]: '5分钟',
      [Timeframe.ONE_HOUR]: '1小时',
      [Timeframe.FOUR_HOURS]: '4小时',
      [Timeframe.ONE_DAY]: '日线',
    }
    return names[timeframe]
  }

  if (loading) {
    return (
      <div className="chart-loading">
        <div className="loading-spinner"></div>
        <p>Loading chart data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="chart-error">
        <p>⚠️ Error loading chart</p>
        <p className="error-message">{error}</p>
        <button onClick={loadChartData}>Retry</button>
      </div>
    )
  }

  return (
    <div className="multi-timeframe-chart">
      <ReactECharts
        ref={chartRef}
        option={chartOption}
        style={{ height, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  )
}
