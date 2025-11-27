import { useState, useCallback, useRef } from 'react';
import { ISeriesApi, SeriesType } from 'lightweight-charts';
import { ChartPriceLine, PriceLineType } from '../types';
import { PriceLineManager } from '../utils/priceLineManager';

interface UsePriceLineDragProps {
  priceLineManager: PriceLineManager | null;
  series: ISeriesApi<SeriesType> | null;
  onPriceChange: (lineId: string, orderId: string, newPrice: number, lineType: PriceLineType) => void;
  dragThreshold?: number; // 检测阈值（像素）
}

interface UsePriceLineDragReturn {
  // 状态
  isDragging: boolean;
  draggingLine: ChartPriceLine | null;
  
  // 方法
  findNearestDraggableLine: (y: number) => ChartPriceLine | undefined;
  findNearestOrderLine: (y: number) => ChartPriceLine | undefined; // 查找所有关联订单的线（用于双击交互）
  startDrag: (line: ChartPriceLine) => void;
  updateDrag: (y: number) => void;
  endDrag: () => void;
  cancelDrag: () => void;
  getCursorStyle: (isNearLine: boolean, isDragging: boolean) => string;
}

/**
 * 价格线拖拽Hook
 * 处理价格线的拖拽交互
 */
export function usePriceLineDrag({
  priceLineManager,
  series,
  onPriceChange,
  dragThreshold = 10,
}: UsePriceLineDragProps): UsePriceLineDragReturn {
  // 拖拽状态
  const [isDragging, setIsDragging] = useState(false);
  const [draggingLine, setDraggingLine] = useState<ChartPriceLine | null>(null);
  
  // 使用ref跟踪最新状态（避免闭包问题）
  const isDraggingRef = useRef(false);
  const draggingLineRef = useRef<ChartPriceLine | null>(null);
  
  // 使用ref保存原始价格，用于取消时恢复
  const originalPriceRef = useRef<number | null>(null);
  const currentPriceRef = useRef<number | null>(null);

  /**
   * 根据价格线类型生成标题
   */
  const generateTitle = useCallback((line: ChartPriceLine, price: number): string => {
    const priceStr = price.toFixed(0);
    
    switch (line.type) {
      case PriceLineType.PENDING:
        return `挂单 @ ${priceStr}`;
      case PriceLineType.STOP_LOSS:
        return `止损 @ ${priceStr}`;
      case PriceLineType.TAKE_PROFIT:
        return `止盈 @ ${priceStr}`;
      case PriceLineType.ENTRY:
        return `入场 @ ${priceStr}`;
      default:
        return priceStr;
    }
  }, []);

  /**
   * 查找最近的可拖拽价格线
   */
  const findNearestDraggableLine = useCallback((y: number): ChartPriceLine | undefined => {
    console.log('🔍 findNearestDraggableLine - priceLineManager:', !!priceLineManager, 'series:', !!series);
    
    if (!priceLineManager || !series) {
      console.log('⚠️ Missing priceLineManager or series');
      return undefined;
    }

    const allLines = priceLineManager.getAllLines();
    const draggableLines = allLines.filter(line => line.draggable);
    console.log('🔍 All lines:', allLines.length, 'Draggable lines:', draggableLines.length);

    let nearestLine: ChartPriceLine | undefined;
    let minDistance = Infinity;

    for (const line of draggableLines) {
      const lineY = series.priceToCoordinate(line.price);
      console.log(`🔍 Line ${line.id}: price=${line.price}, y=${lineY}, mouseY=${y}, distance=${lineY !== null ? Math.abs(y - lineY) : 'N/A'}`);
      if (lineY === null) continue;

      const distance = Math.abs(y - lineY);
      if (distance < dragThreshold && distance < minDistance) {
        minDistance = distance;
        nearestLine = line;
      }
    }

    console.log('🔍 Nearest line:', nearestLine?.id, 'minDistance:', minDistance);
    return nearestLine;
  }, [priceLineManager, series, dragThreshold]);

  /**
   * 查找最近的关联订单的价格线（用于双击交互，包括入场线）
   * 与 findNearestDraggableLine 不同，这个方法查找所有有 orderId 的线，不限于 draggable
   * 
   * 优先级：当多条线距离相近时，优先返回入场线（成本线）
   */
  const findNearestOrderLine = useCallback((y: number): ChartPriceLine | undefined => {
    if (!priceLineManager || !series) {
      return undefined;
    }

    const allLines = priceLineManager.getAllLines();
    // 查找所有有 orderId 的线（包括入场线、止损线、止盈线、挂单线）
    const orderLines = allLines.filter(line => line.orderId);

    // 找出所有在阈值范围内的线
    const nearbyLines: { line: ChartPriceLine; distance: number }[] = [];

    for (const line of orderLines) {
      const lineY = series.priceToCoordinate(line.price);
      if (lineY === null) continue;

      const distance = Math.abs(y - lineY);
      if (distance < dragThreshold) {
        nearbyLines.push({ line, distance });
      }
    }

    if (nearbyLines.length === 0) {
      return undefined;
    }

    // 按距离排序
    nearbyLines.sort((a, b) => a.distance - b.distance);

    // 如果最近的线距离小于5像素，直接返回它（明确的选择）
    if (nearbyLines[0].distance < 5) {
      return nearbyLines[0].line;
    }

    // 否则，如果有入场线（成本线）在阈值范围内，优先返回入场线
    const entryLine = nearbyLines.find(item => item.line.type === PriceLineType.ENTRY);
    if (entryLine) {
      return entryLine.line;
    }

    // 否则，如果有挂单线在阈值范围内，优先返回挂单线
    const pendingLine = nearbyLines.find(item => item.line.type === PriceLineType.PENDING);
    if (pendingLine) {
      return pendingLine.line;
    }

    // 最后返回距离最近的线
    return nearbyLines[0].line;
  }, [priceLineManager, series, dragThreshold]);

  /**
   * 开始拖拽
   */
  const startDrag = useCallback((line: ChartPriceLine) => {
    setIsDragging(true);
    setDraggingLine(line);
    isDraggingRef.current = true;
    draggingLineRef.current = line;
    originalPriceRef.current = line.price;
    currentPriceRef.current = line.price;
  }, []);

  /**
   * 更新拖拽位置
   */
  const updateDrag = useCallback((y: number) => {
    const currentLine = draggingLineRef.current;
    if (!isDraggingRef.current || !currentLine || !series || !priceLineManager) return;

    const newPrice = series.coordinateToPrice(y);
    if (newPrice === null) return;

    currentPriceRef.current = newPrice;

    // 更新价格线位置
    priceLineManager.updateLine(currentLine.id, {
      price: newPrice,
      title: generateTitle(currentLine, newPrice),
    });
  }, [series, priceLineManager, generateTitle]);

  /**
   * 结束拖拽
   */
  const endDrag = useCallback(() => {
    const currentLine = draggingLineRef.current;
    if (!isDraggingRef.current || !currentLine) return;

    const finalPrice = currentPriceRef.current;
    if (finalPrice !== null && currentLine.orderId) {
      onPriceChange(currentLine.id, currentLine.orderId, finalPrice, currentLine.type);
    }

    setIsDragging(false);
    setDraggingLine(null);
    isDraggingRef.current = false;
    draggingLineRef.current = null;
    originalPriceRef.current = null;
    currentPriceRef.current = null;
  }, [onPriceChange]);

  /**
   * 取消拖拽（恢复原始价格）
   */
  const cancelDrag = useCallback(() => {
    const currentLine = draggingLineRef.current;
    if (!isDraggingRef.current || !currentLine || !priceLineManager) return;

    const originalPrice = originalPriceRef.current;
    if (originalPrice !== null) {
      // 恢复原始价格
      priceLineManager.updateLine(currentLine.id, {
        price: originalPrice,
        title: generateTitle(currentLine, originalPrice),
      });
    }

    setIsDragging(false);
    setDraggingLine(null);
    isDraggingRef.current = false;
    draggingLineRef.current = null;
    originalPriceRef.current = null;
    currentPriceRef.current = null;
  }, [priceLineManager, generateTitle]);

  /**
   * 获取鼠标样式
   */
  const getCursorStyle = useCallback((isNearLine: boolean, isDragging: boolean): string => {
    if (isDragging) return 'grabbing';
    if (isNearLine) return 'ns-resize';
    return 'default';
  }, []);

  return {
    isDragging,
    draggingLine,
    findNearestDraggableLine,
    findNearestOrderLine,
    startDrag,
    updateDrag,
    endDrag,
    cancelDrag,
    getCursorStyle,
  };
}

