import { useState } from 'react'
import { TradingOrder, OrderSide, OrderStatus } from '../types'
import './TradingPanel.css'

interface TradingPanelProps {
  orders: TradingOrder[]
  onPlaceOrder: (order: Omit<TradingOrder, 'id' | 'status' | 'createdTime'>) => void
  onCancelOrder: (orderId: string) => void
  currentPrice: number
}

export default function TradingPanel({
  orders,
  onPlaceOrder,
  onCancelOrder,
  currentPrice,
}: TradingPanelProps) {
  const [orderSide, setOrderSide] = useState<OrderSide>(OrderSide.BUY)
  const [orderPrice, setOrderPrice] = useState<string>(currentPrice.toFixed(0))
  const [orderQuantity, setOrderQuantity] = useState<string>('1')
  const [stopLossOffset, setStopLossOffset] = useState<string>('50')

  const handlePlaceOrder = () => {
    const price = parseFloat(orderPrice)
    const quantity = parseInt(orderQuantity)
    const offset = parseFloat(stopLossOffset)

    if (isNaN(price) || isNaN(quantity) || quantity <= 0) {
      alert('请输入有效的价格和手数')
      return
    }

    // Calculate stop loss based on order side
    const stopLoss = orderSide === OrderSide.BUY
      ? price - offset
      : price + offset

    onPlaceOrder({
      side: orderSide,
      price,
      quantity,
      stopLoss: isNaN(offset) ? undefined : stopLoss,
    })

    // Reset form
    setOrderPrice(currentPrice.toFixed(0))
    setOrderQuantity('1')
  }

  const pendingOrders = orders.filter(o => o.status === OrderStatus.PENDING)
  const filledOrders = orders.filter(o => o.status === OrderStatus.FILLED)

  return (
    <div className="trading-panel">
      <div className="trading-header">
        <h3>交易面板</h3>
        <div className="current-price">
          当前价格: <span>{currentPrice.toFixed(0)}</span>
        </div>
      </div>

      <div className="order-form">
        <div className="form-group">
          <label>方向:</label>
          <div className="order-side-buttons">
            <button
              className={`side-button buy ${orderSide === OrderSide.BUY ? 'active' : ''}`}
              onClick={() => setOrderSide(OrderSide.BUY)}
            >
              买入
            </button>
            <button
              className={`side-button sell ${orderSide === OrderSide.SELL ? 'active' : ''}`}
              onClick={() => setOrderSide(OrderSide.SELL)}
            >
              卖出
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>价格:</label>
          <input
            type="number"
            value={orderPrice}
            onChange={(e) => setOrderPrice(e.target.value)}
            placeholder="输入价格"
          />
        </div>

        <div className="form-group">
          <label>手数:</label>
          <input
            type="number"
            value={orderQuantity}
            onChange={(e) => setOrderQuantity(e.target.value)}
            placeholder="输入手数"
            min="1"
          />
        </div>

        <div className="form-group">
          <label>止损点数:</label>
          <input
            type="number"
            value={stopLossOffset}
            onChange={(e) => setStopLossOffset(e.target.value)}
            placeholder="止损点数"
          />
        </div>

        <button className="place-order-button" onClick={handlePlaceOrder}>
          {orderSide === OrderSide.BUY ? '买入下单' : '卖出下单'}
        </button>
      </div>

      <div className="orders-section">
        <h4>挂单 ({pendingOrders.length})</h4>
        <div className="orders-list">
          {pendingOrders.length === 0 ? (
            <div className="no-orders">暂无挂单</div>
          ) : (
            pendingOrders.map(order => (
              <div key={order.id} className={`order-item pending ${order.side}`}>
                <div className="order-info">
                  <span className="order-side-label">
                    {order.side === OrderSide.BUY ? '买入' : '卖出'}
                  </span>
                  <span className="order-price">{order.price.toFixed(0)}</span>
                  <span className="order-quantity">{order.quantity}手</span>
                </div>
                {order.stopLoss && (
                  <div className="order-stoploss">
                    止损: {order.stopLoss.toFixed(0)}
                  </div>
                )}
                <button
                  className="cancel-button"
                  onClick={() => onCancelOrder(order.id)}
                >
                  撤单
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="orders-section">
        <h4>成交 ({filledOrders.length})</h4>
        <div className="orders-list">
          {filledOrders.length === 0 ? (
            <div className="no-orders">暂无成交</div>
          ) : (
            filledOrders.map(order => (
              <div key={order.id} className={`order-item filled ${order.side}`}>
                <div className="order-info">
                  <span className="order-side-label">
                    {order.side === OrderSide.BUY ? '买入' : '卖出'}
                  </span>
                  <span className="order-price">{order.filledPrice?.toFixed(0)}</span>
                  <span className="order-quantity">{order.quantity}手</span>
                </div>
                {order.stopLoss && (
                  <div className="order-stoploss">
                    止损: {order.stopLoss.toFixed(0)}
                  </div>
                )}
                <div className="order-time">
                  {new Date(order.filledTime!).toLocaleString('zh-CN')}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
