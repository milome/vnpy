import { memo } from 'react'

type StatusType = 'drawing' | 'dragging' | 'creating' | 'nearLine' | 'dualStopLoss'

interface StatusIndicatorProps {
  type: StatusType
  visible: boolean
  // 画线模式提示
  drawingPrice?: number
  // 拖拽止损提示
  draggingInfo?: {
    originalPrice: number
    currentPrice: number
    shadowPrice?: number
  }
  // 创建止损/止盈提示
  creatingInfo?: {
    lineType: 'stop_loss' | 'take_profit'
    entryPrice: number
    currentPrice: number
  }
}

/**
 * 状态提示组件
 * 显示各种操作状态的提示信息
 */
function StatusIndicator({
  type,
  visible,
  drawingPrice,
  draggingInfo,
  creatingInfo,
}: StatusIndicatorProps) {
  if (!visible) return null

  const getStatusContent = () => {
    switch (type) {
      case 'drawing':
        return (
          <div>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>画线下单模式</div>
            {drawingPrice !== undefined && (
              <div style={{ fontSize: '1.1rem', fontFamily: 'monospace', color: '#90EE90' }}>
                {drawingPrice.toFixed(0)}
              </div>
            )}
            <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
              点击确认 | ESC取消
            </div>
          </div>
        )

      case 'dragging':
        return (
          <div>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>拖拽移动中</div>
            {draggingInfo && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>原价:</span>
                  <span style={{ fontFamily: 'monospace' }}>{draggingInfo.originalPrice.toFixed(0)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>当前:</span>
                  <span style={{ fontFamily: 'monospace', color: '#90EE90' }}>
                    {draggingInfo.currentPrice.toFixed(0)}
                  </span>
                </div>
                {draggingInfo.shadowPrice !== undefined && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                    <span style={{ opacity: 0.8 }}>保护:</span>
                    <span style={{ fontFamily: 'monospace', color: '#ffa502' }}>
                      {draggingInfo.shadowPrice.toFixed(0)}
                    </span>
                  </div>
                )}
              </>
            )}
            <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
              释放确认 | ESC取消
            </div>
          </div>
        )

      case 'creating':
        return (
          <div>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>
              创建{creatingInfo?.lineType === 'stop_loss' ? '止损' : '止盈'}线
            </div>
            {creatingInfo && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>成本价:</span>
                  <span style={{ fontFamily: 'monospace' }}>{creatingInfo.entryPrice.toFixed(0)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>
                    {creatingInfo.lineType === 'stop_loss' ? '止损:' : '止盈:'}
                  </span>
                  <span style={{ fontFamily: 'monospace', color: '#90EE90' }}>
                    {creatingInfo.currentPrice.toFixed(0)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>点差:</span>
                  <span style={{ fontFamily: 'monospace' }}>
                    {Math.abs(creatingInfo.currentPrice - creatingInfo.entryPrice).toFixed(0)}
                  </span>
                </div>
              </>
            )}
            <div style={{ fontSize: '0.75rem', marginTop: '4px', opacity: 0.8 }}>
              释放鼠标确认 | ESC取消
            </div>
          </div>
        )

      case 'nearLine':
        return (
          <div>拖拽移动 | 双击删除</div>
        )

      case 'dualStopLoss':
        return (
          <div>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>
              🛡️ 双止损保护已激活
            </div>
            {draggingInfo && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>原止损:</span>
                  <span style={{ fontFamily: 'monospace' }}>{draggingInfo.originalPrice.toFixed(0)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <span style={{ opacity: 0.8 }}>新止损:</span>
                  <span style={{ fontFamily: 'monospace', color: '#ffa502' }}>
                    {draggingInfo.currentPrice.toFixed(0)}
                  </span>
                </div>
                {draggingInfo.shadowPrice !== undefined && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                    <span style={{ opacity: 0.8 }}>保护线:</span>
                    <span style={{ fontFamily: 'monospace', color: '#ffa50280' }}>
                      {draggingInfo.shadowPrice.toFixed(0)}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        )

      default:
        return null
    }
  }

  // nearLine类型使用不同的样式
  if (type === 'nearLine') {
    return (
      <div style={{
        position: 'absolute',
        top: '50px',
        right: '10px',
        zIndex: 10,
        backgroundColor: 'rgba(100, 100, 100, 0.9)',
        color: '#fff',
        padding: '8px 12px',
        borderRadius: '6px',
        fontSize: '0.8rem',
      }}>
        {getStatusContent()}
      </div>
    )
  }

  return (
    <div style={{
      position: 'absolute',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      zIndex: 20,
      backgroundColor: type === 'dualStopLoss' 
        ? 'rgba(255, 165, 2, 0.95)' 
        : 'rgba(74, 158, 255, 0.95)',
      color: '#fff',
      padding: '16px 24px',
      borderRadius: '8px',
      fontSize: '0.9rem',
      textAlign: 'center',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      minWidth: '180px',
    }}>
      {getStatusContent()}
    </div>
  )
}

export default memo(StatusIndicator)

