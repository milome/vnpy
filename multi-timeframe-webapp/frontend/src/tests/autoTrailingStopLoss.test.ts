import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoTrailingStopLoss } from '../hooks/useAutoTrailingStopLoss';
import { PriceLineType, OrderSide, ChartPriceLine } from '../types';

// Mock PriceLineManager
const createMockPriceLineManager = () => ({
  getLinesByOrderId: vi.fn(() => []),
  updateLine: vi.fn(),
  createStopLossLine: vi.fn(() => ({ id: 'sl_new', price: 20950 })),
  getLine: vi.fn(),
});

// Mock OrderService
const createMockOrderService = () => ({
  getOrder: vi.fn(),
  updateOrder: vi.fn(),
});

describe('useAutoTrailingStopLoss', () => {
  let mockPriceLineManager: ReturnType<typeof createMockPriceLineManager>;
  let mockOrderService: ReturnType<typeof createMockOrderService>;

  beforeEach(() => {
    mockPriceLineManager = createMockPriceLineManager();
    mockOrderService = createMockOrderService();
  });

  describe('updateStopLossOnPendingDrag', () => {
    it('should update stop loss line when pending line is dragged (BUY order)', () => {
      const pendingLine: ChartPriceLine = {
        id: 'pending_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted',
        draggable: true,
      };

      const stopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950, // 50 points below
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.getLinesByOrderId.mockReturnValue([pendingLine, stopLossLine]);
      mockOrderService.getOrder.mockReturnValue({
        id: 'order_1',
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        stopLoss: 20950,
      });

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      // Drag pending line to new price
      act(() => {
        result.current.updateStopLossOnPendingDrag('order_1', 21100); // New pending price
      });

      // Stop loss should be updated to 21100 - 50 = 21050
      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('sl_1', {
        price: 21050,
        title: expect.stringContaining('21050'),
      });
    });

    it('should update stop loss line when pending line is dragged (SELL order)', () => {
      const pendingLine: ChartPriceLine = {
        id: 'pending_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#00d9ff',
        lineWidth: 1,
        lineStyle: 'dotted',
        draggable: true,
      };

      const stopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 21050, // 50 points above for SELL
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.getLinesByOrderId.mockReturnValue([pendingLine, stopLossLine]);
      mockOrderService.getOrder.mockReturnValue({
        id: 'order_1',
        side: OrderSide.SELL,
        price: 21000,
        quantity: 1,
        stopLoss: 21050,
      });

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      // Drag pending line to new price
      act(() => {
        result.current.updateStopLossOnPendingDrag('order_1', 20900); // New pending price
      });

      // Stop loss should be updated to 20900 + 50 = 20950
      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('sl_1', {
        price: 20950,
        title: expect.stringContaining('20950'),
      });
    });

    it('should create stop loss line if it does not exist', () => {
      const pendingLine: ChartPriceLine = {
        id: 'pending_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted',
        draggable: true,
      };

      // Only pending line, no stop loss
      mockPriceLineManager.getLinesByOrderId.mockReturnValue([pendingLine]);
      mockOrderService.getOrder.mockReturnValue({
        id: 'order_1',
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        // No stopLoss set
      });

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      act(() => {
        result.current.updateStopLossOnPendingDrag('order_1', 21100);
      });

      // Should create new stop loss line
      expect(mockPriceLineManager.createStopLossLine).toHaveBeenCalledWith({
        orderId: 'order_1',
        price: 21050, // 21100 - 50
        side: OrderSide.BUY,
      });
    });

    it('should not update if order does not exist', () => {
      mockPriceLineManager.getLinesByOrderId.mockReturnValue([]);
      mockOrderService.getOrder.mockReturnValue(undefined);

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      act(() => {
        result.current.updateStopLossOnPendingDrag('non_existent', 21100);
      });

      expect(mockPriceLineManager.updateLine).not.toHaveBeenCalled();
      expect(mockPriceLineManager.createStopLossLine).not.toHaveBeenCalled();
    });
  });

  describe('stopLossOffset management', () => {
    it('should allow setting custom stop loss offset', () => {
      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      expect(result.current.stopLossOffset).toBe(50);

      act(() => {
        result.current.setStopLossOffset(100);
      });

      expect(result.current.stopLossOffset).toBe(100);
    });

    it('should use updated offset when calculating stop loss', () => {
      const pendingLine: ChartPriceLine = {
        id: 'pending_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted',
        draggable: true,
      };

      const stopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.getLinesByOrderId.mockReturnValue([pendingLine, stopLossLine]);
      mockOrderService.getOrder.mockReturnValue({
        id: 'order_1',
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        stopLoss: 20950,
      });

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      // Change offset to 100
      act(() => {
        result.current.setStopLossOffset(100);
      });

      // Drag pending line
      act(() => {
        result.current.updateStopLossOnPendingDrag('order_1', 21200);
      });

      // Stop loss should be 21200 - 100 = 21100
      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('sl_1', {
        price: 21100,
        title: expect.stringContaining('21100'),
      });
    });
  });

  describe('auto trailing toggle', () => {
    it('should allow enabling/disabling auto trailing', () => {
      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      expect(result.current.autoTrailingEnabled).toBe(true);

      act(() => {
        result.current.setAutoTrailingEnabled(false);
      });

      expect(result.current.autoTrailingEnabled).toBe(false);
    });

    it('should not update stop loss when auto trailing is disabled', () => {
      const pendingLine: ChartPriceLine = {
        id: 'pending_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted',
        draggable: true,
      };

      const stopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.getLinesByOrderId.mockReturnValue([pendingLine, stopLossLine]);
      mockOrderService.getOrder.mockReturnValue({
        id: 'order_1',
        side: OrderSide.BUY,
        price: 21000,
        quantity: 1,
        stopLoss: 20950,
      });

      const { result } = renderHook(() =>
        useAutoTrailingStopLoss({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
          defaultStopLossOffset: 50,
        })
      );

      // Disable auto trailing
      act(() => {
        result.current.setAutoTrailingEnabled(false);
      });

      // Try to update
      act(() => {
        result.current.updateStopLossOnPendingDrag('order_1', 21100);
      });

      // Should not update
      expect(mockPriceLineManager.updateLine).not.toHaveBeenCalled();
    });
  });
});

