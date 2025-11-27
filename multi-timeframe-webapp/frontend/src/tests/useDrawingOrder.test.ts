import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDrawingOrder } from '../hooks/useDrawingOrder';
import { DrawingMode, OrderSide } from '../types';

// Mock PriceLineManager
const mockPriceLineManager = {
  createPreviewLine: vi.fn(() => ({ id: 'preview_1', price: 21000 })),
  removePreviewLine: vi.fn(),
  createPendingLine: vi.fn(() => ({ id: 'pending_1', price: 21000 })),
  createEntryLine: vi.fn(() => ({ id: 'entry_1', price: 21000 })),
  createStopLossLine: vi.fn(() => ({ id: 'sl_1', price: 20950 })),
  createTakeProfitLine: vi.fn(() => ({ id: 'tp_1', price: 21050 })),
  removeLinesByOrderId: vi.fn(),
  clearAllLines: vi.fn(),
};

// Mock OrderService
const mockOrderService = {
  createOrder: vi.fn(() => ({
    id: 'order_1',
    side: OrderSide.BUY,
    price: 21000,
    quantity: 1,
    status: 'pending',
    createdTime: Date.now(),
  })),
  cancelOrder: vi.fn(() => true),
  fillOrder: vi.fn(),
  updateOrder: vi.fn(),
  getPendingOrders: vi.fn(() => []),
  getFilledOrders: vi.fn(() => []),
  onOrderCreated: vi.fn(),
  onOrderFilled: vi.fn(),
  onOrderCancelled: vi.fn(),
};

describe('useDrawingOrder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('drawing mode management', () => {
    it('should start with NONE drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      expect(result.current.drawingMode).toBe(DrawingMode.NONE);
    });

    it('should enable order line drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
      });

      expect(result.current.drawingMode).toBe(DrawingMode.ORDER_LINE);
      expect(result.current.isDrawing).toBe(true);
    });

    it('should disable drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.disableDrawingMode();
      });

      expect(result.current.drawingMode).toBe(DrawingMode.NONE);
      expect(result.current.isDrawing).toBe(false);
      expect(mockPriceLineManager.removePreviewLine).toHaveBeenCalled();
    });
  });

  describe('preview line', () => {
    it('should update preview line when mouse moves in drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
      });

      expect(mockPriceLineManager.createPreviewLine).toHaveBeenCalledWith(21000);
    });

    it('should not update preview line when not in drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.handleCrosshairMove(21000);
      });

      expect(mockPriceLineManager.createPreviewLine).not.toHaveBeenCalled();
    });

    it('should store current preview price', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21050);
      });

      expect(result.current.previewPrice).toBe(21050);
    });
  });

  describe('order dialog', () => {
    it('should open order dialog when clicking in drawing mode', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      expect(result.current.isOrderDialogOpen).toBe(true);
      expect(result.current.pendingOrderPrice).toBe(21000);
    });

    it('should close order dialog', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      act(() => {
        result.current.closeOrderDialog();
      });

      expect(result.current.isOrderDialogOpen).toBe(false);
    });
  });

  describe('order creation', () => {
    it('should create order and price lines when confirmed', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 2,
          stopLoss: 20950,
          takeProfit: 21100,
        });
      });

      expect(mockOrderService.createOrder).toHaveBeenCalledWith(expect.objectContaining({
        side: OrderSide.BUY,
        price: 21000,
        quantity: 2,
        stopLoss: 20950,
        takeProfit: 21100,
      }));

      expect(mockPriceLineManager.createPendingLine).toHaveBeenCalled();
      expect(mockPriceLineManager.createStopLossLine).toHaveBeenCalled();
      expect(mockPriceLineManager.createTakeProfitLine).toHaveBeenCalled();
    });

    it('should close dialog and disable drawing mode after order confirmation', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 1,
        });
      });

      expect(result.current.isOrderDialogOpen).toBe(false);
      expect(result.current.drawingMode).toBe(DrawingMode.NONE);
    });

    it('should not create take profit line if not specified', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 1,
          stopLoss: 20950,
        });
      });

      expect(mockPriceLineManager.createTakeProfitLine).not.toHaveBeenCalled();
    });
  });

  describe('order cancellation', () => {
    it('should cancel order and remove price lines', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      // First create an order
      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
        result.current.handleCrosshairMove(21000);
        result.current.handleClick();
      });

      act(() => {
        result.current.confirmOrder({
          side: OrderSide.BUY,
          quantity: 1,
        });
      });

      // Then cancel it
      act(() => {
        result.current.cancelPendingOrder('order_1');
      });

      expect(mockOrderService.cancelOrder).toHaveBeenCalledWith('order_1');
      expect(mockPriceLineManager.removeLinesByOrderId).toHaveBeenCalledWith('order_1');
    });
  });

  describe('keyboard shortcuts', () => {
    it('should provide escape handler to cancel drawing', () => {
      const { result } = renderHook(() =>
        useDrawingOrder({
          priceLineManager: mockPriceLineManager as any,
          orderService: mockOrderService as any,
        })
      );

      act(() => {
        result.current.enableDrawingMode(DrawingMode.ORDER_LINE);
      });

      act(() => {
        result.current.handleEscape();
      });

      expect(result.current.drawingMode).toBe(DrawingMode.NONE);
    });
  });
});

