import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '10')
    const metric = searchParams.get('metric') || 'trades'

    const client = await pool.connect()

    try {
      // Get top ParaSwap performers based on trading activity
      const topPerformersQuery = `
        WITH user_stats AS (
          SELECT 
            real_user as address,
            COUNT(*) as total_trades,
            SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN label = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            COUNT(DISTINCT token_address) as unique_tokens,
            COUNT(DISTINCT tx_hash) as unique_transactions,
            CASE 
              WHEN COUNT(*) > 0 
              THEN (SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END)::float / COUNT(*) * 100)
              ELSE 0 
            END as buy_percentage
          FROM paraswap_arena_users 
          GROUP BY real_user
          HAVING COUNT(*) >= 5  -- At least 5 trades to be considered
        )
        SELECT 
          us.address,
          wl.label,
          us.total_trades,
          us.buy_trades,
          us.sell_trades,
          us.unique_tokens,
          us.unique_transactions,
          us.buy_percentage
        FROM user_stats us
        LEFT JOIN wallet_labels wl ON LOWER(us.address) = LOWER(wl.wallet_address)
        ORDER BY ${metric === 'trades' ? 'us.total_trades' : 'us.unique_tokens'} DESC
        LIMIT $1
      `

      const result = await client.query(topPerformersQuery, [limit])

      const performers = result.rows.map((row, index) => ({
        address: row.address,
        label: row.label,
        totalTrades: parseInt(row.total_trades || '0'),
        buyTrades: parseInt(row.buy_trades || '0'),
        sellTrades: parseInt(row.sell_trades || '0'),
        uniqueTokens: parseInt(row.unique_tokens || '0'),
        buyPercentage: parseFloat(row.buy_percentage || '0')
      }))

      return NextResponse.json({
        success: true,
        data: {
          performers,
          metric: metric,
          timestamp: new Date().toISOString()
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