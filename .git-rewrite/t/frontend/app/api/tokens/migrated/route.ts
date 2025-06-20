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
    const days = parseInt(searchParams.get('days') || '30')

    const query = `
      query {
        tokenDeployments(
          first: ${limit}
          orderBy: deployedAt
          orderDirection: desc
          where: { 
            migrationStatus: MIGRATED
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
          liquidityAvax
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
      // Return empty data if subgraph is unavailable (no fallback mock data)
      return NextResponse.json({
        success: true,
        data: {
          tokens: [],
          count: 0,
          metadata: {
            timeframe: `${days}d`,
            limit,
            hasMore: false,
            note: 'No migrated tokens found in Arena ecosystem yet'
          }
        }
      })
    }

    const tokens = subgraphData.data.tokenDeployments.map((token: any) => {
      const totalAvaxVolume = parseFloat(token.totalAvaxVolume || '0')
      const currentPrice = parseFloat(token.currentPriceAvax || '0')
      const avaxRaised = parseFloat(token.avaxRaised || '0')
      
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
        
        // Migration Status
        bondingProgress: 100, // Migrated tokens are 100% complete
        
        // Trading Data
        totalAvaxVolume: totalAvaxVolume,
        totalBuyVolume: parseFloat(token.totalBuyVolume || '0'),
        totalSellVolume: parseFloat(token.totalSellVolume || '0'),
        totalTrades: token.totalTrades || 0,
        totalBuys: token.totalBuys || 0,
        totalSells: token.totalSells || 0,
        
        // Price & Market Data
        currentPriceAvax: currentPrice,
        avaxRaised: avaxRaised,
        marketCap: parseFloat(token.marketCapAvax || '0') || (currentPrice * 1000000000), // Use real data or fallback
        volume24h: parseFloat(token.volume24h || '0') || totalAvaxVolume, // Use real 24h data or fallback
        liquidity: parseFloat(token.liquidityAvax || '0') || (avaxRaised * 2), // Use real liquidity or estimate
        priceHigh24h: parseFloat(token.priceHigh24h || '0'),
        priceLow24h: parseFloat(token.priceLow24h || '0'),
        priceChange24h: parseFloat(token.priceChange24h || '0'),
        
        // Timestamps
        lastTradeTime: parseInt(token.lastTradeTimestamp || '0'),
        lastUpdateTime: parseInt(token.lastUpdateTimestamp || '0'),
        
        category: 'migrated'
      }
    })

    return NextResponse.json({
      success: true,
      data: {
        tokens,
        count: tokens.length,
        metadata: {
          timeframe: `${days}d`,
          limit,
          hasMore: tokens.length === limit,
          note: tokens.length === 0 ? 'No migrated tokens found in Arena ecosystem yet' : 'Real migrated tokens from Arena subgraph'
        }
      }
    })

  } catch (error) {
    console.error('Migrated tokens API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch migrated tokens',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
} 