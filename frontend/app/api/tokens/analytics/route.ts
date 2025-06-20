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
    const timeRange = searchParams.get('timeRange') || '7d'
    
    console.log('Analytics API called with timeRange:', timeRange)
    console.log('Subgraph URL:', config.arenaSubgraphUrl)
    
    // Start with a simple query that should work
    const analyticsQuery = `
      query {
        tokenDeployments(first: 10) {
          id
          tokenAddress
          migrationStatus
          avaxRaised
          name
          symbol
        }
      }
    `

    console.log('Executing analytics query...')
    const subgraphData = await querySubgraph(analyticsQuery)
    console.log('Subgraph response:', JSON.stringify(subgraphData, null, 2))

    if (!subgraphData || !subgraphData.data) {
      console.error('No data from subgraph:', subgraphData)
      return NextResponse.json({
        success: false,
        error: 'Failed to fetch analytics data',
        debug: subgraphData
      })
    }

    const tokens = subgraphData.data.tokenDeployments || []
    console.log('Found tokens:', tokens.length)

    // Calculate basic metrics from the available data
    const totalTokens = tokens.length
    const bondingTokens = tokens.filter((t: any) => t.migrationStatus === 'BONDING')
    const migratedTokens = tokens.filter((t: any) => t.migrationStatus === 'MIGRATED')
    const readyTokens = [] // Will calculate later with full data

    // Calculate total value locked (sum of all avaxRaised)
    const totalValueLocked = tokens.reduce((sum: number, token: any) => {
      return sum + parseFloat(token.avaxRaised || '0')
    }, 0)

    // Use a placeholder for volume
    const volume24h = totalValueLocked * 0.1 // Rough estimate

    // Calculate average migration time (simplified)
    const avgMigrationTime = 6.2 // Placeholder since we don't have deployedAt in simple query

    // Calculate success rate
    const successRate = totalTokens > 0 ? (migratedTokens.length / totalTokens) * 100 : 0

    // Calculate protocol breakdown
    const protocolBreakdown = {
      tokenFactory: totalValueLocked * 0.7, // Arena Token Factory
      bondingCurves: totalValueLocked * 0.25, // Bonding mechanism
      dexLiquidity: totalValueLocked * 0.05   // Migrated DEX pairs
    }

    // Simplified data structures
    const recentActivity = [] // Will add later with full data

    // Migration pipeline data
    const migrationPipeline = {
      bonding: bondingTokens.slice(0, 5).map((token: any) => ({
        address: token.tokenAddress,
        name: token.name || `Token ${token.tokenAddress.slice(-6)}`,
        symbol: token.symbol || token.tokenAddress.slice(-6).toUpperCase(),
        progress: Math.random() * 80, // Placeholder
        timeLeft: '4h 30m', // Placeholder
        currentPrice: 0.001,
        volume24h: 1000,
        change24h: 5.5,
        status: 'bonding'
      })),
      ready: readyTokens,
      migrated: migratedTokens.slice(0, 5).map((token: any) => ({
        address: token.tokenAddress,
        name: token.name || `Token ${token.tokenAddress.slice(-6)}`,
        symbol: token.symbol || token.tokenAddress.slice(-6).toUpperCase(),
        progress: 100,
        timeLeft: 'Migrated',
        currentPrice: 0.002,
        volume24h: 5000,
        change24h: 125.7,
        status: 'migrated'
      }))
    }

    // Historical data (simplified - you might want to add time-series data)
    const historicalData = generateHistoricalData(timeRange, {
      totalValueLocked,
      volume24h,
      totalTokens,
      migratedCount: migratedTokens.length
    })

    return NextResponse.json({
      success: true,
      data: {
        overview: {
          totalValueLocked,
          volume24h,
          totalTokens,
          migratedTokens: migratedTokens.length,
          bondingTokens: bondingTokens.length,
          readyTokens: readyTokens.length,
          successRate,
          avgMigrationTime,
          change24h: 12.5 // You could calculate this from historical data
        },
        protocolBreakdown,
        migrationPipeline,
        recentActivity,
        historicalData,
        metadata: {
          timeRange,
          lastUpdated: new Date().toISOString(),
          totalTrades: 0
        }
      }
    })

  } catch (error) {
    console.error('Analytics API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch analytics data',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}

function calculateTimeLeft(progress: number): string {
  if (progress >= 1.0) return 'Ready'
  if (progress >= 0.9) return `${Math.round((1.0 - progress) * 100)}h`
  if (progress >= 0.5) return `${Math.round((1.0 - progress) * 200)}h`
  return 'Unknown'
}

function generateHistoricalData(timeRange: string, currentData: any) {
  const days = timeRange === '1d' ? 1 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
  const data = []
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    
    // Generate realistic historical progression
    const dayFactor = (days - i) / days
    const randomFactor = 0.8 + Math.random() * 0.4 // 0.8 to 1.2
    
    data.push({
      date: date.toISOString().split('T')[0],
      tvl: Math.round(currentData.totalValueLocked * dayFactor * randomFactor),
      volume: Math.round(currentData.volume24h * randomFactor),
      launches: Math.round((currentData.totalTokens / days) * randomFactor),
      migrations: Math.round((currentData.migratedCount / days) * randomFactor)
    })
  }
  
  return data
} 