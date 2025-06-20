import { NextRequest, NextResponse } from 'next/server'
import { createPublicClient, http, parseAbiItem } from 'viem'
import { avalanche } from 'viem/chains'
import { Pool } from 'pg'
import { getSafeBlockRange, formatBlockRangeError } from '../../../lib/blockchain-utils'

// Contract addresses from your Python files
const TARGET_ADDRESS = '0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e' // Token Factory
const WAVAX_ADDRESS = '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'

// Token Created event ABI
const TOKEN_CREATED_EVENT_ABI = parseAbiItem('event TokenCreated(uint256 tokenId, (uint128 curveScaler, uint16 a, uint8 b, bool lpDeployed, uint8 lpPercentage, uint8 salePercentage, uint8 creatorFeeBasisPoints, address creatorAddress, address pairAddress, address tokenContractAddress) params, uint256 tokenSupply)')

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
  },
  {
    name: 'totalSupply',
    type: 'function',
    stateMutability: 'view', 
    inputs: [],
    outputs: [{ type: 'uint256' }]
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
  totalSupply: string
  creator: string
  launched: Date
  price?: number
  marketCap?: number
  volume24h?: number
  holders?: number
  liquidity?: number
}

async function getTokenDetails(tokenAddress: string) {
  try {
    const tokenContract = {
      address: tokenAddress as `0x${string}`,
      abi: TOKEN_ABI
    }

    const [name, symbol, decimals, totalSupply] = await client.multicall({
      contracts: [
        { ...tokenContract, functionName: 'name' },
        { ...tokenContract, functionName: 'symbol' },
        { ...tokenContract, functionName: 'decimals' },
        { ...tokenContract, functionName: 'totalSupply' }
      ]
    })

    return {
      name: name.result || 'Unknown',
      symbol: symbol.result || 'UNKNOWN',
      decimals: decimals.result || 18,
      totalSupply: totalSupply.result?.toString() || '0'
    }
  } catch (error) {
    console.error('Error fetching token details:', error)
    return {
      name: 'Unknown Token',
      symbol: 'UNKNOWN',
      decimals: 18,
      totalSupply: '0'
    }
  }
}

async function getNewPairsFromDatabase(limit: number = 50): Promise<TokenData[]> {
  try {
    const query = `
      SELECT 
        token_address,
        creator_address,
        deployed_at,
        total_supply,
        pair_address,
        lp_deployed
      FROM token_deployments 
      WHERE deployed_at >= NOW() - INTERVAL '24 hours'
      ORDER BY deployed_at DESC 
      LIMIT $1
    `
    
    const result = await pool.query(query, [limit])
    
    const tokens = await Promise.all(
      result.rows.map(async (row) => {
        const tokenDetails = await getTokenDetails(row.token_address)
        
        return {
          address: row.token_address,
          name: tokenDetails.name,
          symbol: tokenDetails.symbol,
          decimals: tokenDetails.decimals,
          totalSupply: tokenDetails.totalSupply,
          creator: row.creator_address,
          launched: new Date(row.deployed_at),
          price: 0.001, // Initial bonding curve price
          marketCap: 10000, // Estimated initial market cap
          volume24h: 0,
          holders: 1, // Creator
          liquidity: 0
        }
      })
    )
    
    return tokens
  } catch (error) {
    console.error('Database error:', error)
    return []
  }
}

async function getNewPairsFromBlockchain(limit: number = 50): Promise<TokenData[]> {
  try {
    const currentBlock = await client.getBlockNumber()
    const fromBlock = currentBlock - 2000n // Last ~2 hours (within RPC limits)

    const logs = await client.getLogs({
      address: TARGET_ADDRESS as `0x${string}`,
      event: TOKEN_CREATED_EVENT_ABI,
      fromBlock,
      toBlock: 'latest'
    })

    const recentLogs = logs.slice(-limit)
    
    const tokens = await Promise.all(
      recentLogs.map(async (log: any) => {
        try {
          const tokenAddress = log.args.params.tokenContractAddress
          const creator = log.args.params.creatorAddress
          
          const tokenDetails = await getTokenDetails(tokenAddress)
          const block = await client.getBlock({ blockHash: log.blockHash })
          
          return {
            address: tokenAddress,
            name: tokenDetails.name,
            symbol: tokenDetails.symbol,
            decimals: tokenDetails.decimals,
            totalSupply: tokenDetails.totalSupply,
            creator,
            launched: new Date(Number(block.timestamp) * 1000),
            price: 0.001,
            marketCap: 10000,
            volume24h: 0,
            holders: 1,
            liquidity: 0
          }
        } catch (error) {
          console.error('Error processing token:', error)
          return null
        }
      })
    )

    return tokens.filter(Boolean) as TokenData[]
  } catch (error) {
    console.error('Blockchain error:', error)
    return []
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '50')
    
    // Try database first, fallback to blockchain
    let tokens = await getNewPairsFromDatabase(limit)
    
    if (tokens.length === 0) {
      console.log('No tokens from database, fetching from blockchain')
      tokens = await getNewPairsFromBlockchain(limit)
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
        error: 'Failed to fetch new pairs',
        data: [],
        count: 0
      },
      { status: 500 }
    )
  }
} 