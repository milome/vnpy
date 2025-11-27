import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickData, CandlestickSeries } from 'lightweight-charts'
import { Timeframe } from '../types'
import './MultiTimeframeChart.css'

interface SimpleTradingViewChartProps {
  timeframes: Timeframe[]
  height?: string
}

/**
 * Simple TradingView Chart for Testing - MINIMAL VERSION
 */
export default function SimpleTradingViewChart({
  timeframes,
  height = '100%',
}: SimpleTradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    try {
      // Create chart with minimal configuration
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#1e1e1e' },
          textColor: '#ffffff',
        },
        width: chartContainerRef.current.clientWidth,
        height: chartContainerRef.current.clientHeight || 500,
      })

      // Create simple test data
      const testData: CandlestickData[] = [
        { time: '2022-01-01' as any, open: 100, high: 105, low: 95, close: 102 },
        { time: '2022-01-02' as any, open: 102, high: 110, low: 100, close: 108 },
        { time: '2022-01-03' as any, open: 108, high: 115, low: 105, close: 112 },
      ]

      // Try to create candlestick series using the correct API
      const series = chart.addSeries(CandlestickSeries, {
        upColor: 'transparent',  // 阳线空心
        downColor: '#00d9ff',
        borderUpColor: '#ff4757',
        borderDownColor: '#00d9ff',
        wickUpColor: '#ff4757',
        wickDownColor: '#00d9ff',
      })

      series.setData(testData)

      console.log('✅ SimpleTradingView - Chart created successfully!')

      return () => {
        chart.remove()
      }
    } catch (err) {
      console.error('❌ SimpleTradingView - Error:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [height])

  if (error) {
    return (
      <div className="chart-error">
        <p>⚠️ SimpleTradingView Error:</p>
        <p className="error-message">{error}</p>
      </div>
    )
  }

  return (
    <div className="simple-tradingview-chart" style={{ position: 'relative', width: '100%', height }}>
      <div ref={chartContainerRef} style={{ width: '100%', height }} />
      <div style={{ position: 'absolute', top: '10px', left: '10px', fontSize: '0.8rem', color: '#4caf50' }}>
        ✅ SimpleTradingView Test
      </div>
    </div>
  )
}