import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CrosshairDataPanel, { CrosshairData } from '../components/CrosshairDataPanel'
import TradingToolbar from '../components/TradingToolbar'
import OrderListPanel from '../components/OrderListPanel'
import StatusIndicator from '../components/StatusIndicator'
import { DrawingMode, OrderSide, OrderStatus, TradingOrder } from '../types'

/**
 * UI组件单元测试
 * E8: 十字光标K线数据显示面板
 * E9: 工具栏UI、订单列表面板、状态提示UI
 */

describe('E8: CrosshairDataPanel', () => {
  const mockData: CrosshairData = {
    time: '2024-01-15 10:30',
    open: 25000,
    high: 25100,
    low: 24900,
    close: 25050,
    volume: 1234,
    change: 50,
    changePercent: 0.2,
  }

  it('应该显示K线数据', () => {
    render(<CrosshairDataPanel data={mockData} showLegend={false} />)

    expect(screen.getByText('2024-01-15 10:30')).toBeInTheDocument()
    expect(screen.getByText('25000')).toBeInTheDocument() // open
    expect(screen.getByText('25100')).toBeInTheDocument() // high
    expect(screen.getByText('24900')).toBeInTheDocument() // low
    expect(screen.getByText('25050')).toBeInTheDocument() // close
  })

  it('无数据时应显示提示文字', () => {
    render(<CrosshairDataPanel data={null} showLegend={false} />)

    expect(screen.getByText('移动光标查看K线数据')).toBeInTheDocument()
  })

  it('应该显示涨跌幅', () => {
    render(<CrosshairDataPanel data={mockData} showLegend={false} />)

    expect(screen.getByText(/\+50/)).toBeInTheDocument()
    expect(screen.getByText(/\+0\.20%/)).toBeInTheDocument()
  })

  it('应该显示成交量', () => {
    render(<CrosshairDataPanel data={mockData} showLegend={false} />)

    expect(screen.getByText('1,234')).toBeInTheDocument()
  })

  it('应该显示图例', () => {
    const legendItems = [
      { color: '#ff4757', label: '1分钟' },
      { color: '#4a9eff', label: '4小时' },
    ]

    render(<CrosshairDataPanel data={mockData} showLegend={true} legendItems={legendItems} />)

    expect(screen.getByText('图层')).toBeInTheDocument()
    expect(screen.getByText('1分钟')).toBeInTheDocument()
    expect(screen.getByText('4小时')).toBeInTheDocument()
  })
})

describe('E9: TradingToolbar', () => {
  const defaultProps = {
    drawingMode: DrawingMode.NONE,
    isDrawing: false,
    onEnableDrawingMode: vi.fn(),
    onDisableDrawingMode: vi.fn(),
    autoTrailingEnabled: true,
    stopLossOffset: 50,
    onSetAutoTrailingEnabled: vi.fn(),
    onSetStopLossOffset: vi.fn(),
  }

  it('应该显示画线下单按钮', () => {
    render(<TradingToolbar {...defaultProps} />)

    expect(screen.getByText('开始画线')).toBeInTheDocument()
  })

  it('画线模式下应显示取消按钮', () => {
    render(<TradingToolbar {...defaultProps} isDrawing={true} drawingMode={DrawingMode.PENDING} />)

    expect(screen.getByText('取消画线')).toBeInTheDocument()
  })

  it('点击画线按钮应触发回调', () => {
    const onEnableDrawingMode = vi.fn()
    render(<TradingToolbar {...defaultProps} onEnableDrawingMode={onEnableDrawingMode} />)

    fireEvent.click(screen.getByText('开始画线'))

    expect(onEnableDrawingMode).toHaveBeenCalledWith(DrawingMode.PENDING)
  })

  it('应该显示自动止损设置', () => {
    render(<TradingToolbar {...defaultProps} />)

    expect(screen.getByText('自动止损')).toBeInTheDocument()
    expect(screen.getByText('开启')).toBeInTheDocument()
  })

  it('自动止损开关应触发回调', () => {
    const onSetAutoTrailingEnabled = vi.fn()
    render(<TradingToolbar {...defaultProps} onSetAutoTrailingEnabled={onSetAutoTrailingEnabled} />)

    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)

    expect(onSetAutoTrailingEnabled).toHaveBeenCalledWith(false)
  })

  it('止损点数输入应触发回调', () => {
    const onSetStopLossOffset = vi.fn()
    render(<TradingToolbar {...defaultProps} onSetStopLossOffset={onSetStopLossOffset} />)

    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '100' } })

    expect(onSetStopLossOffset).toHaveBeenCalledWith(100)
  })
})

