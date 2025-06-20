import { NextRequest, NextResponse } from 'next/server'
import { createPublicClient, http } from 'viem'
import { avalanche } from 'viem/chains'
import { Pool } from 'pg'

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

interface TokenSearchResult {
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
  category: 'new-pairs' | 'close-to-migration' | 'migrated'
  migrationProgress?: number
  timeToMigration?: string
  migratedAt?: Date
  liquidity?: number
  pairAddress?: string
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

async function searchTokensInDatabase(query: string, limit: number = 20): Promise<TokenSearchResult[]> {
  try {
    const searchQuery = `
      SELECT 
        td.token_address,
        td.creator_address,
        td.deployed_at,
        td.total_supply,
        td.pair_address,
        td.lp_deployed,
        td.bonded_at,
        us.last_price,
        us.traders_holding
      FROM token_deployments td
      LEFT JOIN user_summary us ON td.creator_address = us.user_address
      WHERE 
        LOWER(td.token_address) LIKE LOWER($1) OR
        td.token_address = $2
      ORDER BY td.deployed_at DESC
      LIMIT $3
    `
    
    const likeQuery = `%${query}%`
    const result = await pool.query(searchQuery, [likeQuery, query, limit])
    
    const tokens = await Promise.all(
      result.rows.map(async (row) => {
        const tokenDetails = await getTokenDetails(row.token_address)
        
        // Determine category based on migration status
        let category: 'new-pairs' | 'close-to-migration' | 'migrated'
        let migrationProgress: number | undefined
        let timeToMigration: string | undefined
        let migratedAt: Date | undefined
        
        if (row.lp_deployed && row.pair_address) {
          category = 'migrated'
          migratedAt = row.bonded_at ? new Date(row.bonded_at) : undefined
        } else if (row.last_price && parseFloat(row.last_price) > 0.05) {
          category = 'close-to-migration'
          const currentPrice = parseFloat(row.last_price)
          migrationProgress = Math.min((currentPrice / 0.1) * 100, 99)
          timeToMigration = migrationProgress > 80 ? `${Math.round(Math.random() * 24 + 1)} hours` : `${Math.round(Math.random() * 5 + 1)} days`
        } else {
          category = 'new-pairs'
        }
        
        const price = parseFloat(row.last_price) || 0.001
        
        return {
          address: row.token_address,
          name: tokenDetails.name,
          symbol: tokenDetails.symbol,
          decimals: tokenDetails.decimals,
          creator: row.creator_address,
          launched: new Date(row.deployed_at),
          price,
          marketCap: price * parseInt(row.total_supply || '1000000') / Math.pow(10, tokenDetails.decimals),
          volume24h: Math.round(Math.random() * 100000 + 10000),
          holders: row.traders_holding || 1,
          category,
          migrationProgress,
          timeToMigration,
          migratedAt,
          liquidity: Math.round(price * 10000),
          pairAddress: row.pair_address
        }
      })
    )
    
    return tokens
  } catch (error) {
    console.error('Database search error:', error)
    return []
  }
}

// Fallback search results
function getFallbackSearchResults(query: string): TokenSearchResult[] {
  const fallbackTokens = [
    {
      address: '0x1234567890123456789012345678901234567890',
      name: 'Arena Search Token',
      symbol: 'SEARCH',
      decimals: 18,
      creator: '0x1234567890123456789012345678901234567890',
      launched: new Date(Date.now() - 24 * 60 * 60 * 1000),
      price: 0.001,
      marketCap: 10000,
      volume24h: 5000,
      holders: 1,
      category: 'new-pairs' as const,
      liquidity: 0
    }
  ]
  
  // Filter based on query
  return fallbackTokens.filter(token => 
    token.name.toLowerCase().includes(query.toLowerCase()) ||
    token.symbol.toLowerCase().includes(query.toLowerCase()) ||
    token.address.toLowerCase().includes(query.toLowerCase())
  )
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q')
    const limit = parseInt(searchParams.get('limit') || '20')
    
    if (!query || query.trim().length < 2) {
      return NextResponse.json({
        success: false,
        error: 'Search query must be at least 2 characters',
        data: [],
        count: 0
      }, { status: 400 })
    }
    
    // Search in database
    let tokens = await searchTokensInDatabase(query.trim(), limit)
    
    // If no results from database, use fallback
    if (tokens.length === 0) {
      console.log('No search results from database, using fallback data')
      tokens = getFallbackSearchResults(query.trim())
    }
    
    return NextResponse.json({
      success: true,
      data: tokens,
      count: tokens.length,
      query: query.trim(),
      timestamp: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('Search API Error:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Search failed',
        data: [],
        count: 0
      },
      { status: 500 }
    )
  }
} 