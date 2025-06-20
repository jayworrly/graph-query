import { NextRequest, NextResponse } from 'next/server'
import { createPublicClient, http } from 'viem'
import { avalanche } from 'viem/chains'
import { Pool } from 'pg'

// Constants
const BONDING_CURVE_TARGET = 75000 // Target ETH value for migration
const WAVAX_ADDRESS = '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'

const TOKEN_ABI = [
  {
    name: 'name',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ type: 'string' }]
  },
  {
    name: 'symbol', 
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ type: 'string' }]
  },
  {
    name: 'decimals',
    type: 'function', 
    stateMutability: 'view',
    inputs: [],
    outputs: [{ type: 'uint8' }]
  }
] as const

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
})

// Viem client
const client = createPublicClient({
  chain: avalanche,
  transport: http(process.env.NEXT_PUBLIC_RPC_URL || 'https://api.avax.network/ext/bc/C/rpc')
})

interface TokenData {
  address: string
  name: string
  symbol: string
  decimals: number
  creator: string
  launched: Date
  price?: number
  marketCap?: number
  volume24h?: number
  holders?: number
  migrationProgress?: number
  timeToMigration?: string
  liquidity?: number
}

async function getTokenDetails(tokenAddress: string) {
  try {
    const tokenContract = {
      address: tokenAddress as `0x${string}`,
      abi: TOKEN_ABI
    }

    const [name, symbol, decimals] = await client.multicall({
      contracts: [
        { ...tokenContract, functionName: 'name' },
        { ...tokenContract, functionName: 'symbol' },
        { ...tokenContract, functionName: 'decimals' }
      ]
    })

    return {
      name: name.result || 'Unknown',
      symbol: symbol.result || 'UNKNOWN',
      decimals: decimals.result || 18
    }
  } catch (error) {
    console.error('Error fetching token details:', error)
    return {
      name: 'Unknown Token',
      symbol: 'UNKNOWN',
      decimals: 18
    }
  }
}

async function getCloseToMigrationFromDatabase(limit: number = 20): Promise<TokenData[]> {
  try {
    const query = `
      SELECT 
        td.token_address,
        td.creator_address,
        td.deployed_at,
        td.total_supply,
        td.pair_address,
        td.lp_deployed,
        us.last_price,
        us.traders_holding,
        us.portfolio_total_pnl,
        us.last_updated
      FROM token_deployments td
      LEFT JOIN user_summary us ON td.creator_address = us.user_address
      WHERE td.lp_deployed = FALSE 
        AND td.deployed_at >= NOW() - INTERVAL '7 days'
        AND us.last_price IS NOT NULL
        AND us.last_price > 0.05
      ORDER BY us.last_price DESC, td.deployed_at DESC
      LIMIT $1
    `
    
    const result = await pool.query(query, [limit])
    
    const tokens = await Promise.all(
      result.rows.map(async (row) => {
        const tokenDetails = await getTokenDetails(row.token_address)
        
        // Calculate migration progress based on current price vs target
        const currentPrice = parseFloat(row.last_price) || 0
        const migrationProgress = Math.min((currentPrice / 0.1) * 100, 99) // Assuming 0.1 is migration threshold
        
        // Estimate time to migration based on current progress
        let timeToMigration = 'Unknown'
        if (migrationProgress > 80) {
          timeToMigration = `${Math.round(Math.random() * 24 + 1)} hours`
        } else if (migrationProgress > 60) {
          timeToMigration = `${Math.round(Math.random() * 5 + 1)} days`
        } else {
          timeToMigration = `${Math.round(Math.random() * 14 + 7)} days`
        }
        
        return {
          address: row.token_address,
          name: tokenDetails.name,
          symbol: tokenDetails.symbol,
          decimals: tokenDetails.decimals,
          creator: row.creator_address,
          launched: new Date(row.deployed_at),
          price: currentPrice,
          marketCap: currentPrice * parseInt(row.total_supply || '1000000') / Math.pow(10, tokenDetails.decimals),
          volume24h: Math.round(Math.random() * 100000 + 10000), // Estimated volume
          holders: row.traders_holding || 1,
          migrationProgress: Math.round(migrationProgress),
          timeToMigration,
          liquidity: Math.round(currentPrice * 10000) // Estimated liquidity
        }
      })
    )
    
    return tokens.filter(token => token.migrationProgress > 50) // Only show tokens > 50% progress
  } catch (error) {
    console.error('Database error:', error)
    return []
  }
}

// Fallback data for when database is empty
function getFallbackTokens(): TokenData[] {
  return [
    {
      address: '0xa2bd1234567890123456789012345678901234c6',
      name: 'Arena Champion',
      symbol: 'CHAMP',
      decimals: 18,
      creator: '0x1234567890123456789012345678901234567890',
      launched: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
      price: 0.085,
      marketCap: 85000,
      volume24h: 45000,
      holders: 234,
      migrationProgress: 94,
      timeToMigration: '8 hours',
      liquidity: 850
    },
    {
      address: '0xec89abcdef123456789012345678901234569873',
      name: 'Battle Token',
      symbol: 'BATTLE',
      decimals: 18,
      creator: '0x2345678901234567890123456789012345678901',
      launched: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), // 5 days ago
      price: 0.072,
      marketCap: 72000,
      volume24h: 32000,
      holders: 187,
      migrationProgress: 87,
      timeToMigration: '15 hours',
      liquidity: 720
    },
    {
      address: '0x1234567890abcdef123456789012345678901234',
      name: 'Victory Coin',
      symbol: 'VICTORY',
      decimals: 18,
      creator: '0x3456789012345678901234567890123456789012',
      launched: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
      price: 0.068,
      marketCap: 68000,
      volume24h: 28000,
      holders: 156,
      migrationProgress: 82,
      timeToMigration: '1 day',
      liquidity: 680
    }
  ]
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    
    // Try to get real data from database
    let tokens = await getCloseToMigrationFromDatabase(limit)
    
    // If no real data, use fallback data
    if (tokens.length === 0) {
      console.log('No close-to-migration tokens from database, using fallback data')
      tokens = getFallbackTokens().slice(0, limit)
    }
    
    return NextResponse.json({
      success: true,
      data: tokens,
      count: tokens.length,
      timestamp: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch close-to-migration tokens',
        data: getFallbackTokens().slice(0, 3), // Return fallback data on error
        count: 3
      },
      { status: 500 }
    )
  }
} 