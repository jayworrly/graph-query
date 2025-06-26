import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../../lib/database'

export async function GET(
  request: NextRequest,
  { params }: { params: { address: string } }
) {
  try {
    const { address } = params

    if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid wallet address format'
      }, { status: 400 })
    }

    const client = await pool.connect()

    try {
      // Get wallet label if available
      const labelQuery = `
        SELECT DISTINCT wl.label
        FROM wallet_labels wl
        WHERE LOWER(wl.wallet_address) = LOWER($1)
        LIMIT 1
      `
      const labelResult = await client.query(labelQuery, [address])
      const walletLabel = labelResult.rows[0]?.label

      // Get comprehensive wallet analysis
      const analysisQuery = `
        WITH wallet_stats AS (
          SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            SUM(avax_amount) as total_volume,
            AVG(avax_amount) as avg_trade_size,
            MIN(timestamp) as first_trade,
            MAX(timestamp) as last_trade
          FROM bonding_events 
          WHERE LOWER(user_address) = LOWER($1)
        ),
        pnl_stats AS (
          SELECT 
            SUM(realized_pnl) as total_pnl,
            COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as profitable_trades,
            COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losing_trades,
            MAX(realized_pnl) as biggest_win,
            MIN(realized_pnl) as biggest_loss
          FROM (
            SELECT 
              token_address,
              user_address,
              SUM(CASE WHEN trade_type = 'BUY' THEN -avax_amount ELSE avax_amount END) as realized_pnl
            FROM bonding_events 
            WHERE LOWER(user_address) = LOWER($1)
            GROUP BY token_address, user_address
                          HAVING SUM(CASE WHEN trade_type = 'BUY' THEN -1 ELSE 1 END) >= 0
          ) pnl_calc
        )
        SELECT 
          ws.*,
          ps.total_pnl,
          ps.profitable_trades,
          ps.losing_trades,
          ps.biggest_win,
          ps.biggest_loss,
          CASE 
            WHEN ws.total_trades > 0 
            THEN (ps.profitable_trades::float / ws.total_trades * 100)
            ELSE 0 
          END as win_rate
        FROM wallet_stats ws
        CROSS JOIN pnl_stats ps
      `

      const analysisResult = await client.query(analysisQuery, [address])
      
      if (analysisResult.rows.length === 0) {
        return NextResponse.json({
          success: false,
          error: 'No trading data found for this wallet'
        }, { status: 404 })
      }

      const stats = analysisResult.rows[0]

      // Get recent trades
      const recentTradesQuery = `
        SELECT 
          be.trade_type,
          be.token_address,
          td.name as token_name,
          td.symbol as token_symbol,
          be.avax_amount,
          be.timestamp,
          CASE 
            WHEN be.trade_type = 'SELL' THEN 
              (SELECT SUM(b2.avax_amount) 
               FROM bonding_events b2 
               WHERE b2.token_address = be.token_address 
               AND LOWER(b2.user_address) = LOWER(be.user_address)
               AND b2.trade_type = 'BUY' 
               AND b2.timestamp <= be.timestamp) - be.avax_amount
            ELSE 0
          END as estimated_pnl
        FROM bonding_events be
        LEFT JOIN token_deployments td ON be.token_address = td.id
        WHERE LOWER(be.user_address) = LOWER($1)
        ORDER BY be.timestamp DESC
        LIMIT 20
      `

      const recentTradesResult = await client.query(recentTradesQuery, [address])

      // Format the response
      const walletData = {
        address: address,
        label: walletLabel,
        totalPnl: parseFloat(stats.total_pnl || '0'),
        totalTrades: parseInt(stats.total_trades || '0'),
        winRate: parseFloat(stats.win_rate || '0'),
        totalVolume: parseFloat(stats.total_volume || '0'),
        avgTradeSize: parseFloat(stats.avg_trade_size || '0'),
        firstTradeDate: stats.first_trade ? new Date(stats.first_trade).toLocaleDateString() : 'N/A',
        lastTradeDate: stats.last_trade ? new Date(stats.last_trade).toLocaleDateString() : 'N/A',
        profitableTrades: parseInt(stats.profitable_trades || '0'),
        losingTrades: parseInt(stats.losing_trades || '0'),
        biggestWin: parseFloat(stats.biggest_win || '0'),
        biggestLoss: parseFloat(stats.biggest_loss || '0'),
        recentTrades: recentTradesResult.rows.map(trade => ({
          date: new Date(trade.timestamp).toLocaleDateString(),
          type: trade.trade_type,
          token: trade.token_symbol || trade.token_name || 'Unknown',
          amount: parseFloat(trade.avax_amount),
          pnl: parseFloat(trade.estimated_pnl || '0')
        }))
      }

      return NextResponse.json({
        success: true,
        data: walletData
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('Wallet analysis API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch wallet analysis'
    }, { status: 500 })
  }
} 