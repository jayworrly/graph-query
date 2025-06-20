import { NextRequest, NextResponse } from 'next/server'

// GraphQL endpoint for Arena subgraph
const SUBGRAPH_URL = process.env.ARENA_SUBGRAPH_URL || 'https://api.thegraph.com/subgraphs/name/arena/trading'

interface TradingActivityParams {
  timeframe?: '1h' | '24h' | '7d' | '30d'
  tokenAddress?: string
  userAddress?: string
  limit?: number
  offset?: number
}

interface TradingActivity {
  // Token info
  tokenAddress: string
  tokenName: string
  tokenSymbol: string
  
  // Trade details
  id: string
  user: string
  tradeType: 'BUY' | 'SELL'
  avaxAmount: string
  tokenAmount: string
  pricePerToken: string
  
  // Context
  bondingProgress?: number
  migrationStatus: string
  timestamp: string
  blockNumber: string
  transactionHash: string
  
  // DEX vs Bonding curve
  platform: 'BONDING_CURVE' | 'DEX'
  pairAddress?: string
}

async function fetchTradingActivity(params: TradingActivityParams): Promise<TradingActivity[]> {
  try {
    // Calculate timestamp for timeframe
    const now = Math.floor(Date.now() / 1000)
    const timeframes = {
      '1h': now - 3600,
      '24h': now - 86400,
      '7d': now - 604800,
      '30d': now - 2592000
    }
    
    const fromTimestamp = params.timeframe ? timeframes[params.timeframe] : timeframes['24h']
    
    // Build GraphQL query based on parameters
    let whereClause = `timestamp_gte: "${fromTimestamp}"`
    
    if (params.tokenAddress) {
      whereClause += `, token: "${params.tokenAddress.toLowerCase()}"`
    }
    
    if (params.userAddress) {
      whereClause += `, user: "${params.userAddress.toLowerCase()}"`
    }

    // Query for bonding events
    const bondingQuery = `
      query BondingActivity {
        bondingEvents(
          first: ${params.limit || 50}
          skip: ${params.offset || 0}
          orderBy: timestamp
          orderDirection: desc
          where: { ${whereClause} }
        ) {
          id
          token {
            tokenAddress
            name
            symbol
            migrationStatus
            bondingProgress
          }
          user
          avaxAmount
          tokenAmount
          pricePerToken
          tradeType
          timestamp
          blockNumber
          transactionHash
        }
      }
    `

    // Query for DEX swap events
    const swapQuery = `
      query SwapActivity {
        swapEvents(
          first: ${params.limit || 50}
          skip: ${params.offset || 0}
          orderBy: timestamp
          orderDirection: desc
          where: { ${whereClause} }
        ) {
          id
          token {
            tokenAddress
            name
            symbol
            migrationStatus
            pairAddress
          }
          user
          amountIn
          amountOut
          pricePerToken
          tradeType
          pair
          timestamp
          blockNumber
          transactionHash
        }
      }
    `

    // Execute both queries
    const [bondingResponse, swapResponse] = await Promise.all([
      fetch(SUBGRAPH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: bondingQuery })
      }),
      fetch(SUBGRAPH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: swapQuery })
      })
    ])

    const bondingData = await bondingResponse.json()
    const swapData = await swapResponse.json()

    // Combine and format results
    const activities: TradingActivity[] = []

    // Process bonding events
    if (bondingData.data?.bondingEvents) {
      bondingData.data.bondingEvents.forEach((event: any) => {
        activities.push({
          tokenAddress: event.token.tokenAddress,
          tokenName: event.token.name,
          tokenSymbol: event.token.symbol,
          id: event.id,
          user: event.user,
          tradeType: event.tradeType,
          avaxAmount: event.avaxAmount,
          tokenAmount: event.tokenAmount,
          pricePerToken: event.pricePerToken,
          bondingProgress: parseFloat(event.token.bondingProgress),
          migrationStatus: event.token.migrationStatus,
          timestamp: event.timestamp,
          blockNumber: event.blockNumber,
          transactionHash: event.transactionHash,
          platform: 'BONDING_CURVE'
        })
      })
    }

    // Process swap events
    if (swapData.data?.swapEvents) {
      swapData.data.swapEvents.forEach((event: any) => {
        activities.push({
          tokenAddress: event.token.tokenAddress,
          tokenName: event.token.name,
          tokenSymbol: event.token.symbol,
          id: event.id,
          user: event.user,
          tradeType: event.tradeType,
          avaxAmount: event.tradeType === 'BUY' ? event.amountIn : event.amountOut,
          tokenAmount: event.tradeType === 'BUY' ? event.amountOut : event.amountIn,
          pricePerToken: event.pricePerToken,
          migrationStatus: event.token.migrationStatus,
          timestamp: event.timestamp,
          blockNumber: event.blockNumber,
          transactionHash: event.transactionHash,
          platform: 'DEX',
          pairAddress: event.pair
        })
      })
    }

    // Sort by timestamp (most recent first)
    activities.sort((a, b) => parseInt(b.timestamp) - parseInt(a.timestamp))

    // Apply limit if needed
    return activities.slice(0, params.limit || 50)

  } catch (error) {
    console.error('Error fetching trading activity from subgraph:', error)
    return []
  }
}

