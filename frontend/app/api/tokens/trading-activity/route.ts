import { NextRequest, NextResponse } from 'next/server'
import { config } from '../../../../config'

interface SubgraphTokenDeployment {
  id: string
  tokenAddress: string
  creator: string
  tokenId: string
  deployedAt: string
  bondingProgress: string
  migrationStatus: 'BONDING' | 'CLOSE_TO_MIGRATION' | 'MIGRATED'
  totalVolume: string
  totalTrades: number
  bondingEvents: {
    id: string
    user: string
    avaxAmount: string
    tokenAmount: string
    tradeType: 'BUY' | 'SELL'
    timestamp: string
    transactionHash: string
  }[]
}

interface SubgraphResponse {
  data: {
    tokenDeployments: SubgraphTokenDeployment[]
    bondingEvents: {
      id: string
      token: {
        id: string
        tokenAddress: string
      }
      user: string
      avaxAmount: string
      tokenAmount: string
      tradeType: 'BUY' | 'SELL'
      timestamp: string
      transactionHash: string
    }[]
  }
}

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

function getTimeframeFilter(timeframe: string): string {
  const now = Math.floor(Date.now() / 1000)
  
  switch (timeframe) {
    case '1h':
      return `timestamp_gte: "${now - 3600}"`
    case '24h':
      return `timestamp_gte: "${now - 86400}"`
    case '7d':
      return `timestamp_gte: "${now - 604800}"`
    case '30d':
      return `timestamp_gte: "${now - 2592000}"`
    default:
      return ''
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const timeframe = searchParams.get('timeframe') || '24h'
    const token = searchParams.get('token')
    const user = searchParams.get('user')
    const limit = parseInt(searchParams.get('limit') || '100')

    // Build GraphQL query
    const timeFilter = getTimeframeFilter(timeframe)
    const tokenFilter = token ? `token: "${token}"` : ''
    const userFilter = user ? `user: "${user}"` : ''
    
    const filters = [timeFilter, tokenFilter, userFilter].filter(Boolean).join(', ')
    const whereClause = filters ? `(where: { ${filters} })` : ''

    const query = `
      query {
        tokenDeployments(
          first: ${limit}
          orderBy: deployedAt
          orderDirection: desc
          ${whereClause}
        ) {
          id
          tokenAddress
          creator
          tokenId
          deployedAt
          bondingProgress
          migrationStatus
          totalVolume
          totalTrades
          bondingEvents(
            first: 10
            orderBy: timestamp
            orderDirection: desc
            ${whereClause}
          ) {
            id
            user
            avaxAmount
            tokenAmount
            tradeType
            timestamp
            transactionHash
          }
        }
        
        bondingEvents(
          first: ${limit}
          orderBy: timestamp
          orderDirection: desc
          ${whereClause}
        ) {
          id
          token {
            id
            tokenAddress
          }
          user
          avaxAmount
          tokenAmount
          tradeType
          timestamp
          transactionHash
        }
      }
    `

    const subgraphData = await querySubgraph(query)

    if (!subgraphData || !subgraphData.data) {
      // Fallback to demo data if subgraph is unavailable
      return NextResponse.json({
        success: true,
        data: {
          summary: {
            totalVolume: '0',
            totalTrades: 0,
            uniqueTraders: 0,
            timeframe
          },
          bondingCurve: {
            events: [],
            volume: '0',
            trades: 0
          },
          dexTrading: {
            events: [],
            volume: '0',
            trades: 0
          },
          combined: []
        }
      })
    }

    const { tokenDeployments, bondingEvents } = subgraphData.data

    // Calculate summary statistics
    const totalVolume = bondingEvents.reduce((sum: bigint, event: any) => 
      sum + BigInt(event.avaxAmount), 0n
    ).toString()

    const totalTrades = bondingEvents.length
    const uniqueTraders = new Set(bondingEvents.map((event: any) => event.user)).size

    // Format bonding curve events
    const formattedBondingEvents = bondingEvents.map((event: any) => ({
      type: 'bonding',
      tokenAddress: event.token.tokenAddress,
      user: event.user,
      avaxAmount: event.avaxAmount,
      tokenAmount: event.tokenAmount,
      tradeType: event.tradeType,
      timestamp: parseInt(event.timestamp),
      transactionHash: event.transactionHash,
      price: (parseFloat(event.avaxAmount) / parseFloat(event.tokenAmount)).toString()
    }))

    // For now, DEX trading events will be empty until we add DEX tracking
    const dexEvents: any[] = []

    // Combine all events
    const combinedEvents = [
      ...formattedBondingEvents,
      ...dexEvents
    ].sort((a, b) => b.timestamp - a.timestamp)

    return NextResponse.json({
      success: true,
      data: {
        summary: {
          totalVolume,
          totalTrades,
          uniqueTraders,
          timeframe
        },
        bondingCurve: {
          events: formattedBondingEvents,
          volume: totalVolume,
          trades: formattedBondingEvents.length
        },
        dexTrading: {
          events: dexEvents,
          volume: '0',
          trades: 0
        },
        combined: combinedEvents,
        tokens: tokenDeployments.map((token: SubgraphTokenDeployment) => ({
          address: token.tokenAddress,
          creator: token.creator,
          deployedAt: parseInt(token.deployedAt),
          bondingProgress: parseFloat(token.bondingProgress),
          migrationStatus: token.migrationStatus,
          totalVolume: token.totalVolume,
          totalTrades: token.totalTrades
        }))
      }
    })

  } catch (error) {
    console.error('Trading activity API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch trading activity',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
} 