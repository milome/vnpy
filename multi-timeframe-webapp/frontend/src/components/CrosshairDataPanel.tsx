import { memo } from 'react'

/**
 * 十字光标K线数据显示数据
 */
export interface CrosshairData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  change: number
  changePercent: number
}

interface CrosshairDataPanelProps {
  data: CrosshairData | null
  showLegend?: boolean
  legendItems?: Array<{ color: string; label: string }>
}

/**
 * 十字光标K线数据显示面板
 * 显示OHLCV数据和涨跌幅
 */
function CrosshairDataPanel({
  data,
  showLegend = true,
  legendItems = [],
}: CrosshairDataPanelProps) {
  return (
    <div style={{
      position: 'absolute',
      top: '10px',
      left: '10px',
      zIndex: 10,
      backgroundColor: 'rgba(30, 30, 30, 0.9)',
      padding: '10px',
      borderRadius: '6px',
      fontSize: '0.85rem',
      minWidth: '220px',
    }}>
      {/* K线数据显示 */}
      {data ? (
        <div style={{ marginBottom: showLegend ? '10px' : '0' }}>
          <div style={{ 
            color: '#888', 
            fontSize: '0.75rem', 
            marginBottom: '6px',
            borderBottom: '1px solid #404040',
            paddingBottom: '4px',
          }}>
            {data.time}
          </div>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '4px 12px',
            fontSize: '0.8rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>开:</span>
              <span style={{ color: '#fff', fontFamily: 'monospace' }}>{data.open.toFixed(0)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>高:</span>
              <span style={{ color: '#ff4757', fontFamily: 'monospace' }}>{data.high.toFixed(0)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>收:</span>
              <span style={{ color: '#fff', fontFamily: 'monospace' }}>{data.close.toFixed(0)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>低:</span>
              <span style={{ color: '#00d9ff', fontFamily: 'monospace' }}>{data.low.toFixed(0)}</span>
            </div>
          </div>
          <div style={{ 
            marginTop: '6px', 
            paddingTop: '6px', 
            borderTop: '1px solid #404040',
            fontSize: '0.8rem',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#888' }}>涨跌:</span>
              <span style={{ 
                color: data.change >= 0 ? '#ff4757' : '#00d9ff',
                fontFamily: 'monospace',
                fontWeight: '600',
              }}>
                {data.change >= 0 ? '+' : ''}{data.change.toFixed(0)} 
                ({data.changePercent >= 0 ? '+' : ''}{data.changePercent.toFixed(2)}%)
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888' }}>成交量:</span>
              <span style={{ 
                color: data.change >= 0 ? '#ff4757' : '#00d9ff',
                fontFamily: 'monospace',
              }}>
                {data.volume.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ 
          color: '#666', 
          fontSize: '0.75rem', 
          marginBottom: showLegend ? '10px' : '0',
          fontStyle: 'italic',
        }}>
          移动光标查看K线数据
        </div>
      )}
      
      {/* 图层图例 */}
      {showLegend && legendItems.length > 0 && (
        <div style={{ 
          borderTop: data ? '1px solid #404040' : 'none',
          paddingTop: data ? '8px' : '0',
        }}>
          <div style={{ marginBottom: '6px', fontWeight: 'bold', color: '#ffffff', fontSize: '0.8rem' }}>图层</div>
          {legendItems.map((item, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: index < legendItems.length - 1 ? '4px' : '0',
              }}
            >
              <div style={{
                width: '16px',
                height: '8px',
                backgroundColor: item.color,
                borderRadius: '2px',
              }} />
              <span style={{ color: '#aaa', fontSize: '0.75rem' }}>{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default memo(CrosshairDataPanel)

