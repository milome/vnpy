import { useState, useEffect, useCallback } from 'react';
import { OrderSide } from '../types';
import './OrderDialog.css';

interface OrderDialogProps {
  isOpen: boolean;
  price: number;
  onConfirm: (options: {
    side: OrderSide;
    quantity: number;
    stopLoss?: number;
    takeProfit?: number;
  }) => void;
  onCancel: () => void;
}

/**
 * 下单确认弹窗组件
 * 用于确认画线下单的参数
 */
export default function OrderDialog({
  isOpen,
  price,
  onConfirm,
  onCancel,
}: OrderDialogProps) {
  const [side, setSide] = useState<OrderSide>(OrderSide.BUY);
  const [quantity, setQuantity] = useState(1);
  const [stopLossOffset, setStopLossOffset] = useState(50);
  const [takeProfitOffset, setTakeProfitOffset] = useState(100);
  const [useStopLoss, setUseStopLoss] = useState(true);
  const [useTakeProfit, setUseTakeProfit] = useState(false);

  // 计算止损和止盈价格
  const stopLossPrice = side === OrderSide.BUY
    ? price - stopLossOffset
    : price + stopLossOffset;

  const takeProfitPrice = side === OrderSide.BUY
    ? price + takeProfitOffset
    : price - takeProfitOffset;

  const handleConfirm = useCallback(() => {
    console.log('🔧 OrderDialog - handleConfirm called', { side, quantity, stopLossPrice, takeProfitPrice });
    onConfirm({
      side,
      quantity,
      stopLoss: useStopLoss ? stopLossPrice : undefined,
      takeProfit: useTakeProfit ? takeProfitPrice : undefined,
    });
  }, [side, quantity, useStopLoss, stopLossPrice, useTakeProfit, takeProfitPrice, onConfirm]);

  // 键盘事件处理
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        handleConfirm();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel, handleConfirm]);

  if (!isOpen) return null;

  return (
    <div className="order-dialog-overlay" onClick={onCancel}>
      <div className="order-dialog" onClick={e => e.stopPropagation()}>
        <div className="order-dialog-header">
          <h3>确认下单</h3>
          <button type="button" className="close-button" onClick={onCancel}>×</button>
        </div>

        <div className="order-dialog-body">
          {/* 价格显示 */}
          <div className="order-price-display">
            <span className="label">下单价格</span>
            <span className="price">{price.toFixed(0)}</span>
          </div>

          {/* 买卖方向 */}
          <div className="form-group">
            <label>交易方向</label>
            <div className="side-buttons">
              <button
                type="button"
                className={`side-button buy ${side === OrderSide.BUY ? 'active' : ''}`}
                onClick={() => setSide(OrderSide.BUY)}
              >
                买入
              </button>
              <button
                type="button"
                className={`side-button sell ${side === OrderSide.SELL ? 'active' : ''}`}
                onClick={() => setSide(OrderSide.SELL)}
              >
                卖出
              </button>
            </div>
          </div>

          {/* 数量 */}
          <div className="form-group">
            <label>手数</label>
            <div className="quantity-input">
              <button
                type="button"
                className="quantity-button"
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
              >
                -
              </button>
              <input
                type="number"
                value={quantity}
                onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                min="1"
              />
              <button
                type="button"
                className="quantity-button"
                onClick={() => setQuantity(quantity + 1)}
              >
                +
              </button>
            </div>
          </div>

          {/* 止损设置 */}
          <div className="form-group">
            <div className="checkbox-row">
              <label>
                <input
                  type="checkbox"
                  checked={useStopLoss}
                  onChange={e => setUseStopLoss(e.target.checked)}
                />
                设置止损
              </label>
            </div>
            {useStopLoss && (
              <div className="offset-input">
                <span className="offset-label">止损点数</span>
                <input
                  type="number"
                  value={stopLossOffset}
                  onChange={e => setStopLossOffset(Math.max(1, parseInt(e.target.value) || 1))}
                  min="1"
                />
                <span className="calculated-price">= {stopLossPrice.toFixed(0)}</span>
              </div>
            )}
          </div>

          {/* 止盈设置 */}
          <div className="form-group">
            <div className="checkbox-row">
              <label>
                <input
                  type="checkbox"
                  checked={useTakeProfit}
                  onChange={e => {
                    console.log('🔧 Take profit checkbox changed:', e.target.checked)
                    setUseTakeProfit(e.target.checked)
                  }}
                />
                设置止盈
              </label>
            </div>
            {useTakeProfit && (
              <div className="offset-input">
                <span className="offset-label">止盈点数</span>
                <input
                  type="number"
                  value={takeProfitOffset}
                  onChange={e => setTakeProfitOffset(Math.max(1, parseInt(e.target.value) || 1))}
                  min="1"
                />
                <span className="calculated-price">= {takeProfitPrice.toFixed(0)}</span>
              </div>
            )}
          </div>

          {/* 订单摘要 */}
          <div className="order-summary">
            <div className="summary-row">
              <span>方向</span>
              <span className={side === OrderSide.BUY ? 'buy' : 'sell'}>
                {side === OrderSide.BUY ? '买入' : '卖出'}
              </span>
            </div>
            <div className="summary-row">
              <span>价格</span>
              <span>{price.toFixed(0)}</span>
            </div>
            <div className="summary-row">
              <span>数量</span>
              <span>{quantity} 手</span>
            </div>
            {useStopLoss && (
              <div className="summary-row">
                <span>止损</span>
                <span className="stop-loss">{stopLossPrice.toFixed(0)} (-{stopLossOffset})</span>
              </div>
            )}
            {useTakeProfit && (
              <div className="summary-row">
                <span>止盈</span>
                <span className="take-profit">{takeProfitPrice.toFixed(0)} (+{takeProfitOffset})</span>
              </div>
            )}
          </div>
        </div>

        <div className="order-dialog-footer">
          <button type="button" className="cancel-button" onClick={onCancel}>
            取消
          </button>
          <button
            type="button"
            className={`confirm-button ${side === OrderSide.BUY ? 'buy' : 'sell'}`}
            onClick={handleConfirm}
          >
            确认{side === OrderSide.BUY ? '买入' : '卖出'}
          </button>
        </div>
      </div>
    </div>
  );
}

