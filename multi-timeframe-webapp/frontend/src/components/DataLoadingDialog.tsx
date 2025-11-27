import { useEffect } from 'react';
import './DataLoadingDialog.css';

interface DataLoadingDialogProps {
  isOpen: boolean;
  startDate: string;
  endDate: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 数据加载确认弹窗
 * 只做确认，不显示进度（真实加载状态由图表组件显示）
 */
export default function DataLoadingDialog({
  isOpen,
  startDate,
  endDate,
  onConfirm,
  onCancel,
}: DataLoadingDialogProps) {
  // ESC键关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  // 计算日期范围的天数
  const calculateDays = () => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const days = calculateDays();

  // 估算数据量
  const estimateDataSize = () => {
    // 假设每天约8小时交易时间，每小时60根1分钟K线
    const barsPerDay = 8 * 60;
    const totalBars = days * barsPerDay;
    if (totalBars > 10000) {
      return `约 ${(totalBars / 1000).toFixed(0)}K 根K线`;
    }
    return `约 ${totalBars} 根K线`;
  };

  return (
    <div className="data-loading-overlay">
      <div className="data-loading-dialog">
        <div className="data-loading-header">
          <h3>📊 确认加载数据</h3>
          <button className="close-button" onClick={onCancel} type="button">
            ×
          </button>
        </div>

        <div className="data-loading-body">
          {/* 日期范围显示 */}
          <div className="date-range-info">
            <div className="date-row">
              <span className="date-label">起始日期:</span>
              <span className="date-value">{startDate}</span>
            </div>
            <div className="date-row">
              <span className="date-label">结束日期:</span>
              <span className="date-value">{endDate}</span>
            </div>
            <div className="date-row total">
              <span className="date-label">数据范围:</span>
              <span className="date-value">{days} 天</span>
            </div>
            <div className="date-row">
              <span className="date-label">预估数据:</span>
              <span className="date-value">{estimateDataSize()}</span>
            </div>
          </div>

          {/* 加载步骤说明 */}
          <div className="loading-steps">
            <div className="step-title">加载流程：</div>
            <div className="step-item">
              <span className="step-icon">1️⃣</span>
              <span>加载1分钟K线原始数据</span>
            </div>
            <div className="step-item">
              <span className="step-icon">2️⃣</span>
              <span>按日期范围筛选数据</span>
            </div>
            <div className="step-item">
              <span className="step-icon">3️⃣</span>
              <span>聚合计算4小时K线</span>
            </div>
            <div className="step-item">
              <span className="step-icon">4️⃣</span>
              <span>渲染图表</span>
            </div>
          </div>

          {/* 提示信息 */}
          {days > 30 && (
            <div className="loading-tip warning">
              <p>⚠️ 时间范围较长（{days}天），加载可能需要一些时间</p>
            </div>
          )}
        </div>

        <div className="data-loading-footer">
          <button 
            className="cancel-button" 
            onClick={onCancel}
            type="button"
          >
            取消
          </button>
          <button 
            className="confirm-button" 
            onClick={onConfirm}
            type="button"
          >
            📥 确认加载
          </button>
        </div>
      </div>
    </div>
  );
}

