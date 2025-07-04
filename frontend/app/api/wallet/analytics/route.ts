import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const client = await pool.connect()

    try {
      // Overall ParaSwap statistics
      const overviewQuery = `
        SELECT 
          COUNT(*) as total_transactions,
          COUNT(DISTINCT real_user) as unique_users,
          COUNT(DISTINCT token_address) as unique_tokens,
          COUNT(DISTINCT tx_hash) as unique_tx_hashes,
          SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END) as total_buys,
          SUM(CASE WHEN label = 'SELL' THEN 1 ELSE 0 END) as total_sells,
          MIN(block_number) as first_block,
          MAX(block_number) as latest_block,
          MIN(created_at) as first_activity,
          MAX(created_at) as latest_activity
        FROM paraswap_arena_users
      `

      // User activity distribution
      const userDistributionQuery = `
        WITH user_trade_counts AS (
          SELECT 
            real_user,
            COUNT(*) as trade_count
          FROM paraswap_arena_users
          GROUP BY real_user
        )
        SELECT 
          CASE 
            WHEN trade_count >= 1000 THEN 'Power Traders (1000+)'
            WHEN trade_count >= 100 THEN 'Active Traders (100-999)'
            WHEN trade_count >= 10 THEN 'Regular Traders (10-99)'
            ELSE 'Light Traders (1-9)'
          END as trader_category,
          COUNT(*) as user_count,
          SUM(trade_count) as total_trades
        FROM user_trade_counts
        GROUP BY 
          CASE 
            WHEN trade_count >= 1000 THEN 'Power Traders (1000+)'
            WHEN trade_count >= 100 THEN 'Active Traders (100-999)'
            WHEN trade_count >= 10 THEN 'Regular Traders (10-99)'
            ELSE 'Light Traders (1-9)'
          END
        ORDER BY 
          CASE 
            WHEN trader_category = 'Power Traders (1000+)' THEN 1
            WHEN trader_category = 'Active Traders (100-999)' THEN 2
            WHEN trader_category = 'Regular Traders (10-99)' THEN 3
            ELSE 4
          END
      `

      // Top tokens by activity
      const topTokensQuery = `
        SELECT 
          token_address,
          COUNT(*) as transaction_count,
          COUNT(DISTINCT real_user) as unique_traders,
          SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END) as buy_count,
          SUM(CASE WHEN label = 'SELL' THEN 1 ELSE 0 END) as sell_count
        FROM paraswap_arena_users
        GROUP BY token_address
        ORDER BY transaction_count DESC
        LIMIT 10
      `

      const [overviewResult, distributionResult, topTokensResult] = await Promise.all([
        client.query(overviewQuery),
        client.query(userDistributionQuery),
        client.query(topTokensQuery)
      ])

      const overview = overviewResult.rows[0]
      const distribution = distributionResult.rows
      const topTokens = topTokensResult.rows

      const analytics = {
        overview: {
          totalTransactions: parseInt(overview.total_transactions),
          uniqueUsers: parseInt(overview.unique_users),
          uniqueTokens: parseInt(overview.unique_tokens),
          uniqueTxHashes: parseInt(overview.unique_tx_hashes),
          totalBuys: parseInt(overview.total_buys),
          totalSells: parseInt(overview.total_sells),
          buyPercentage: Math.round((parseInt(overview.total_buys) / parseInt(overview.total_transactions)) * 100),
          blockRange: {
            first: parseInt(overview.first_block),
            latest: parseInt(overview.latest_block)
          },
          timeRange: {
            first: overview.first_activity ? new Date(overview.first_activity).toLocaleDateString() : null,
            latest: overview.latest_activity ? new Date(overview.latest_activity).toLocaleDateString() : null
          }
        },
        userDistribution: distribution.map(dist => ({
          category: dist.trader_category,
          userCount: parseInt(dist.user_count),
          totalTrades: parseInt(dist.total_trades)
        })),
        topTokens: topTokens.map(token => ({
          address: token.token_address,
          transactionCount: parseInt(token.transaction_count),
          uniqueTraders: parseInt(token.unique_traders),
          buyCount: parseInt(token.buy_count),
          sellCount: parseInt(token.sell_count),
          buyPercentage: Math.round((parseInt(token.buy_count) / parseInt(token.transaction_count)) * 100)
        }))
      }

      return NextResponse.json({
        success: true,
        data: analytics
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('ParaSwap analytics API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to get ParaSwap analytics'
    }, { status: 500 })
  }
}