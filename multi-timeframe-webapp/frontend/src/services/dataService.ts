import Papa from 'papaparse'
import { KLineData, ChartKLineData, Timeframe, CSVParseResult } from '../types'
import { convertArrayToChartData, sortByTimestamp, validateKLineData } from '../utils/dataTransform'

/**
 * CSV Data Service
 * Back to loading pre-generated CSV files for better performance and accuracy
 */
class CSVDataService {
  private cache: Map<Timeframe, ChartKLineData[]> = new Map()
  private loading: Map<Timeframe, Promise<ChartKLineData[]>> = new Map()
  private dataLimit = 1000 // Default to 1000 candles for fast loading

  /**
   * Set the maximum number of candles to load for performance optimization
   */
  setDataLimit(limit: number): void {
    this.dataLimit = limit
    // Clear cache when limit changes
    this.cache.clear()
  }

  /**
   * Get current data limit
   */
  getDataLimit(): number {
    return this.dataLimit
  }

  /**
   * Get the CSV file path for a given timeframe
   */
  private getFilePath(timeframe: Timeframe): string {
    // In dev mode, Vite serves files from public directory at root
    const fileName = `${timeframe}_MHImain_HKFE.csv`
    return `/data/${fileName}`
  }

  /**
   * Load CSV data from file
   */
  private async loadCSV(timeframe: Timeframe): Promise<CSVParseResult> {
    return new Promise((resolve) => {
      const filePath = this.getFilePath(timeframe)

      fetch(filePath)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Failed to fetch ${filePath}: ${response.statusText}`)
          }
          return response.text()
        })
        .then((csvText) => {
          Papa.parse<KLineData>(csvText, {
            header: true,
            dynamicTyping: true,
            skipEmptyLines: true,
            transformHeader: (header) => header.trim(),
            complete: (results) => {
              // Validate and filter out invalid data
              const validData = results.data.filter((row) => validateKLineData(row))

              if (validData.length === 0) {
                console.warn(`No valid data found in CSV for ${timeframe}`)
                resolve({
                  data: [],
                  error: new Error(`No valid data found in CSV for ${timeframe}`),
                })
                return
              }

              // For faster loading, only take the most recent N candles (or all if limit is -1)
              // This provides sufficient data for visualization while improving performance
              const recentData = this.dataLimit === -1 ? validData : validData.slice(-this.dataLimit)

              const limitText = this.dataLimit === -1 ? 'all' : this.dataLimit.toString()
              console.log(`📊 Loaded ${recentData.length} ${timeframe} candles from CSV (${limitText === 'all' ? 'all' : `last ${limitText}`} from ${validData.length} total)`)
              resolve({
                data: recentData,
              })
            },
            error: (error) => {
              resolve({
                data: [],
                error: new Error(`CSV parse error: ${error.message}`),
              })
            },
          })
        })
        .catch((error) => {
          resolve({
            data: [],
            error: error as Error,
          })
        })
    })
  }

  /**
   * Get data for a specific timeframe
   * Uses cache if available, otherwise loads from CSV
   */
  async getData(timeframe: Timeframe, forceReload = false): Promise<ChartKLineData[]> {
    // Return cached data if available and not forcing reload
    if (!forceReload && this.cache.has(timeframe)) {
      return this.cache.get(timeframe)!
    }

    // If already loading, return the existing promise
    if (this.loading.has(timeframe)) {
      return this.loading.get(timeframe)!
    }

    // Start loading
    const loadPromise = this.loadAndCache(timeframe)
    this.loading.set(timeframe, loadPromise)

    try {
      const data = await loadPromise
      return data
    } finally {
      this.loading.delete(timeframe)
    }
  }

  /**
   * Load data and cache it
   */
  private async loadAndCache(timeframe: Timeframe): Promise<ChartKLineData[]> {
    const result = await this.loadCSV(timeframe)

    if (result.error) {
      console.error(`Error loading ${timeframe} data:`, result.error)
      throw result.error
    }

    // Convert to chart data format and sort by timestamp
    const chartData = convertArrayToChartData(result.data)
    const sortedData = sortByTimestamp(chartData)

    // Cache the data
    this.cache.set(timeframe, sortedData)

    return sortedData
  }

  /**
   * Preload multiple timeframes
   */
  async preloadTimeframes(timeframes: Timeframe[]): Promise<void> {
    await Promise.all(timeframes.map((tf) => this.getData(tf)))
  }

  /**
   * Get data for multiple timeframes
   */
  async getMultipleTimeframes(
    timeframes: Timeframe[]
  ): Promise<Map<Timeframe, ChartKLineData[]>> {
    const results = await Promise.all(
      timeframes.map(async (tf) => {
        const data = await this.getData(tf)
        return [tf, data] as [Timeframe, ChartKLineData[]]
      })
    )

    return new Map(results)
  }

  /**
   * Clear cache for a specific timeframe or all
   */
  clearCache(timeframe?: Timeframe): void {
    if (timeframe) {
      this.cache.delete(timeframe)
    } else {
      this.cache.clear()
    }
  }

  /**
   * Get cache status
   */
  getCacheStatus(): {
    cached: Timeframe[]
    loading: Timeframe[]
  } {
    return {
      cached: Array.from(this.cache.keys()),
      loading: Array.from(this.loading.keys()),
    }
  }

  /**
   * Get cached data size (approximate)
   */
  getCacheSize(): number {
    let totalSize = 0
    this.cache.forEach((data) => {
      totalSize += data.length
    })
    return totalSize
  }

  /**
   * Debug function: Get first few candles of a timeframe to verify boundaries
   */
  async debugTimeframeBoundaries(timeframe: Timeframe, count = 10): Promise<void> {
    const data = await this.getData(timeframe)
    if (data.length === 0) {
      console.log(`❌ No data for ${timeframe}`)
      return
    }

    console.log(`🔍 First ${count} ${timeframe} candles:`)
    const sample = data.slice(0, count)

    sample.forEach((candle, index) => {
      const date = new Date(candle.timestamp)
      const timeStr = date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        weekday: 'short'
      })

      const direction = candle.close > candle.open ? '📈 阳线' : '📉 阴线'
      console.log(`  ${index + 1}. ${timeStr} | ${direction} | O:${candle.open} H:${candle.high} L:${candle.low} C:${candle.close}`)
    })
  }
}

// Export singleton instance
export const dataService = new CSVDataService()
export default dataService
