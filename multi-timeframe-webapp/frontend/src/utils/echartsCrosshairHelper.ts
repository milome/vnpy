import type { EChartsType } from 'echarts'

/**
 * ECharts 十字光标辅助工具
 * 用于从鼠标事件获取图表上的价格和时间
 */

export interface CrosshairPosition {
  price: number
  time: number
  pixelX: number
  pixelY: number
}

/**
 * 从像素坐标获取图表数据坐标
 * @param chart ECharts实例
 * @param pixelX 像素X坐标
 * @param pixelY 像素Y坐标
 * @returns 数据坐标（时间和价格），如果超出图表范围返回null
 */
export function getDataFromPixel(
  chart: EChartsType,
  pixelX: number,
  pixelY: number
): CrosshairPosition | null {
  try {
    // 将像素坐标转换为数据坐标
    // 对于K线图，x轴是时间，y轴是价格
    const dataPoint = chart.convertFromPixel({ seriesIndex: 0 }, [pixelX, pixelY])
    
    if (!dataPoint || dataPoint.length < 2) {
      return null
    }

    const time = dataPoint[0]
    const price = dataPoint[1]

    // 检查是否在有效范围内
    if (typeof time !== 'number' || typeof price !== 'number' || isNaN(time) || isNaN(price)) {
      return null
    }

    return {
      time,
      price,
      pixelX,
      pixelY,
    }
  } catch (error) {
    console.warn('Failed to convert pixel to data:', error)
    return null
  }
}

/**
 * 从鼠标事件获取图表数据坐标
 * @param chart ECharts实例
 * @param event 鼠标事件
 * @returns 数据坐标，如果超出图表范围返回null
 */
export function getDataFromMouseEvent(
  chart: EChartsType,
  event: MouseEvent
): CrosshairPosition | null {
  // 获取图表容器的边界
  const chartDom = chart.getDom()
  if (!chartDom) return null

  const rect = chartDom.getBoundingClientRect()
  
  // 计算相对于图表容器的坐标
  const pixelX = event.clientX - rect.left
  const pixelY = event.clientY - rect.top

  return getDataFromPixel(chart, pixelX, pixelY)
}

/**
 * 从ECharts事件参数获取价格
 * ECharts的事件回调中已经包含了数据信息
 * @param params ECharts事件参数
 * @returns 价格，如果无法获取返回null
 */
export function getPriceFromEChartsEvent(params: any): number | null {
  if (!params) return null

  // 如果是K线数据，value是数组 [open, close, low, high]
  if (params.data && Array.isArray(params.data)) {
    // 对于K线图，取收盘价作为当前价格
    const [, open, close] = params.data
    if (typeof close === 'number') {
      return close
    }
  }

  // 如果有value属性
  if (typeof params.value === 'number') {
    return params.value
  }

  return null
}

/**
 * 获取图表Y轴范围
 * @param chart ECharts实例
 * @returns Y轴范围 {min, max}，如果无法获取返回null
 */
export function getYAxisRange(chart: EChartsType): { min: number; max: number } | null {
  try {
    const option = chart.getOption()
    if (!option || !option.yAxis) return null

    const yAxis = Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis
    if (!yAxis) return null

    // 获取当前的min和max（可能是自动计算的）
    const model = (chart as any).getModel()
    if (!model) return null

    const yAxisModel = model.getComponent('yAxis', 0)
    if (!yAxisModel) return null

    const axis = yAxisModel.axis
    if (!axis) return null

    const extent = axis.scale?.getExtent?.()
    if (!extent || extent.length < 2) return null

    return {
      min: extent[0],
      max: extent[1],
    }
  } catch (error) {
    console.warn('Failed to get Y axis range:', error)
    return null
  }
}

/**
 * 将价格转换为像素Y坐标
 * @param chart ECharts实例
 * @param price 价格
 * @returns 像素Y坐标，如果无法转换返回null
 */
export function priceToPixelY(chart: EChartsType, price: number): number | null {
  try {
    // 方法1: 使用grid坐标系
    const pixel = chart.convertToPixel('grid', [0, price])
    if (pixel && pixel.length >= 2 && typeof pixel[1] === 'number' && !isNaN(pixel[1])) {
      return pixel[1]
    }

    // 方法2: 手动计算
    const yAxisRange = getYAxisRange(chart)
    if (!yAxisRange) return null

    const option = chart.getOption()
    if (!option || !option.grid) return null

    const grid = Array.isArray(option.grid) ? option.grid[0] : option.grid
    if (!grid) return null

    const chartHeight = chart.getHeight()
    
    const parseValue = (value: string | number | undefined, total: number, defaultValue: number): number => {
      if (value === undefined) return defaultValue
      if (typeof value === 'number') return value
      if (typeof value === 'string' && value.endsWith('%')) {
        return (parseFloat(value) / 100) * total
      }
      return parseFloat(value as string) || defaultValue
    }

    const top = parseValue(grid.top as string | number, chartHeight, 60)
    const bottom = parseValue(grid.bottom as string | number, chartHeight, 100)
    
    const plotTop = top
    const plotBottom = chartHeight - bottom
    const plotHeight = plotBottom - plotTop

    // 价格转换为像素Y（注意Y轴方向）
    const ratio = (yAxisRange.max - price) / (yAxisRange.max - yAxisRange.min)
    const pixelY = plotTop + ratio * plotHeight
    
    return pixelY
  } catch (error) {
    console.warn('Failed to convert price to pixel:', error)
    return null
  }
}

