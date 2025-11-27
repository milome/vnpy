import { memo } from 'react'
import { DrawingMode } from '../types'

interface TradingToolbarProps {
  // 画线模式
  drawingMode: DrawingMode
  isDrawing: boolean
  onEnableDrawingMode: (mode: DrawingMode) => void
  onDisableDrawingMode: () => void
  
  // 自动追踪止损
  autoTrailingEnabled: boolean
  stopLossOffset: number
  onSetAutoTrailingEnabled: (enabled: boolean) => void
  onSetStopLossOffset: (offset: number) => void
}

/**
 * 交易工具栏
 * 包含画线下单按钮和自动止损设置
 */
function TradingToolbar({
  drawingMode,
  isDrawing,
  onEnableDrawingMode,
  onDisableDrawingMode,
  autoTrailingEnabled,
  stopLossOffset,
  onSetAutoTrailingEnabled,
  onSetStopLossOffset,
}: TradingToolbarProps) {
  return (
    <div style={{
      position: 'absolute',
      top: '10px',
      right: '10px',
      zIndex: 10,
      backgroundColor: 'rgba(30, 30, 30, 0.95)',
      padding: '10px',
      borderRadius: '6px',
      fontSize: '0.85rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      minWidth: '180px',
    }}>
      {/* 画线下单按钮 */}
      <div>
        <div style={{ marginBottom: '6px', fontWeight: 'bold', color: '#ffffff', fontSize: '0.8rem' }}>
          画线下单
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => isDrawing ? onDisableDrawingMode() : onEnableDrawingMode(DrawingMode.PENDING)}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: isDrawing ? '#4a9eff' : '#2a2a2a',
              color: '#fff',
              border: isDrawing ? '1px solid #4a9eff' : '1px solid #404040',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: '500',
              transition: 'all 0.2s',
            }}
          >
            {isDrawing ? '取消画线' : '开始画线'}
          </button>
        </div>
        {isDrawing && (
          <div style={{ 
            marginTop: '6px', 
            padding: '6px 8px',
            backgroundColor: 'rgba(74, 158, 255, 0.2)',
            borderRadius: '4px',
            fontSize: '0.75rem',
            color: '#4a9eff',
          }}>
            点击图表选择价格 | ESC取消
          </div>
        )}
      </div>

      {/* 分隔线 */}
      <div style={{ borderTop: '1px solid #404040', margin: '4px 0' }} />

      {/* 自动追踪止损设置 */}
      <div>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '8px',
        }}>
          <span style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.8rem' }}>自动止损</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoTrailingEnabled}
              onChange={(e) => onSetAutoTrailingEnabled(e.target.checked)}
              style={{ 
                width: '14px', 
                height: '14px',
                cursor: 'pointer',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: autoTrailingEnabled ? '#00d9ff' : '#888' }}>
              {autoTrailingEnabled ? '开启' : '关闭'}
            </span>
          </label>
        </div>
        
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px',
          opacity: autoTrailingEnabled ? 1 : 0.5,
        }}>
          <span style={{ fontSize: '0.75rem', color: '#888' }}>止损点数:</span>
          <input
            type="number"
            value={stopLossOffset}
            onChange={(e) => onSetStopLossOffset(Math.max(1, parseInt(e.target.value) || 1))}
            disabled={!autoTrailingEnabled}
            style={{
              width: '60px',
              padding: '4px 6px',
              backgroundColor: '#1e1e1e',
              border: '1px solid #404040',
              borderRadius: '4px',
              color: '#fff',
              fontSize: '0.8rem',
              fontFamily: 'monospace',
            }}
            min="1"
          />
        </div>
      </div>
    </div>
  )
}

export default memo(TradingToolbar)