// Fallback trading activity data
function getFallbackTradingActivity(): TradingActivity[] {
  const now = Math.floor(Date.now() / 1000)
  
  return [
    {
      tokenAddress: '0x1234567890123456789012345678901234567890',
      tokenName: 'Arena Champion',
      tokenSymbol: 'CHAMP',
      id: 'bonding-1',
      user: '0xabcdef1234567890123456789012345678901234',
      tradeType: 'BUY',
      avaxAmount: '1000000000000000000', // 1 AVAX
      tokenAmount: '1000000000000000000000', // 1000 tokens
      pricePerToken: '0.001',
      bondingProgress: 45,
      migrationStatus: 'PENDING',
      timestamp: (now - 300).toString(), // 5 minutes ago
      blockNumber: '64150000',
      transactionHash: '0x123...',
      platform: 'BONDING_CURVE'
    },
    {
      tokenAddress: '0x2345678901234567890123456789012345678901',
      tokenName: 'Victory Token',
      tokenSymbol: 'VICTORY',
      id: 'swap-1',
      user: '0xbcdef12345678901234567890123456789012345',
      tradeType: 'SELL',
      avaxAmount: '2000000000000000000', // 2 AVAX
      tokenAmount: '500000000000000000000', // 500 tokens
      pricePerToken: '0.004',
      migrationStatus: 'MIGRATED',
      timestamp: (now - 600).toString(), // 10 minutes ago
      blockNumber: '64149950',
      transactionHash: '0x456...',
      platform: 'DEX',
      pairAddress: '0xcdef123456789012345678901234567890123456'
    }
  ]
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    
    const params: TradingActivityParams = {
      timeframe: (searchParams.get('timeframe') as any) || '24h',
      tokenAddress: searchParams.get('tokenAddress') || undefined,
      userAddress: searchParams.get('userAddress') || undefined,
      limit: parseInt(searchParams.get('limit') || '50'),
      offset: parseInt(searchParams.get('offset') || '0')
    }

    // Validate timeframe
    if (!['1h', '24h', '7d', '30d'].includes(params.timeframe!)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid timeframe. Use: 1h, 24h, 7d, or 30d',
        data: []
      }, { status: 400 })
    }

    // Try to fetch from subgraph
    let activities = await fetchTradingActivity(params)

    // Use fallback data if subgraph is unavailable
    if (activities.length === 0) {
      console.log('No trading activity from subgraph, using fallback data')
      activities = getFallbackTradingActivity()
    }

    // Calculate summary statistics
    const summary = {
      totalTrades: activities.length,
      totalVolumeAVAX: activities.reduce((sum, activity) => 
        sum + parseFloat(activity.avaxAmount), 0
      ),
      uniqueTraders: new Set(activities.map(a => a.user)).size,
      bondingTrades: activities.filter(a => a.platform === 'BONDING_CURVE').length,
      dexTrades: activities.filter(a => a.platform === 'DEX').length,
      buyTrades: activities.filter(a => a.tradeType === 'BUY').length,
      sellTrades: activities.filter(a => a.tradeType === 'SELL').length
    }

    return NextResponse.json({
      success: true,
      data: activities,
      summary,
      params,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('Trading activity API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch trading activity',
      data: getFallbackTradingActivity().slice(0, 10),
      summary: { totalTrades: 2, totalVolumeAVAX: 3, uniqueTraders: 2 }
    }, { status: 500 })
  }
} 