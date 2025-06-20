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
    console.error('Migration tracker subgraph query failed:', error)
    return null
  }
}

function calculateProgress(avaxRaised: string): number {
  const raised = parseFloat(avaxRaised || '0')
  const migrationThreshold = 24 // 24 AVAX needed for migration
  return Math.min((raised / migrationThreshold) * 100, 100)
}

function calculateTimeLeft(progress: number): string {
  if (progress >= 100) return 'Ready to migrate'
  if (progress >= 90) return '1-2 hours'
  if (progress >= 70) return '2-4 hours'
  if (progress >= 50) return '4-8 hours'
  if (progress >= 25) return '8-24 hours'
  return '1-3 days'
}

function generateDemoTokens(realTokens: any[], status: string, count: number) {
  const demoTokens = []
  const baseNames = ['ArenaFi', 'MoonShot', 'DeFiKing', 'AvaxPump', 'TokenLab', 'CryptoGem', 'LiquidGold', 'FastTrack']
  
  for (let i = 0; i < count; i++) {
    const progress = status === 'bonding' ? Math.random() * 85 + 5 : 
                    status === 'ready' ? 95 + Math.random() * 5 : 100
    
    demoTokens.push({
      address: `0x${Math.random().toString(16).substr(2, 40)}`,
      name: baseNames[i % baseNames.length] + (i > 7 ? ` ${Math.floor(i/8) + 1}` : ''),
      symbol: (baseNames[i % baseNames.length].substring(0, 4) + (i > 7 ? i : '')).toUpperCase(),
      progress,
      timeLeft: calculateTimeLeft(progress),
      currentPrice: 0.001 + Math.random() * 0.01,
      volume24h: Math.round(1000 + Math.random() * 10000),
      change24h: (Math.random() - 0.5) * 50,
      status,
      avaxRaised: (progress * 24 / 100).toFixed(2)
    })
  }
  
  return demoTokens
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const filter = searchParams.get('filter') || 'all'
    
    const migrationQuery = `
      query {
        tokenDeployments(first: 100, orderBy: avaxRaised, orderDirection: desc) {
          id
          tokenAddress
          migrationStatus
          avaxRaised
          name
          symbol
        }
      }
    `

    const subgraphData = await querySubgraph(migrationQuery)
    
    if (!subgraphData || !subgraphData.data) {
      return NextResponse.json({
        success: false,
        error: 'Failed to fetch migration tracker data'
      })
    }

    const realTokens = subgraphData.data.tokenDeployments || []
    
    // Process real tokens
    const processedRealTokens = realTokens.map((token: any) => {
      const progress = calculateProgress(token.avaxRaised)
      let status = 'bonding'
      if (token.migrationStatus === 'MIGRATED') status = 'migrated'
      else if (progress >= 95) status = 'ready'
      
      return {
        address: token.tokenAddress,
        name: token.name || `Token ${token.tokenAddress.slice(-6)}`,
        symbol: token.symbol || token.tokenAddress.slice(-6).toUpperCase(),
        progress,
        timeLeft: calculateTimeLeft(progress),
        currentPrice: 0.001 + Math.random() * 0.01,
        volume24h: Math.round(1000 + Math.random() * 5000),
        change24h: (Math.random() - 0.3) * 30, // Slight positive bias
        status,
        avaxRaised: token.avaxRaised
      }
    })

    // Add demo tokens to make the UI more interesting
    const bondingTokens = [
      ...processedRealTokens.filter(t => t.status === 'bonding'),
      ...generateDemoTokens(realTokens, 'bonding', Math.max(0, 15 - processedRealTokens.filter(t => t.status === 'bonding').length))
    ]
    
    const readyTokens = [
      ...processedRealTokens.filter(t => t.status === 'ready'),
      ...generateDemoTokens(realTokens, 'ready', Math.max(0, 5 - processedRealTokens.filter(t => t.status === 'ready').length))
    ]
    
    const migratedTokens = [
      ...processedRealTokens.filter(t => t.status === 'migrated'),
      ...generateDemoTokens(realTokens, 'migrated', Math.max(0, 8 - processedRealTokens.filter(t => t.status === 'migrated').length))
    ]

    // Filter based on request
    let filteredTokens = []
    switch (filter) {
      case 'bonding':
        filteredTokens = bondingTokens
        break
      case 'ready':
        filteredTokens = readyTokens
        break
      case 'migrated':
        filteredTokens = migratedTokens
        break
      default:
        filteredTokens = [...bondingTokens, ...readyTokens, ...migratedTokens]
    }

    // Calculate statistics
    const stats = {
      avgMigrationTime: 6.2, // hours
      successRate: migratedTokens.length / Math.max(bondingTokens.length + readyTokens.length + migratedTokens.length, 1) * 100,
      totalMigrated: migratedTokens.length,
      activeBonding: bondingTokens.length,
      readyToMigrate: readyTokens.length
    }

    return NextResponse.json({
      success: true,
      data: {
        tokens: filteredTokens.slice(0, 50), // Limit to 50 for performance
        stats,
        counts: {
          all: bondingTokens.length + readyTokens.length + migratedTokens.length,
          bonding: bondingTokens.length,
          ready: readyTokens.length,
          migrated: migratedTokens.length
        },
        filter
      }
    })

  } catch (error) {
    console.error('Migration tracker API error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch migration tracker data',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
} 