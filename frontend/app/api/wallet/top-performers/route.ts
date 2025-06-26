import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const metric = searchParams.get('metric') || 'pnl' // pnl, volume, trades, winrate

    const client = await pool.connect()

    try {
      let orderClause = ''
      switch (metric) {
        case 'volume':
          orderClause = 'total_volume DESC'
          break
        case 'trades':
          orderClause = 'total_trades DESC'
          break
        case 'winrate':
          orderClause = 'win_rate DESC, total_trades DESC'
          break
        default:
          orderClause = 'total_pnl DESC'
      }

      const topPerformersQuery = `
        WITH wallet_performance AS (
          SELECT 
            be.user_address,
            COUNT(*) as total_trades,
            SUM(be.avax_amount) as total_volume,
            SUM(CASE WHEN be.trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN be.trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            MIN(be.timestamp) as first_trade,
            MAX(be.timestamp) as last_trade
          FROM bonding_events be
          GROUP BY be.user_address
          HAVING COUNT(*) >= 5  -- Only include wallets with at least 5 trades
        ),
        wallet_pnl AS (
          SELECT 
            user_address,
            SUM(realized_pnl) as total_pnl,
            COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as profitable_positions,
            COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losing_positions,
            AVG(realized_pnl) as avg_pnl,
            MAX(realized_pnl) as best_trade,
            MIN(realized_pnl) as worst_trade
          FROM (
            SELECT 
              user_address,
              token_address,
              SUM(CASE WHEN trade_type = 'BUY' THEN -avax_amount ELSE avax_amount END) as realized_pnl
            FROM bonding_events 
            GROUP BY user_address, token_address
            HAVING SUM(CASE WHEN trade_type = 'BUY' THEN -1 ELSE 1 END) >= 0  -- Only closed positions
          ) pnl_calc
          GROUP BY user_address
        )
        SELECT 
          wp.user_address,
          wl.label,
          wp.total_trades,
          wp.total_volume,
          wp.buy_trades,
          wp.sell_trades,
          wpnl.total_pnl,
          wpnl.profitable_positions,
          wpnl.losing_positions,
          wpnl.avg_pnl,
          wpnl.best_trade,
          wpnl.worst_trade,
          CASE 
            WHEN wpnl.profitable_positions + wpnl.losing_positions > 0 
            THEN (wpnl.profitable_positions::float / (wpnl.profitable_positions + wpnl.losing_positions) * 100)
            ELSE 0 
          END as win_rate,
          wp.first_trade,
          wp.last_trade
        FROM wallet_performance wp
        JOIN wallet_pnl wpnl ON wp.user_address = wpnl.user_address
        LEFT JOIN wallet_labels wl ON LOWER(wl.wallet_address) = LOWER(wp.user_address)
        WHERE wpnl.total_pnl IS NOT NULL
        ORDER BY ${orderClause}
        LIMIT $1
      `

      const result = await client.query(topPerformersQuery, [limit])

      const topPerformers = result.rows.map(row => ({
        address: row.user_address,
        label: row.label,
        totalPnl: parseFloat(row.total_pnl || '0'),
        totalTrades: parseInt(row.total_trades || '0'),
        totalVolume: parseFloat(row.total_volume || '0'),
        winRate: parseFloat(row.win_rate || '0'),
        profitablePositions: parseInt(row.profitable_positions || '0'),
        losingPositions: parseInt(row.losing_positions || '0'),
        avgPnl: parseFloat(row.avg_pnl || '0'),
        bestTrade: parseFloat(row.best_trade || '0'),
        worstTrade: parseFloat(row.worst_trade || '0'),
        firstTrade: row.first_trade ? new Date(row.first_trade).toLocaleDateString() : null,
        lastTrade: row.last_trade ? new Date(row.last_trade).toLocaleDateString() : null
      }))

      return NextResponse.json({
        success: true,
        data: {
          performers: topPerformers,
          metric: metric,
          total: topPerformers.length
        }
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('Top performers API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch top performers'
    }, { status: 500 })
  }
} 