import { NextRequest, NextResponse } from 'next/server'
import { config } from '../../../../config'

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
    const minProgress = parseFloat(searchParams.get('minProgress') || '0.5') // 50% minimum

    const query = `
      query {
        tokenDeployments(
          first: ${limit}
          orderBy: bondingProgress
          orderDirection: desc
          where: { 
            migrationStatus: CLOSE_TO_MIGRATION
            bondingProgress_gte: "${minProgress * 100}"
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
      // Fallback to demo data if subgraph is unavailable
      return NextResponse.json({
        success: true,
        data: {
          tokens: [],
          count: 0,
          metadata: {
            minProgress,
            limit,
            hasMore: false
          }
        }
      })
    }

    const tokens = subgraphData.data.tokenDeployments.map((token: any) => {
      // Calculate estimated time to migration based on 503.15 AVAX threshold
      const avaxRaised = parseFloat(token.avaxRaised || '0')
      const bondingThreshold = 503.15
      const progressPercent = parseFloat(token.bondingProgress || '0')
      const avaxRemaining = bondingThreshold - avaxRaised
      const estimatedHoursToMigration = avaxRemaining > 0 ? (avaxRemaining / 10) : 0 // Rough estimate: 10 AVAX per hour
      
      return {
        address: token.tokenAddress,
        creator: token.creator,
        tokenId: parseInt(token.tokenId),
        deployedAt: parseInt(token.deployedAt),
        
        // Token Metadata (real from blockchain)
        name: token.name || `Token ${token.tokenAddress.slice(-6)}`,
        symbol: token.symbol || token.tokenAddress.slice(-6).toUpperCase(),
        decimals: token.decimals || 18,
        totalSupply: token.totalSupply || '0',
        
        // Migration Progress
        bondingProgress: progressPercent,
        avaxRaised: avaxRaised,
        avaxRemaining: Math.max(0, avaxRemaining),
        estimatedTimeToMigration: estimatedHoursToMigration,
        
        // Trading Data
        totalAvaxVolume: parseFloat(token.totalAvaxVolume || '0'),
        totalBuyVolume: parseFloat(token.totalBuyVolume || '0'),
        totalSellVolume: parseFloat(token.totalSellVolume || '0'),
        totalTrades: token.totalTrades || 0,
        totalBuys: token.totalBuys || 0,
        totalSells: token.totalSells || 0,
        
        // Price Data
        currentPriceAvax: parseFloat(token.currentPriceAvax || '0'),
        marketCapAvax: parseFloat(token.marketCapAvax || '0'),
        priceHigh24h: parseFloat(token.priceHigh24h || '0'),
        priceLow24h: parseFloat(token.priceLow24h || '0'),
        volume24h: parseFloat(token.volume24h || '0'),
        priceChange24h: parseFloat(token.priceChange24h || '0'),
        
        // Timestamps
        lastTradeTime: parseInt(token.lastTradeTimestamp || '0'),
        lastUpdateTime: parseInt(token.lastUpdateTimestamp || '0'),
        
        category: 'close-to-migration'
      }
    })

    // Sort by highest bonding progress first
    tokens.sort((a, b) => b.bondingProgress - a.bondingProgress)

    return NextResponse.json({
      success: true,
      data: {
        tokens,
        count: tokens.length,
        metadata: {
          minProgress: minProgress * 100, // Return as percentage
          limit,
          hasMore: tokens.length === limit
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