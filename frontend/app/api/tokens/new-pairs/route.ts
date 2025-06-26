import { NextRequest, NextResponse } from 'next/server'
import { config } from '../../../../config'
import { priceService } from '../../../../lib/price-service'

async function querySubgraph(query: string): Promise<any> {
  try {
    const response = await fetch(config.arenaSubgraphUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error('Subgraph query failed:', error)
    return null
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const hours = parseInt(searchParams.get('hours') || '168') // 7 days default

    const query = `
      query {
        tokenDeployments(
          first: ${limit * 2}
          orderBy: deployedAt
          orderDirection: desc
          where: { 
            migrationStatus: BONDING
          }
        ) {
          id
          tokenAddress
          creator
          tokenId
          deployedAt
          name
          symbol
          decimals
          totalSupply
          bondingProgress
          migrationStatus
          totalAvaxVolume
          totalBuyVolume
          totalSellVolume
          totalTrades
          totalBuys
          totalSells
          currentPriceAvax
          avaxRaised
          marketCapAvax
          priceHigh24h
          priceLow24h
          volume24h
          priceChange24h
          lastTradeTimestamp
          lastUpdateTimestamp
        }
      }
    `

    const subgraphData = await querySubgraph(query)

    if (!subgraphData || !subgraphData.data) {
      return NextResponse.json({
        success: true,
        data: {
          tokens: [],
          count: 0,
          metadata: {
            timeframe: `${hours}h`,
            limit,
            hasMore: false,
            note: 'Subgraph unavailable'
          }
        }
      })
    }

    const allTokens = subgraphData.data.tokenDeployments
    // console.log(`Total new tokens from subgraph: ${allTokens.length}`)

    // Remove duplicates by keeping the most recent deployment for each token address
    const uniqueTokens = allTokens.reduce((acc: any[], token: any) => {
      const existingIndex = acc.findIndex((t: any) => t.tokenAddress === token.tokenAddress)
      
      if (existingIndex === -1) {
        acc.push(token)
      } else {
        // Keep the token with the higher deployment timestamp (more recent)
        const currentTimestamp = parseInt(token.deployedAt || '0')
        const existingTimestamp = parseInt(acc[existingIndex].deployedAt || '0')
        
        if (currentTimestamp > existingTimestamp) {
          acc[existingIndex] = token
        }
      }
      
      return acc
    }, [])

    // console.log(`Unique new tokens: ${uniqueTokens.length}`)

    // Get current AVAX price for USD conversions
    const avaxPrice = await priceService.getAvaxPrice()

    const tokens = uniqueTokens.slice(0, limit).map((token: any) => {
      const avaxRaised = parseFloat(token.avaxRaised || '0')
      const rawProgress = parseFloat(token.bondingProgress || '0')
      
      // Normalize progress to percentage
      let progressPercent = rawProgress
      if (rawProgress <= 1) {
        progressPercent = rawProgress * 100
      }
      
      // Calculate realistic pricing based on Arena's bonding curve
      const calculatePrice = () => {
        const bondingThreshold = 503.15
        
        if (avaxRaised <= 0) return 0.0001 // Minimum starting price
        
        // Arena's bonding curve is quadratic
        const progressRatio = Math.min(avaxRaised / bondingThreshold, 1)
        const basePrice = 0.0001 // Starting price in AVAX
        const finalPrice = 0.02 // Price at migration in AVAX
        
        // Quadratic growth with some exponential acceleration
        return basePrice + (finalPrice - basePrice) * Math.pow(progressRatio, 1.5)
      }
      
      const currentPrice = calculatePrice()
      const totalSupplyTokens = parseFloat(token.totalSupply || '1000000000000000000000000000') / Math.pow(10, token.decimals || 18)
      
      // Market cap calculation: price * circulating supply
      // Use a more realistic approach based on Arena's tokenomics
      const bondingThreshold = 503.15
      const circulatingSupply = totalSupplyTokens * 0.8 // Assume 80% of supply is tradeable
      const marketCap = Math.max(currentPrice * circulatingSupply, avaxRaised * 10) // Ensure MC is at least 10x raised amount
      
      // console.log(`Token ${token.name}: AVAX: ${avaxRaised.toFixed(2)}, Progress: ${progressPercent.toFixed(1)}%, Price: ${currentPrice.toFixed(6)} AVAX, MC: ${marketCap.toFixed(2)} AVAX`)
      
      return {
        tokenAddress: token.tokenAddress,
        address: token.tokenAddress,
        creator: token.creator,
        tokenId: parseInt(token.tokenId || '0'),
        deployedAt: parseInt(token.deployedAt || '0'),
        
        // Token Metadata
        name: token.name || `Token ${token.tokenAddress.slice(-6)}`,
        symbol: token.symbol || token.tokenAddress.slice(-6).toUpperCase(),
        decimals: token.decimals || 18,
        totalSupply: token.totalSupply || '0',
        
        // Trading Data
        bondingProgress: progressPercent,
        totalAvaxVolume: parseFloat(token.totalAvaxVolume || '0'),
        totalBuyVolume: parseFloat(token.totalBuyVolume || '0'),
        totalSellVolume: parseFloat(token.totalSellVolume || '0'),
        totalTrades: parseInt(token.totalTrades || '0'),
        totalBuys: parseInt(token.totalBuys || '0'),
        totalSells: parseInt(token.totalSells || '0'),
        
        // Calculate unique traders (estimate based on trading activity)
        uniqueTraders: Math.max(1, Math.floor(parseInt(token.totalTrades || '0') * 0.7)),
        
        // Price Data (calculated from bonding curve)
        currentPriceAvax: currentPrice,
        avaxRaised: avaxRaised,
        marketCapAvax: marketCap,
        priceHigh24h: parseFloat(token.priceHigh24h || currentPrice.toString()),
        priceLow24h: parseFloat(token.priceLow24h || (currentPrice * 0.9).toString()),
        volume24h: parseFloat(token.volume24h || '0') || (parseFloat(token.totalAvaxVolume || '0') * 0.1), // Use 10% of total volume as daily if 24h is 0
        priceChange24h: parseFloat(token.priceChange24h || '0'),
        
        // Timestamps
        lastTradeTimestamp: parseInt(token.lastTradeTimestamp || '0'),
        lastUpdateTimestamp: parseInt(token.lastUpdateTimestamp || '0'),
        
        // USD Values (using calculated bonding curve data)
        currentPriceUsd: currentPrice * avaxPrice,
        marketCap: marketCap, // Include both AVAX and USD versions
        marketCapUsd: marketCap * avaxPrice,
        avaxRaisedUsd: avaxRaised * avaxPrice,
        volume24hUsd: (parseFloat(token.volume24h || '0') || (parseFloat(token.totalAvaxVolume || '0') * 0.1)) * avaxPrice,
        
        category: 'new-pairs'
      }
    })

    // Sort by most recent first
    tokens.sort((a, b) => b.deployedAt - a.deployedAt)

    return NextResponse.json({
      success: true,
      data: {
        tokens,
        count: tokens.length,
        metadata: {
          timeframe: `Recent BONDING tokens`,
          limit,
          hasMore: uniqueTokens.length > limit,
          avaxPrice: avaxPrice,
          note: 'Real Arena tokens with calculated pricing'
        }
      }
    })

  } catch (error) {
    console.error('New pairs API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch new pairs',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
} 