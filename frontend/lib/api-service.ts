export interface TokenData {
  id: number
  name: string
  symbol: string
  address: string
  price: number
  change24h: number
  volume24h: number
  marketCap: number
  holders: number
  image: string
  tokenId: string
  tokenSupply: string
  creatorAddress: string
  pairAddress: string
  lpDeployed: boolean
  lpPercentage: number
  salePercentage: number
  creatorFeeBasisPoints: number
  curveScaler: string
  launched?: Date
  liquidity?: number
  migrationProgress?: number
  timeToMigration?: string
  migrationDate?: string
  newAddress?: string
  
  // New fields from v0.0.4 subgraph
  totalTrades?: number
  totalBuys?: number
  totalSells?: number
  uniqueTraders?: number
  priceHigh24h?: number
  priceLow24h?: number
  avaxRaised?: number
  migrationThreshold?: number
  lastTradeTimestamp?: number
}

export class ApiService {
  static async getNewPairs(limit: number = 50): Promise<TokenData[]> {
    try {
      const response = await fetch(`/api/tokens/new-pairs?limit=${limit}`)
      const result = await response.json()
      
      if (!result.success || !result.data?.tokens) {
        console.warn('Failed to fetch new pairs from API')
        return []
      }

      // Convert API response to TokenData format using real blockchain data
      const tokens = result.data.tokens.map((token: any, index: number) => {
        return {
          id: index + 1,
          name: token.name || 'Unknown Token', // Real name from blockchain
          symbol: token.symbol || 'UNKNOWN', // Real symbol from blockchain
          address: token.tokenAddress || token.address,
          price: parseFloat(token.currentPriceAvax || '0'),
          change24h: parseFloat(token.priceChange24h || '0'),
          volume24h: parseFloat(token.volume24h || '0'),
          marketCap: parseFloat(token.marketCapAvax || '0'),
          holders: parseInt(token.holders || '0'),
          image: this.getTokenFallbackImage(token.symbol || 'UNKNOWN'),
          tokenId: token.tokenId?.toString() || '0',
          tokenSupply: token.totalSupply || '1000000000000000000000000000',
          creatorAddress: token.creator || '0x0000000000000000000000000000000000000000',
          pairAddress: token.pairAddress || '0x0000000000000000000000000000000000000000',
          lpDeployed: token.migrationStatus === 'MIGRATED',
          lpPercentage: token.migrationStatus === 'MIGRATED' ? 100 : 0,
          salePercentage: 100,
          creatorFeeBasisPoints: 0,
          curveScaler: '1000000000000000000',
          launched: new Date(parseInt(token.deployedAt || '0') * 1000),
          migrationProgress: parseFloat(token.bondingProgress || '0'),
          
          // New fields from enhanced subgraph
          totalTrades: parseInt(token.totalTrades || '0'),
          totalBuys: parseInt(token.totalBuys || '0'),
          totalSells: parseInt(token.totalSells || '0'),
          uniqueTraders: parseInt(token.uniqueTraders || '0'),
          priceHigh24h: parseFloat(token.priceHigh24h || '0'),
          priceLow24h: parseFloat(token.priceLow24h || '0'),
          avaxRaised: parseFloat(token.avaxRaised || '0'),
          migrationThreshold: parseFloat(token.migrationThreshold || '503.15'),
          lastTradeTimestamp: parseInt(token.lastTradeTimestamp || '0')
        }
      })

      return tokens
    } catch (error) {
      console.error('Error fetching new pairs:', error)
      return []
    }
  }