/**
 * 将像素Y坐标转换为价格
 * @param chart ECharts实例
 * @param pixelY 像素Y坐标
 * @returns 价格，如果无法转换返回null
 */
export function pixelYToPrice(chart: EChartsType, pixelY: number): number | null {
  try {
    // 方法1: 使用 grid 坐标系转换
    const data = chart.convertFromPixel('grid', [0, pixelY])
    console.log('🔍 convertFromPixel result:', data)
    if (data && data.length >= 2 && typeof data[1] === 'number' && !isNaN(data[1])) {
      return data[1]
    }

    // 方法2: 手动计算（基于Y轴范围）
    const yAxisRange = getYAxisRange(chart)
    console.log('🔍 Y axis range:', yAxisRange)
    if (!yAxisRange) {
      console.warn('pixelYToPrice: Cannot get Y axis range')
      return null
    }

    const option = chart.getOption()
    if (!option || !option.grid) {
      console.warn('pixelYToPrice: No grid option')
      return null
    }

    const grid = Array.isArray(option.grid) ? option.grid[0] : option.grid
    if (!grid) {
      console.warn('pixelYToPrice: No grid')
      return null
    }

    const chartHeight = chart.getHeight()
    const chartWidth = chart.getWidth()
    console.log('🔍 Chart size:', chartWidth, 'x', chartHeight)
    
    // 解析grid配置
    const parseValue = (value: string | number | undefined, total: number, defaultValue: number): number => {
      if (value === undefined) return defaultValue
      if (typeof value === 'number') return value
      if (typeof value === 'string' && value.endsWith('%')) {
        return (parseFloat(value) / 100) * total
      }
      return parseFloat(value as string) || defaultValue
    }

    const top = parseValue(grid.top as string | number, chartHeight, 60)
    const bottom = parseValue(grid.bottom as string | number, chartHeight, 60)
    
    const plotTop = top
    const plotBottom = chartHeight - bottom
    const plotHeight = plotBottom - plotTop
    
    console.log('🔍 Plot area: top=', plotTop, 'bottom=', plotBottom, 'height=', plotHeight)
    console.log('🔍 pixelY=', pixelY)

    // 检查是否在绘图区域内
    if (pixelY < plotTop || pixelY > plotBottom) {
      console.warn('pixelYToPrice: pixelY out of plot area')
      return null
    }

    // 像素Y坐标转换为价格（注意Y轴是从上到下，但价格是从低到高）
    const ratio = (pixelY - plotTop) / plotHeight
    const price = yAxisRange.max - ratio * (yAxisRange.max - yAxisRange.min)
    
    console.log('🔍 Calculated price:', price)
    return price
  } catch (error) {
    console.warn('Failed to convert pixel to price:', error)
    return null
  }
}

/**
 * 创建十字光标移动处理器
 * 返回一个可以绑定到图表的事件处理函数
 * @param chart ECharts实例
 * @param onMove 十字光标移动回调
 * @returns 事件处理函数
 */
export function createCrosshairMoveHandler(
  chart: EChartsType,
  onMove: (position: CrosshairPosition | null) => void
): (event: MouseEvent) => void {
  return (event: MouseEvent) => {
    const position = getDataFromMouseEvent(chart, event)
    onMove(position)
  }
}

/**
 * 检查点是否在图表绑制区域内
 * @param chart ECharts实例
 * @param pixelX 像素X坐标
 * @param pixelY 像素Y坐标
 * @returns 是否在绘制区域内
 */
export function isPointInPlotArea(
  chart: EChartsType,
  pixelX: number,
  pixelY: number
): boolean {
  try {
    const option = chart.getOption()
    if (!option || !option.grid) return false

    const grid = Array.isArray(option.grid) ? option.grid[0] : option.grid
    if (!grid) return false

    const chartDom = chart.getDom()
    if (!chartDom) return false

    const width = chart.getWidth()
    const height = chart.getHeight()

    // 解析grid配置（可能是百分比或像素值）
    const parseValue = (value: string | number | undefined, total: number, defaultValue: number): number => {
      if (value === undefined) return defaultValue
      if (typeof value === 'number') return value
      if (value.endsWith('%')) {
        return (parseFloat(value) / 100) * total
      }
      return parseFloat(value) || defaultValue
    }

    const left = parseValue(grid.left as string | number, width, 80)
    const right = parseValue(grid.right as string | number, width, 80)
    const top = parseValue(grid.top as string | number, height, 60)
    const bottom = parseValue(grid.bottom as string | number, height, 60)

    const plotLeft = left
    const plotRight = width - right
    const plotTop = top
    const plotBottom = height - bottom

    return pixelX >= plotLeft && pixelX <= plotRight && pixelY >= plotTop && pixelY <= plotBottom
  } catch (error) {
    console.warn('Failed to check if point is in plot area:', error)
    return false
  }
}

