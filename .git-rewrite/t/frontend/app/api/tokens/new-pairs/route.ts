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
    const hours = parseInt(searchParams.get('hours') || '168') // 7 days default

    // Note: Temporarily removing time filter due to timestamp format issues
    const query = `
      query {
        tokenDeployments(
          first: ${limit}
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
            hasMore: false
          }
        }
      })
    }

    const tokens = subgraphData.data.tokenDeployments.map((token: any) => {
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
        
        // Trading Data
        bondingProgress: parseFloat(token.bondingProgress || '0'),
        totalAvaxVolume: parseFloat(token.totalAvaxVolume || '0'),
        totalBuyVolume: parseFloat(token.totalBuyVolume || '0'),
        totalSellVolume: parseFloat(token.totalSellVolume || '0'),
        totalTrades: token.totalTrades || 0,
        totalBuys: token.totalBuys || 0,
        totalSells: token.totalSells || 0,
        
        // Price Data
        currentPriceAvax: parseFloat(token.currentPriceAvax || '0'),
        avaxRaised: parseFloat(token.avaxRaised || '0'),
        marketCapAvax: parseFloat(token.marketCapAvax || '0'),
        priceHigh24h: parseFloat(token.priceHigh24h || '0'),
        priceLow24h: parseFloat(token.priceLow24h || '0'),
        volume24h: parseFloat(token.volume24h || '0'),
        priceChange24h: parseFloat(token.priceChange24h || '0'),
        
        // Timestamps
        lastTradeTime: parseInt(token.lastTradeTimestamp || '0'),
        lastUpdateTime: parseInt(token.lastUpdateTimestamp || '0'),
        
        category: 'new-pairs'
      }
    })

    return NextResponse.json({
      success: true,
      data: {
        tokens,
        count: tokens.length,
        metadata: {
          timeframe: `${hours}h (showing all BONDING tokens)`,
          limit,
          hasMore: tokens.length === limit,
          note: 'Real Arena tokens from subgraph - time filter temporarily disabled'
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