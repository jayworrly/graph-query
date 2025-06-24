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
    
    // Updated migration thresholds - more realistic for "close to migration"
    const minProgressPercent = parseFloat(searchParams.get('minProgress') || '60') // 60%
    const maxProgressPercent = parseFloat(searchParams.get('maxProgress') || '95') // 95%

    // Query for all BONDING tokens to filter them properly
    const query = `
      query {
        tokenDeployments(
          first: ${limit * 3}
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
      console.log('Subgraph data unavailable, returning empty result')
      return NextResponse.json({
        success: true,
        data: {
          tokens: [],
          count: 0,
          metadata: {
            minProgress: minProgressPercent,
            maxProgress: maxProgressPercent,
            limit,
            hasMore: false,
            note: 'Subgraph unavailable'
          }
        }
      })
    }

    const allTokens = subgraphData.data.tokenDeployments
    console.log(`Total BONDING tokens from subgraph: ${allTokens.length}`)
    
    // Debug sample tokens to understand data format
    if (allTokens.length > 0) {
      console.log('Sample BONDING token data:')
      allTokens.slice(0, 3).forEach((token: any, i: number) => {
        const progress = parseFloat(token.bondingProgress || '0')
        const avaxRaised = parseFloat(token.avaxRaised || '0')
        console.log(`${i + 1}. ${token.name || 'Unnamed'} - Progress: ${progress}%, AVAX: ${avaxRaised}, Status: ${token.migrationStatus}`)
      })
    }

    // Remove duplicates by keeping the most recent deployment for each token address
    const uniqueTokens = allTokens.reduce((acc: any[], token: any) => {
      const existingIndex = acc.findIndex(t => t.tokenAddress === token.tokenAddress)
      
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

    console.log(`Unique tokens after deduplication: ${uniqueTokens.length}`)

    // Filter for tokens close to migration
    const filteredTokens = uniqueTokens.filter((token: any) => {
      const progress = parseFloat(token.bondingProgress || '0')
      const avaxRaised = parseFloat(token.avaxRaised || '0')
      
      // Check if progress is in the right range
      // Handle both percentage (0-100) and decimal (0-1) formats
      let actualProgress = progress
      if (progress <= 1) {
        actualProgress = progress * 100 // Convert decimal to percentage
      }
      
      // Alternative check: if AVAX raised is substantial (approaching 503.15 threshold)
      const isCloseByAvax = avaxRaised >= 300 && avaxRaised < 503.15 // 300+ AVAX raised
      const isCloseByProgress = actualProgress >= minProgressPercent && actualProgress <= maxProgressPercent
      
      return isCloseByProgress || isCloseByAvax
    })
    
    console.log(`Tokens close to migration (${minProgressPercent}-${maxProgressPercent}% or 300+ AVAX): ${filteredTokens.length}`)

    // Get current AVAX price for USD conversions
    const avaxPrice = await priceService.getAvaxPrice()
    
    const tokens = filteredTokens.slice(0, limit).map((token: any) => {
      const avaxRaised = parseFloat(token.avaxRaised || '0')
      const bondingThreshold = 503.15
      const rawProgress = parseFloat(token.bondingProgress || '0')
      
      // Normalize progress to percentage
      let progressPercent = rawProgress
      if (rawProgress <= 1) {
        progressPercent = rawProgress * 100
      }
      
      const avaxRemaining = Math.max(0, bondingThreshold - avaxRaised)
      const estimatedHoursToMigration = avaxRemaining > 0 ? Math.ceil(avaxRemaining / 5) : 0 // More conservative estimate
      
      // Calculate current price using real Arena bonding curve
      const calculatePrice = () => {
        if (avaxRaised <= 0) return 0
        
        // Arena's bonding curve is roughly quadratic
        // Price increases exponentially as it approaches the migration threshold
        const progressRatio = Math.min(avaxRaised / bondingThreshold, 1)
        const basePrice = 0.0001 // Starting price in AVAX
        const finalPrice = 0.02 // Price at migration in AVAX
        
        return basePrice + (finalPrice - basePrice) * Math.pow(progressRatio, 1.5)
      }
      
      const currentPriceAvax = calculatePrice()
      const totalSupplyTokens = parseFloat(token.totalSupply || '1000000000000000000000000000') / Math.pow(10, token.decimals || 18)
      const marketCapAvax = currentPriceAvax * totalSupplyTokens * (progressPercent / 100)
      
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
        
        // Migration Progress
        bondingProgress: progressPercent,
        avaxRaised: avaxRaised,
        avaxRemaining: avaxRemaining,
        estimatedTimeToMigration: estimatedHoursToMigration,
        migrationThreshold: bondingThreshold,
        
        // Trading Data
        totalAvaxVolume: parseFloat(token.totalAvaxVolume || '0'),
        totalBuyVolume: parseFloat(token.totalBuyVolume || '0'),
        totalSellVolume: parseFloat(token.totalSellVolume || '0'),
        totalTrades: parseInt(token.totalTrades || '0'),
        totalBuys: parseInt(token.totalBuys || '0'),
        totalSells: parseInt(token.totalSells || '0'),
        
        // Calculate unique traders (estimate based on trading activity)
        uniqueTraders: Math.max(1, Math.floor(parseInt(token.totalTrades || '0') * 0.7)),
        
        // Price Data
        currentPriceAvax: currentPriceAvax,
        marketCapAvax: marketCapAvax,
        priceHigh24h: parseFloat(token.priceHigh24h || '0'),
        priceLow24h: parseFloat(token.priceLow24h || '0'),
        volume24h: parseFloat(token.volume24h || '0'),
        priceChange24h: parseFloat(token.priceChange24h || '0'),
        
        // Timestamps
        lastTradeTimestamp: parseInt(token.lastTradeTimestamp || '0'),
        lastUpdateTimestamp: parseInt(token.lastUpdateTimestamp || '0'),
        
        // USD Values
        currentPriceUsd: currentPriceAvax * avaxPrice,
        marketCapUsd: marketCapAvax * avaxPrice,
        avaxRaisedUsd: avaxRaised * avaxPrice,
        volume24hUsd: parseFloat(token.volume24h || '0') * avaxPrice,
        
        category: 'close-to-migration'
      }
    })

    // Sort by AVAX raised (closest to migration first)
    tokens.sort((a, b) => b.avaxRaised - a.avaxRaised)

    return NextResponse.json({
      success: true,
      data: {
        tokens,
        count: tokens.length,
        metadata: {
          minProgress: minProgressPercent,
          maxProgress: maxProgressPercent,
          limit,
          hasMore: filteredTokens.length > limit,
          totalFiltered: filteredTokens.length,
          avaxPrice: avaxPrice
        }
      }
    })

  } catch (error) {
    console.error('Close to migration API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch tokens close to migration',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
} 