  static async getCloseToMigration(limit: number = 20): Promise<TokenData[]> {
    try {
      const response = await fetch(`/api/tokens/close-to-migration?limit=${limit}`)
      const result = await response.json()
      
      if (!result.success || !result.data?.tokens) {
        console.warn('Failed to fetch close to migration tokens from API')
        return []
      }

      // Convert API response to TokenData format using real blockchain data
      const tokens = result.data.tokens.map((token: any, index: number) => {
        const progress = parseFloat(token.bondingProgress || '0')
        const threshold = parseFloat(token.migrationThreshold || '503.15')
        const remaining = threshold - parseFloat(token.avaxRaised || '0')
        const estimatedHours = remaining > 0 ? Math.ceil(remaining / 10) : 0 // Rough estimate
        
        return {
          id: index + 1,
          name: token.name || 'Unknown Token',
          symbol: token.symbol || 'UNKNOWN',
          address: token.tokenAddress || token.address,
          price: parseFloat(token.currentPriceAvax || '0'),
          change24h: parseFloat(token.priceChange24h || '0'),
          volume24h: parseFloat(token.volume24h || '0'),
          marketCap: parseFloat(token.marketCapAvax || '0'),
          holders: parseInt(token.holders || '0'),
          image: this.getTokenFallbackImage(token.symbol || 'UNKNOWN'),
          tokenId: token.tokenId?.toString() || '0',
          tokenSupply: token.totalSupply || '1000000000000000000000000000',
          creatorAddress: token.creator || '0x0000000000000000000000000000000000000000',
          pairAddress: token.pairAddress || '0x0000000000000000000000000000000000000000',
          lpDeployed: false,
          lpPercentage: 0,
          salePercentage: 100,
          creatorFeeBasisPoints: 0,
          curveScaler: '1000000000000000000',
          launched: new Date(parseInt(token.deployedAt || '0') * 1000),
          migrationProgress: progress,
          timeToMigration: estimatedHours > 0 ? `${estimatedHours}h` : 'Soon',
          
          // New fields from enhanced subgraph
          totalTrades: parseInt(token.totalTrades || '0'),
          totalBuys: parseInt(token.totalBuys || '0'),
          totalSells: parseInt(token.totalSells || '0'),
          uniqueTraders: parseInt(token.uniqueTraders || '0'),
          priceHigh24h: parseFloat(token.priceHigh24h || '0'),
          priceLow24h: parseFloat(token.priceLow24h || '0'),
          avaxRaised: parseFloat(token.avaxRaised || '0'),
          migrationThreshold: parseFloat(token.migrationThreshold || '503.15'),
          lastTradeTimestamp: parseInt(token.lastTradeTimestamp || '0')
        }
      })

      return tokens
    } catch (error) {
      console.error('Error fetching close to migration tokens:', error)
      return []
    }
  }

  static async getMigratedTokens(limit: number = 20): Promise<TokenData[]> {
    try {
      const response = await fetch(`/api/tokens/migrated?limit=${limit}`)
      const result = await response.json()
      
      if (!result.success || !result.data?.tokens) {
        console.warn('Failed to fetch migrated tokens from API')
        return []
      }

      // Convert API response to TokenData format using real blockchain data
      const tokens = result.data.tokens.map((token: any, index: number) => {
        return {
          id: index + 1,
          name: token.name || 'Unknown Token',
          symbol: token.symbol || 'UNKNOWN',
          address: token.tokenAddress || token.address,
          price: parseFloat(token.currentPriceAvax || '0'),
          change24h: parseFloat(token.priceChange24h || '0'),
          volume24h: parseFloat(token.volume24h || '0'),
          marketCap: parseFloat(token.marketCapAvax || '0'),
          holders: parseInt(token.holders || '0'),
          image: this.getTokenFallbackImage(token.symbol || 'UNKNOWN'),
          tokenId: token.tokenId?.toString() || '0',
          tokenSupply: token.totalSupply || '1000000000000000000000000000',
          creatorAddress: token.creator || '0x0000000000000000000000000000000000000000',
          pairAddress: token.pairAddress || '0x0000000000000000000000000000000000000000',
          lpDeployed: true,
          lpPercentage: 100,
          salePercentage: 100,
          creatorFeeBasisPoints: 0,
          curveScaler: '1000000000000000000',
          launched: new Date(parseInt(token.deployedAt || '0') * 1000),
          migrationProgress: 100,
          liquidity: parseFloat(token.liquidityAvax || '0'),
          migrationDate: token.migrationDate || 'Recently',
          
          // New fields from enhanced subgraph
          totalTrades: parseInt(token.totalTrades || '0'),
          totalBuys: parseInt(token.totalBuys || '0'),
          totalSells: parseInt(token.totalSells || '0'),
          uniqueTraders: parseInt(token.uniqueTraders || '0'),
          priceHigh24h: parseFloat(token.priceHigh24h || '0'),
          priceLow24h: parseFloat(token.priceLow24h || '0'),
          avaxRaised: parseFloat(token.avaxRaised || '0'),
          migrationThreshold: parseFloat(token.migrationThreshold || '503.15'),
          lastTradeTimestamp: parseInt(token.lastTradeTimestamp || '0')
        }
      })

      return tokens
    } catch (error) {
      console.error('Error fetching migrated tokens:', error)
      return []
    }
  }

  private static getTokenFallbackImage(symbol: string): string {
    // Generate a simple fallback image URL based on symbol
    const colors = ['FF6B6B', '4ECDC4', '45B7D1', '96CEB4', 'FFEAA7', 'DDA0DD', 'F0A3A3', '6C5CE7']
    const hash = symbol.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    const color = colors[Math.abs(hash) % colors.length]
    return `https://via.placeholder.com/32x32/${color}/FFFFFF?text=${symbol.charAt(0)}`
  }
} 