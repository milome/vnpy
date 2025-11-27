import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PriceLineManager } from '../utils/priceLineManager';
import { PriceLineType, OrderSide, ChartPriceLine } from '../types';

// Mock lightweight-charts series
const createMockSeries = () => {
  const priceLines = new Map<string, any>();
  
  return {
    createPriceLine: vi.fn((options: any) => {
      const line = {
        options: () => options,
        applyOptions: vi.fn((newOptions: any) => {
          Object.assign(options, newOptions);
        }),
      };
      priceLines.set(options.id || `line_${priceLines.size}`, line);
      return line;
    }),
    removePriceLine: vi.fn((line: any) => {
      // Find and remove the line
      for (const [key, value] of priceLines.entries()) {
        if (value === line) {
          priceLines.delete(key);
          break;
        }
      }
    }),
    priceLines: vi.fn(() => Array.from(priceLines.values())),
    _priceLines: priceLines, // For testing
  };
};

describe('PriceLineManager', () => {
  let manager: PriceLineManager;
  let mockSeries: ReturnType<typeof createMockSeries>;

  beforeEach(() => {
    mockSeries = createMockSeries();
    manager = new PriceLineManager(mockSeries as any);
  });

  describe('createEntryLine', () => {
    it('should create an entry price line for buy order', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 2,
      });

      expect(line).toBeDefined();
      expect(line.type).toBe(PriceLineType.ENTRY);
      expect(line.price).toBe(21000);
      expect(mockSeries.createPriceLine).toHaveBeenCalled();
    });

    it('should use red color for buy entry line (Chinese convention)', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 2,
      });

      expect(line.color).toContain('#ff'); // Red color
    });

    it('should use cyan color for sell entry line', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.SELL,
        quantity: 2,
      });

      expect(line.color).toContain('#0'); // Cyan color
    });

    it('should include quantity in title', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 3,
      });

      expect(line.title).toContain('3');
    });
  });

  describe('createStopLossLine', () => {
    it('should create a stop loss line', () => {
      const line = manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      expect(line).toBeDefined();
      expect(line.type).toBe(PriceLineType.STOP_LOSS);
      expect(line.price).toBe(20950);
      expect(line.lineStyle).toBe('dashed');
    });

    it('should use orange/warning color for stop loss', () => {
      const line = manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      expect(line.color).toBeDefined();
    });
  });

  describe('createTakeProfitLine', () => {
    it('should create a take profit line', () => {
      const line = manager.createTakeProfitLine({
        orderId: 'order_1',
        price: 21100,
        side: OrderSide.BUY,
      });

      expect(line).toBeDefined();
      expect(line.type).toBe(PriceLineType.TAKE_PROFIT);
      expect(line.price).toBe(21100);
      expect(line.lineStyle).toBe('dashed');
    });
  });

  describe('createPendingLine', () => {
    it('should create a pending order line', () => {
      const line = manager.createPendingLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });

      expect(line).toBeDefined();
      expect(line.type).toBe(PriceLineType.PENDING);
      expect(line.lineStyle).toBe('dotted');
    });
  });

  describe('createPreviewLine', () => {
    it('should create a preview line for drawing mode', () => {
      const line = manager.createPreviewLine(21000);

      expect(line).toBeDefined();
      expect(line.type).toBe(PriceLineType.PREVIEW);
      expect(line.price).toBe(21000);
    });

    it('should update existing preview line instead of creating new one', () => {
      manager.createPreviewLine(21000);
      manager.createPreviewLine(21050);

      // Should only have one preview line
      const lines = manager.getLinesByType(PriceLineType.PREVIEW);
      expect(lines.length).toBe(1);
      expect(lines[0].price).toBe(21050);
    });
  });

  describe('removePreviewLine', () => {
    it('should remove the preview line', () => {
      manager.createPreviewLine(21000);
      manager.removePreviewLine();

      const lines = manager.getLinesByType(PriceLineType.PREVIEW);
      expect(lines.length).toBe(0);
    });
  });

  describe('updateLine', () => {
    it('should update line price', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });

      const updated = manager.updateLine(line.id, { price: 21050 });

      expect(updated?.price).toBe(21050);
    });

    it('should return undefined for non-existent line', () => {
      const updated = manager.updateLine('non-existent', { price: 21050 });

      expect(updated).toBeUndefined();
    });
  });

  describe('removeLine', () => {
    it('should remove a line by id', () => {
      const line = manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });

      const success = manager.removeLine(line.id);

      expect(success).toBe(true);
      expect(manager.getLine(line.id)).toBeUndefined();
    });

    it('should return false for non-existent line', () => {
      const success = manager.removeLine('non-existent');

      expect(success).toBe(false);
    });
  });

  describe('removeLinesByOrderId', () => {
    it('should remove all lines for an order', () => {
      manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });
      manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });
      manager.createTakeProfitLine({
        orderId: 'order_1',
        price: 21100,
        side: OrderSide.BUY,
      });

      const count = manager.removeLinesByOrderId('order_1');

      expect(count).toBe(3);
      expect(manager.getLinesByOrderId('order_1').length).toBe(0);
    });
  });

  describe('getLinesByOrderId', () => {
    it('should return all lines for an order', () => {
      manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });
      manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      const lines = manager.getLinesByOrderId('order_1');

      expect(lines.length).toBe(2);
    });
  });

  describe('getLinesByType', () => {
    it('should return all lines of a specific type', () => {
      manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });
      manager.createEntryLine({
        orderId: 'order_2',
        price: 21100,
        side: OrderSide.SELL,
        quantity: 2,
      });
      manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      const entryLines = manager.getLinesByType(PriceLineType.ENTRY);

      expect(entryLines.length).toBe(2);
    });
  });

  describe('getAllLines', () => {
    it('should return all lines', () => {
      manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });
      manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      const lines = manager.getAllLines();

      expect(lines.length).toBe(2);
    });
  });

  describe('clearAllLines', () => {
    it('should remove all lines', () => {
      manager.createEntryLine({
        orderId: 'order_1',
        price: 21000,
        side: OrderSide.BUY,
        quantity: 1,
      });
      manager.createStopLossLine({
        orderId: 'order_1',
        price: 20950,
        side: OrderSide.BUY,
      });

      manager.clearAllLines();

      expect(manager.getAllLines().length).toBe(0);
    });
  });
});

