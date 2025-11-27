import { useState, useCallback } from 'react'
import './App.css'
// import MultiTimeframeChart from './components/MultiTimeframeChart'  // 备用
import EChartsTradingChart from './components/EChartsTradingChart'
import TradingViewChart from './components/TradingViewChart'
// import SimpleTradingViewChart from './components/SimpleTradingViewChart'  // 备用
import DataLoadingDialog from './components/DataLoadingDialog'
import { Timeframe } from './types'
import { dataService } from './services/dataService'

// 计算默认日期（最近7天）
const getDefaultDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 7)
  
  const formatDate = (d: Date) => d.toISOString().split('T')[0]
  return {
    start: formatDate(start),
    end: formatDate(end),
  }
}

const defaultDates = getDefaultDates()

function App() {
  // Display only 4H and 1M for testing
  const timeframes = [
    Timeframe.FOUR_HOURS,
    // Timeframe.ONE_HOUR,
    // Timeframe.FIVE_MINUTES,
    Timeframe.ONE_MINUTE,
  ]

  const [chartEngine, setChartEngine] = useState<'echarts-trading' | 'tradingview'>('tradingview')
  
  // 日期选择（UI显示用）
  const [selectedStartDate, setSelectedStartDate] = useState(defaultDates.start)
  const [selectedEndDate, setSelectedEndDate] = useState(defaultDates.end)
  
  // 实际加载的日期（图表使用）
  const [loadedStartDate, setLoadedStartDate] = useState(defaultDates.start)
  const [loadedEndDate, setLoadedEndDate] = useState(defaultDates.end)
  
  const [refreshKey, setRefreshKey] = useState(0)
  
  // 数据加载弹窗状态
  const [isLoadingDialogOpen, setIsLoadingDialogOpen] = useState(false)

  // 检查日期是否有变化
  const hasDateChanged = selectedStartDate !== loadedStartDate || selectedEndDate !== loadedEndDate

  // 打开加载弹窗
  const handleOpenLoadDialog = useCallback(() => {
    setIsLoadingDialogOpen(true)
  }, [])

  // 关闭加载弹窗
  const handleCloseLoadDialog = useCallback(() => {
    setIsLoadingDialogOpen(false)
  }, [])

  // 确认加载数据
  const handleConfirmLoad = useCallback(() => {
    // 关闭弹窗
    setIsLoadingDialogOpen(false)
    
    // 清除缓存并更新日期，触发图表重新加载
    dataService.clearCache()
    setLoadedStartDate(selectedStartDate)
    setLoadedEndDate(selectedEndDate)
    setRefreshKey(prev => prev + 1)
  }, [selectedStartDate, selectedEndDate])

  const handleRefreshData = () => {
    dataService.clearCache()
    // Force re-render by incrementing refresh key
    setRefreshKey(prev => prev + 1)
  }

  const renderChart = () => {
    switch (chartEngine) {
      case 'tradingview':
        return <TradingViewChart timeframes={timeframes} startDate={loadedStartDate} endDate={loadedEndDate} key={`tv-${loadedStartDate}-${loadedEndDate}-${refreshKey}`} />
      case 'echarts-trading':
        return <EChartsTradingChart timeframes={timeframes} startDate={loadedStartDate} endDate={loadedEndDate} key={`ect-${loadedStartDate}-${loadedEndDate}-${refreshKey}`} />
      default:
        return <TradingViewChart timeframes={timeframes} startDate={loadedStartDate} endDate={loadedEndDate} key={`tv-${loadedStartDate}-${loadedEndDate}-${refreshKey}`} />
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Multi-Timeframe K-Line Chart</h1>
        <div className="contract-info">
          <span className="symbol">MHImain</span>
          <span className="exchange">HKFE</span>
        </div>
        <div className="controls">
          <div className="chart-engine-selector">
            <label>
              图表引擎:
              <select
                value={chartEngine}
                onChange={(e) => setChartEngine(e.target.value as 'echarts-trading' | 'tradingview')}
              >
                <option value="tradingview">TradingView ⭐</option>
                <option value="echarts-trading">ECharts</option>
              </select>
            </label>
          </div>
          {(
            <div className="time-range-selector">
              <label>
                起始时间:
                <input
                  type="date"
                  value={selectedStartDate}
                  onChange={(e) => setSelectedStartDate(e.target.value)}
                  style={{ marginLeft: '8px', padding: '4px' }}
                />
              </label>
              <label style={{ marginLeft: '16px' }}>
                结束时间:
                <input
                  type="date"
                  value={selectedEndDate}
                  onChange={(e) => setSelectedEndDate(e.target.value)}
                  style={{ marginLeft: '8px', padding: '4px' }}
                />
              </label>
              {/* 加载数据按钮 - 日期变化时高亮显示 */}
              <button 
                onClick={handleOpenLoadDialog} 
                style={{ 
                  marginLeft: '16px', 
                  padding: '8px 16px', 
                  cursor: 'pointer',
                  backgroundColor: hasDateChanged ? '#1e90ff' : '#4a4a4a',
                  color: '#fff',
                  border: hasDateChanged ? '2px solid #1e90ff' : '1px solid #666',
                  borderRadius: '6px',
                  fontWeight: hasDateChanged ? '600' : '400',
                  transition: 'all 0.2s',
                }}
              >
                📥 {hasDateChanged ? '加载新数据' : '加载数据'}
              </button>
            </div>
          )}
          <button onClick={handleRefreshData} style={{ marginLeft: '10px', padding: '8px 16px', cursor: 'pointer' }}>
            刷新缓存
          </button>
        </div>
      </header>
      <main className="app-main">
        <div className="chart-container">
          {renderChart()}
        </div>
      </main>

      {/* 数据加载确认弹窗 */}
      <DataLoadingDialog
        isOpen={isLoadingDialogOpen}
        startDate={selectedStartDate}
        endDate={selectedEndDate}
        onConfirm={handleConfirmLoad}
        onCancel={handleCloseLoadDialog}
      />
    </div>
  )
}

export default App