describe('E9: OrderListPanel', () => {
  const mockOrders: TradingOrder[] = [
    {
      id: 'order1',
      side: OrderSide.BUY,
      price: 25000,
      quantity: 1,
      status: OrderStatus.PENDING,
      createdTime: Date.now(),
    },
    {
      id: 'order2',
      side: OrderSide.SELL,
      price: 25100,
      quantity: 2,
      status: OrderStatus.FILLED,
      filledPrice: 25100,
      filledTime: Date.now(),
      createdTime: Date.now() - 1000,
      stopLoss: 25200,
    },
  ]

  it('无订单时不应渲染', () => {
    const { container } = render(
      <OrderListPanel orders={[]} onCancelOrder={vi.fn()} />
    )

    expect(container.firstChild).toBeNull()
  })

  it('应该显示挂单', () => {
    render(<OrderListPanel orders={mockOrders} onCancelOrder={vi.fn()} />)

    expect(screen.getByText('挂单 (1)')).toBeInTheDocument()
    expect(screen.getByText('25000')).toBeInTheDocument()
  })

  it('应该显示已成交订单', () => {
    render(<OrderListPanel orders={mockOrders} onCancelOrder={vi.fn()} />)

    expect(screen.getByText('持仓 (1)')).toBeInTheDocument()
    expect(screen.getByText('25100')).toBeInTheDocument()
  })

  it('点击撤单按钮应触发回调', () => {
    const onCancelOrder = vi.fn()
    render(<OrderListPanel orders={mockOrders} onCancelOrder={onCancelOrder} />)

    fireEvent.click(screen.getByText('撤单'))

    expect(onCancelOrder).toHaveBeenCalledWith('order1')
  })

  it('点击成交按钮应触发回调', () => {
    const onSimulateFill = vi.fn()
    render(
      <OrderListPanel 
        orders={mockOrders} 
        onCancelOrder={vi.fn()} 
        onSimulateFill={onSimulateFill}
      />
    )

    fireEvent.click(screen.getByText('成交'))

    expect(onSimulateFill).toHaveBeenCalledWith('order1')
  })

  it('应该显示止损信息', () => {
    render(<OrderListPanel orders={mockOrders} onCancelOrder={vi.fn()} />)

    expect(screen.getByText(/止损:/)).toBeInTheDocument()
    expect(screen.getByText('25200')).toBeInTheDocument()
  })
})

describe('E9: StatusIndicator', () => {
  it('不可见时不应渲染', () => {
    const { container } = render(
      <StatusIndicator type="drawing" visible={false} />
    )

    expect(container.firstChild).toBeNull()
  })

  it('画线模式应显示提示', () => {
    render(<StatusIndicator type="drawing" visible={true} drawingPrice={25000} />)

    expect(screen.getByText('画线下单模式')).toBeInTheDocument()
    expect(screen.getByText('25000')).toBeInTheDocument()
    expect(screen.getByText(/点击确认/)).toBeInTheDocument()
  })

  it('拖拽模式应显示原价和当前价', () => {
    render(
      <StatusIndicator 
        type="dragging" 
        visible={true} 
        draggingInfo={{
          originalPrice: 25000,
          currentPrice: 24900,
        }}
      />
    )

    expect(screen.getByText('拖拽移动中')).toBeInTheDocument()
    expect(screen.getByText('25000')).toBeInTheDocument()
    expect(screen.getByText('24900')).toBeInTheDocument()
  })

  it('创建止损/止盈模式应显示相关信息', () => {
    render(
      <StatusIndicator 
        type="creating" 
        visible={true} 
        creatingInfo={{
          lineType: 'stop_loss',
          entryPrice: 25000,
          currentPrice: 24900,
        }}
      />
    )

    expect(screen.getByText('创建止损线')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument() // 点差
  })

  it('靠近价格线提示应显示操作说明', () => {
    render(<StatusIndicator type="nearLine" visible={true} />)

    expect(screen.getByText(/拖拽移动/)).toBeInTheDocument()
    expect(screen.getByText(/双击删除/)).toBeInTheDocument()
  })

  it('双止损保护模式应显示特殊样式', () => {
    render(
      <StatusIndicator 
        type="dualStopLoss" 
        visible={true} 
        draggingInfo={{
          originalPrice: 24900,
          currentPrice: 24800,
          shadowPrice: 24870,
        }}
      />
    )

    expect(screen.getByText(/双止损保护已激活/)).toBeInTheDocument()
    expect(screen.getByText('24870')).toBeInTheDocument() // 影子线价格
  })
})

