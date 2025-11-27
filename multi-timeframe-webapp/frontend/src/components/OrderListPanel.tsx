import { memo } from 'react'
import { TradingOrder, OrderSide, OrderStatus } from '../types'

interface OrderListPanelProps {
  orders: TradingOrder[]
  onSimulateFill?: (orderId: string) => void
  onCancelOrder: (orderId: string) => void
  onClosePosition?: (orderId: string) => void
}

/**
 * 订单列表面板
 * 显示挂单和已成交订单
 */
function OrderListPanel({
  orders,
  onSimulateFill,
  onCancelOrder,
  onClosePosition,
}: OrderListPanelProps) {
  const pendingOrders = orders.filter(o => o.status === OrderStatus.PENDING)
  const filledOrders = orders.filter(o => o.status === OrderStatus.FILLED)

  if (pendingOrders.length === 0 && filledOrders.length === 0) {
    return null
  }

  return (
    <div style={{
      position: 'absolute',
      bottom: '60px',
      left: '10px',
      zIndex: 10,
      backgroundColor: 'rgba(30, 30, 30, 0.95)',
      padding: '10px',
      borderRadius: '6px',
      fontSize: '0.8rem',
      maxHeight: '300px',
      overflowY: 'auto',
      minWidth: '200px',
    }}>
      {/* 挂单列表 */}
      {pendingOrders.length > 0 && (
        <>
          <div style={{ marginBottom: '8px', fontWeight: 'bold', color: '#ffffff' }}>
            挂单 ({pendingOrders.length})
          </div>
          {pendingOrders.map(order => (
            <div key={order.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 8px',
              backgroundColor: '#2a2a2a',
              borderRadius: '4px',
              marginBottom: '4px',
              borderLeft: `3px solid ${order.side === OrderSide.BUY ? '#ff4757' : '#00d9ff'}`,
            }}>
              <span style={{ 
                color: order.side === OrderSide.BUY ? '#ff4757' : '#00d9ff',
                fontWeight: '600',
              }}>
                {order.side === OrderSide.BUY ? '买' : '卖'}
              </span>
              <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                {order.price.toFixed(0)}
              </span>
              <span style={{ color: '#888' }}>×{order.quantity}</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
                {onSimulateFill && (
                  <button
                    onClick={() => onSimulateFill(order.id)}
                    style={{
                      padding: '2px 6px',
                      backgroundColor: '#00d9ff',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.7rem',
                    }}
                    title="模拟成交"
                  >
                    成交
                  </button>
                )}
                <button
                  onClick={() => onCancelOrder(order.id)}
                  style={{
                    padding: '2px 6px',
                    backgroundColor: 'transparent',
                    color: '#ff4757',
                    border: '1px solid #ff4757',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    fontSize: '0.7rem',
                  }}
                >
                  撤单
                </button>
              </div>
            </div>
          ))}
        </>
      )}
      
      {/* 已成交订单列表 */}
      {filledOrders.length > 0 && (
        <>
          <div style={{ 
            marginTop: pendingOrders.length > 0 ? '12px' : '0',
            marginBottom: '8px', 
            fontWeight: 'bold', 
            color: '#ffffff',
          }}>
            持仓 ({filledOrders.length})
          </div>
          {filledOrders.map(order => (
            <div key={order.id} style={{
              padding: '6px 8px',
              backgroundColor: '#2a2a2a',
              borderRadius: '4px',
              marginBottom: '4px',
              borderLeft: `3px solid ${order.side === OrderSide.BUY ? '#ff4757' : '#00d9ff'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ 
                  color: order.side === OrderSide.BUY ? '#ff4757' : '#00d9ff',
                  fontWeight: '600',
                }}>
                  {order.side === OrderSide.BUY ? '多' : '空'}
                </span>
                <span style={{ color: '#fff', fontFamily: 'monospace' }}>
                  {order.filledPrice?.toFixed(0)}
                </span>
                <span style={{ color: '#888' }}>×{order.quantity}</span>
                {onClosePosition && (
                  <button
                    onClick={() => onClosePosition(order.id)}
                    style={{
                      marginLeft: 'auto',
                      padding: '2px 6px',
                      backgroundColor: 'transparent',
                      color: '#ffa502',
                      border: '1px solid #ffa502',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.7rem',
                    }}
                  >
                    平仓
                  </button>
                )}
              </div>
              {/* 止损止盈信息 */}
              <div style={{ 
                display: 'flex', 
                gap: '12px', 
                fontSize: '0.7rem',
                color: '#888',
              }}>
                {order.stopLoss && (
                  <span>
                    止损: <span style={{ color: '#ffa502' }}>{order.stopLoss.toFixed(0)}</span>
                  </span>
                )}
                {order.takeProfit && (
                  <span>
                    止盈: <span style={{ color: '#1e90ff' }}>{order.takeProfit.toFixed(0)}</span>
                  </span>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

export default memo(OrderListPanel)

