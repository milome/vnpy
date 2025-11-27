import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDualStopLoss } from '../hooks/useDualStopLoss';
import { PriceLineType, OrderSide, ChartPriceLine } from '../types';

// Mock PriceLineManager
const createMockPriceLineManager = () => ({
  createPriceLine: vi.fn((config) => config),
  updateLine: vi.fn(),
  removeLine: vi.fn(() => true),
  getLine: vi.fn(),
  getLinesByOrderId: vi.fn(() => []),
});

describe('useDualStopLoss', () => {
  let mockPriceLineManager: ReturnType<typeof createMockPriceLineManager>;

  beforeEach(() => {
    mockPriceLineManager = createMockPriceLineManager();
  });

  describe('startDragStopLoss', () => {
    it('should create a shadow stop loss line when dragging starts', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      // Should create shadow line
      expect(mockPriceLineManager.createPriceLine).toHaveBeenCalledWith(
        expect.objectContaining({
          price: 20950,
          type: PriceLineType.STOP_LOSS,
          lineStyle: 'dotted', // Shadow line uses dotted style
        })
      );

      expect(result.current.isDraggingStopLoss).toBe(true);
      expect(result.current.originalPrice).toBe(20950);
      expect(result.current.shadowLineId).toBeDefined();
    });

    it('should store original stop loss price', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      expect(result.current.originalPrice).toBe(20950);
    });
  });

  describe('updateDragStopLoss', () => {
    it('should update the main stop loss line position during drag', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      act(() => {
        result.current.updateDragStopLoss(21000); // New price
      });

      expect(result.current.currentPrice).toBe(21000);
    });

    it('should update shadow line with lag (slower movement)', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const lagFactor = 0.3;
      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
          lagFactor,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      // Move to 21000 (delta = 50)
      act(() => {
        result.current.updateDragStopLoss(21000);
      });

      // Shadow should move by delta * lagFactor = 50 * 0.3 = 15
      // New shadow price = 20950 + 15 = 20965
      expect(result.current.shadowPrice).toBe(20965);
      expect(result.current.originalPrice).toBe(20950); // Original price unchanged
      
      // updateLine should be called for shadow line
      expect(mockPriceLineManager.updateLine).toHaveBeenCalled();
    });
  });

  describe('confirmDragStopLoss', () => {
    it('should remove shadow line when drag is confirmed', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.createPriceLine.mockReturnValue({
        id: 'shadow_sl_1',
        price: 20950,
      });

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      act(() => {
        result.current.updateDragStopLoss(21000);
      });

      act(() => {
        result.current.confirmDragStopLoss();
      });

      // Shadow line should be removed
      expect(mockPriceLineManager.removeLine).toHaveBeenCalledWith('shadow_sl_1');
      expect(result.current.isDraggingStopLoss).toBe(false);
      expect(result.current.shadowLineId).toBeNull();
    });

    it('should return the new stop loss price on confirm', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      act(() => {
        result.current.updateDragStopLoss(21000);
      });

      let confirmedPrice: number | null = null;
      act(() => {
        confirmedPrice = result.current.confirmDragStopLoss();
      });

      expect(confirmedPrice).toBe(21000);
    });
  });

  describe('cancelDragStopLoss', () => {
    it('should restore original stop loss price when cancelled', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      mockPriceLineManager.createPriceLine.mockReturnValue({
        id: 'shadow_sl_1',
        price: 20950,
      });

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      act(() => {
        result.current.updateDragStopLoss(21000);
      });

      act(() => {
        result.current.cancelDragStopLoss();
      });

      // Should remove shadow line
      expect(mockPriceLineManager.removeLine).toHaveBeenCalledWith('shadow_sl_1');
      
      // Should restore main line to original price
      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('sl_1', {
        price: 20950,
        title: expect.stringContaining('20950'),
      });

      expect(result.current.isDraggingStopLoss).toBe(false);
    });
  });

  describe('shadow line appearance', () => {
    it('should create shadow line with semi-transparent color', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      expect(mockPriceLineManager.createPriceLine).toHaveBeenCalledWith(
        expect.objectContaining({
          color: expect.stringContaining('80'), // Semi-transparent (ends with 80)
          lineStyle: 'dotted',
          title: expect.stringContaining('保护止损'),
        })
      );
    });
  });

  describe('protection status', () => {
    it('should indicate protection is active during drag', () => {
      const originalStopLossLine: ChartPriceLine = {
        id: 'sl_1',
        orderId: 'order_1',
        type: PriceLineType.STOP_LOSS,
        price: 20950,
        color: '#ffa502',
        lineWidth: 1,
        lineStyle: 'dashed',
        draggable: true,
      };

      const { result } = renderHook(() =>
        useDualStopLoss({
          priceLineManager: mockPriceLineManager as any,
        })
      );

      expect(result.current.isProtectionActive).toBe(false);

      act(() => {
        result.current.startDragStopLoss(originalStopLossLine, OrderSide.BUY);
      });

      expect(result.current.isProtectionActive).toBe(true);

      act(() => {
        result.current.confirmDragStopLoss();
      });

      expect(result.current.isProtectionActive).toBe(false);
    });
  });
});

