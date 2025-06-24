interface AvaxPriceResponse {
  price: number
  lastUpdated: number
}

class PriceService {
  private static instance: PriceService
  private avaxPrice: number = 0
  private lastUpdated: number = 0
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  private constructor() {}

  static getInstance(): PriceService {
    if (!PriceService.instance) {
      PriceService.instance = new PriceService()
    }
    return PriceService.instance
  }

  async getAvaxPrice(): Promise<number> {
    const now = Date.now()
    
    // Return cached price if still valid
    if (this.avaxPrice > 0 && (now - this.lastUpdated) < this.CACHE_DURATION) {
      return this.avaxPrice
    }

    try {
      // Try DexScreener first (most reliable for AVAX)
      const avaxPrice = await this.fetchFromDexScreener()
      if (avaxPrice > 0) {
        this.avaxPrice = avaxPrice
        this.lastUpdated = now
        return avaxPrice
      }

      // Fallback to CoinGecko
      const coinGeckoPrice = await this.fetchFromCoinGecko()
      if (coinGeckoPrice > 0) {
        this.avaxPrice = coinGeckoPrice
        this.lastUpdated = now
        return coinGeckoPrice
      }

      // Last resort - return cached value or default
      return this.avaxPrice > 0 ? this.avaxPrice : 35 // Default fallback price
    } catch (error) {
      console.error('Error fetching AVAX price:', error)
      return this.avaxPrice > 0 ? this.avaxPrice : 35
    }
  }

  private async fetchFromDexScreener(): Promise<number> {
    try {
      // DexScreener for WAVAX-USDC pair on Avalanche
      const response = await fetch('https://api.dexscreener.com/latest/dex/tokens/0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7')
      
      if (!response.ok) {
        throw new Error(`DexScreener API error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data?.pairs && data.pairs.length > 0) {
        // Find the pair with highest liquidity
        const bestPair = data.pairs
          .filter((pair: any) => pair.baseToken.symbol === 'WAVAX' && pair.quoteToken.symbol === 'USDC')
          .sort((a: any, b: any) => parseFloat(b.liquidity?.usd || '0') - parseFloat(a.liquidity?.usd || '0'))[0]
        
        if (bestPair && bestPair.priceUsd) {
          const price = parseFloat(bestPair.priceUsd)
          console.log(`AVAX price from DexScreener: $${price}`)
          return price
        }
      }
      
      return 0
    } catch (error) {
      console.error('DexScreener fetch error:', error)
      return 0
    }
  }

  private async fetchFromCoinGecko(): Promise<number> {
    try {
      const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd')
      
      if (!response.ok) {
        throw new Error(`CoinGecko API error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data && data['avalanche-2'] && data['avalanche-2'].usd) {
        const price = data['avalanche-2'].usd
        console.log(`AVAX price from CoinGecko: $${price}`)
        return price
      }
      
      return 0
    } catch (error) {
      console.error('CoinGecko fetch error:', error)
      return 0
    }
  }

  // Utility function to convert AVAX to USD
  async convertAvaxToUsd(avaxAmount: number): Promise<number> {
    const avaxPrice = await this.getAvaxPrice()
    return avaxAmount * avaxPrice
  }

  // Format currency values
  formatUsd(amount: number): string {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}K`
    } else {
      return `$${amount.toFixed(2)}`
    }
  }

  formatAvax(amount: number): string {
    if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K AVAX`
    } else {
      return `${amount.toFixed(2)} AVAX`
    }
  }
}

export const priceService = PriceService.getInstance()
export { PriceService } 