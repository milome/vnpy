import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePriceLineDrag } from '../hooks/usePriceLineDrag';
import { PriceLineType, OrderSide } from '../types';

// Mock PriceLineManager
const createMockPriceLineManager = () => ({
  getAllLines: vi.fn(() => []),
  getLine: vi.fn(),
  updateLine: vi.fn(),
  getLinesByOrderId: vi.fn(() => []),
});

// Mock series for coordinate conversion
const createMockSeries = () => ({
  coordinateToPrice: vi.fn((y: number) => 21000 + (300 - y)), // Simple conversion
  priceToCoordinate: vi.fn((price: number) => 300 - (price - 21000)),
});

describe('usePriceLineDrag', () => {
  let mockPriceLineManager: ReturnType<typeof createMockPriceLineManager>;
  let mockSeries: ReturnType<typeof createMockSeries>;
  let onPriceChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockPriceLineManager = createMockPriceLineManager();
    mockSeries = createMockSeries();
    onPriceChange = vi.fn();
  });

  describe('drag detection', () => {
    it('should detect when mouse is near a draggable price line', () => {
      mockPriceLineManager.getAllLines.mockReturnValue([
        {
          id: 'line_1',
          orderId: 'order_1',
          type: PriceLineType.PENDING,
          price: 21000,
          color: '#ff4757',
          lineWidth: 1,
          lineStyle: 'dotted',
          draggable: true,
        },
      ]);

      mockSeries.priceToCoordinate.mockReturnValue(100);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
          dragThreshold: 10,
        })
      );

      // Mouse at y=105, line at y=100, within threshold
      const nearLine = result.current.findNearestDraggableLine(105);
      expect(nearLine).toBeDefined();
      expect(nearLine?.id).toBe('line_1');
    });

    it('should not detect non-draggable lines', () => {
      mockPriceLineManager.getAllLines.mockReturnValue([
        {
          id: 'line_1',
          orderId: 'order_1',
          type: PriceLineType.ENTRY,
          price: 21000,
          color: '#ff4757',
          lineWidth: 2,
          lineStyle: 'solid',
          draggable: false,
        },
      ]);

      mockSeries.priceToCoordinate.mockReturnValue(100);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
          dragThreshold: 10,
        })
      );

      const nearLine = result.current.findNearestDraggableLine(105);
      expect(nearLine).toBeUndefined();
    });

    it('should not detect lines outside threshold', () => {
      mockPriceLineManager.getAllLines.mockReturnValue([
        {
          id: 'line_1',
          orderId: 'order_1',
          type: PriceLineType.PENDING,
          price: 21000,
          color: '#ff4757',
          lineWidth: 1,
          lineStyle: 'dotted',
          draggable: true,
        },
      ]);

      mockSeries.priceToCoordinate.mockReturnValue(100);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
          dragThreshold: 10,
        })
      );

      // Mouse at y=120, line at y=100, outside threshold
      const nearLine = result.current.findNearestDraggableLine(120);
      expect(nearLine).toBeUndefined();
    });
  });

  describe('drag state', () => {
    it('should start dragging when startDrag is called', () => {
      const line = {
        id: 'line_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted' as const,
        draggable: true,
      };

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
        })
      );

      act(() => {
        result.current.startDrag(line);
      });

      expect(result.current.isDragging).toBe(true);
      expect(result.current.draggingLine).toEqual(line);
    });

    it('should update line price during drag', () => {
      const line = {
        id: 'line_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted' as const,
        draggable: true,
      };

      mockSeries.coordinateToPrice.mockReturnValue(21050);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
        })
      );

      act(() => {
        result.current.startDrag(line);
        result.current.updateDrag(150); // y coordinate
      });

      expect(mockPriceLineManager.updateLine).toHaveBeenCalledWith('line_1', {
        price: 21050,
        title: expect.any(String),
      });
    });

    it('should call onPriceChange when drag ends', () => {
      const line = {
        id: 'line_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted' as const,
        draggable: true,
      };

      mockSeries.coordinateToPrice.mockReturnValue(21050);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
        })
      );

      act(() => {
        result.current.startDrag(line);
        result.current.updateDrag(150);
        result.current.endDrag();
      });

      expect(result.current.isDragging).toBe(false);
      expect(onPriceChange).toHaveBeenCalledWith('line_1', 'order_1', 21050, PriceLineType.PENDING);
    });

    it('should cancel drag without calling onPriceChange', () => {
      const line = {
        id: 'line_1',
        orderId: 'order_1',
        type: PriceLineType.PENDING,
        price: 21000,
        color: '#ff4757',
        lineWidth: 1,
        lineStyle: 'dotted' as const,
        draggable: true,
      };

      mockSeries.coordinateToPrice.mockReturnValue(21050);
      mockPriceLineManager.getLine.mockReturnValue(line);

      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
        })
      );

      act(() => {
        result.current.startDrag(line);
        result.current.updateDrag(150);
        result.current.cancelDrag();
      });

      expect(result.current.isDragging).toBe(false);
      expect(onPriceChange).not.toHaveBeenCalled();
      // Should restore original price
      expect(mockPriceLineManager.updateLine).toHaveBeenLastCalledWith('line_1', {
        price: 21000,
        title: expect.any(String),
      });
    });
  });

  describe('cursor style', () => {
    it('should return appropriate cursor style', () => {
      const { result } = renderHook(() =>
        usePriceLineDrag({
          priceLineManager: mockPriceLineManager as any,
          series: mockSeries as any,
          onPriceChange,
        })
      );

      expect(result.current.getCursorStyle(false, false)).toBe('default');
      expect(result.current.getCursorStyle(true, false)).toBe('ns-resize');
      expect(result.current.getCursorStyle(true, true)).toBe('grabbing');
    });
  });
});

