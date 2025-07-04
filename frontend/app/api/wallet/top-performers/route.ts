import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const metric = searchParams.get('metric') || 'trades' // trades, tokens, activity

    const client = await pool.connect()

    try {
      let orderClause = ''
      switch (metric) {
        case 'tokens':
          orderClause = 'unique_tokens DESC, total_trades DESC'
          break
        case 'activity':
          orderClause = 'trading_days DESC, total_trades DESC'
          break
        case 'buys':
          orderClause = 'buy_trades DESC'
          break
        case 'sells':
          orderClause = 'sell_trades DESC'
          break
        default:
          orderClause = 'total_trades DESC'
      }

      const topPerformersQuery = `
        WITH user_performance AS (
          SELECT 
            pau.real_user,
            COUNT(*) as total_trades,
            SUM(CASE WHEN pau.label = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN pau.label = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            COUNT(DISTINCT pau.token_address) as unique_tokens,
            COUNT(DISTINCT pau.tx_hash) as unique_transactions,
            COUNT(DISTINCT DATE(pau.created_at)) as trading_days,
            MIN(pau.block_number) as first_block,
            MAX(pau.block_number) as last_block,
            MIN(pau.created_at) as first_trade,
            MAX(pau.created_at) as last_trade
          FROM paraswap_arena_users pau
          GROUP BY pau.real_user
          HAVING COUNT(*) >= 10  -- Only include users with at least 10 trades
        ),
        user_top_token AS (
          SELECT DISTINCT ON (real_user)
            real_user,
            token_address as favorite_token,
            COUNT(*) as favorite_token_trades
          FROM paraswap_arena_users
          GROUP BY real_user, token_address
          ORDER BY real_user, COUNT(*) DESC
        )
        SELECT 
          up.real_user,
          wl.label,
          up.total_trades,
          up.buy_trades,
          up.sell_trades,
          up.unique_tokens,
          up.unique_transactions,
          up.trading_days,
          up.first_block,
          up.last_block,
          up.first_trade,
          up.last_trade,
          utt.favorite_token,
          utt.favorite_token_trades,
          CASE 
            WHEN up.total_trades > 0 
            THEN (up.buy_trades::float / up.total_trades * 100)
            ELSE 0 
          END as buy_percentage,
          CASE 
            WHEN up.trading_days > 0 
            THEN (up.total_trades::float / up.trading_days)
            ELSE 0 
          END as trades_per_day
        FROM user_performance up
        LEFT JOIN wallet_labels wl ON LOWER(wl.wallet_address) = LOWER(up.real_user)
        LEFT JOIN user_top_token utt ON up.real_user = utt.real_user
        ORDER BY ${orderClause}
        LIMIT $1
      `

      const result = await client.query(topPerformersQuery, [limit])

      const topPerformers = result.rows.map(row => ({
        address: row.real_user,
        label: row.label,
        totalTrades: parseInt(row.total_trades || '0'),
        buyTrades: parseInt(row.buy_trades || '0'),
        sellTrades: parseInt(row.sell_trades || '0'),
        buyPercentage: parseFloat(row.buy_percentage || '0'),
        uniqueTokens: parseInt(row.unique_tokens || '0'),
        uniqueTransactions: parseInt(row.unique_transactions || '0'),
        tradingDays: parseInt(row.trading_days || '0'),
        tradesPerDay: parseFloat(row.trades_per_day || '0'),
        favoriteToken: row.favorite_token,
        favoriteTokenTrades: parseInt(row.favorite_token_trades || '0'),
        firstBlock: parseInt(row.first_block || '0'),
        lastBlock: parseInt(row.last_block || '0'),
        firstTrade: row.first_trade ? new Date(row.first_trade).toLocaleDateString() : null,
        lastTrade: row.last_trade ? new Date(row.last_trade).toLocaleDateString() : null
      }))

      return NextResponse.json({
        success: true,
        data: {
          performers: topPerformers,
          metric: metric,
          total: topPerformers.length,
          source: 'paraswap'
        }
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('ParaSwap top performers API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch ParaSwap top performers'
    }, { status: 500 })
  }
}