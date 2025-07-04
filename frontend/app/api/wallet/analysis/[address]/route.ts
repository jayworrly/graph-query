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

      // Get comprehensive bonding curve analysis with proper wei conversion and token symbols
      const analysisQuery = `
        WITH user_trades AS (
          SELECT 
            be.user_address,
            be.token_address,
            be.trade_type,
            be.avax_amount,
            be.token_amount,
            be.price_avax,
            be.protocol_fee,
            be.creator_fee,
            be.referral_fee,
            be.timestamp,
            be.transaction_hash,
            td.name as token_name,
            td.symbol as token_symbol,
            -- Calculate total cost including fees for BUY trades
            CASE 
              WHEN be.trade_type = 'BUY' THEN be.avax_amount + be.protocol_fee + be.creator_fee + be.referral_fee
              ELSE be.avax_amount - be.protocol_fee - be.creator_fee - be.referral_fee
            END as net_avax_amount
          FROM bonding_events be
          LEFT JOIN token_deployments td ON be.token_address = td.id
          WHERE LOWER(be.user_address) = LOWER($1)
        ),
        position_pnl AS (
          SELECT 
            token_address,
            token_name,
            token_symbol,
            COUNT(*) as trades,
            SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_buy_cost,
            SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) as total_sell_revenue,
            SUM(CASE WHEN trade_type = 'BUY' THEN token_amount ELSE 0 END) as tokens_bought,
            SUM(CASE WHEN trade_type = 'SELL' THEN token_amount ELSE 0 END) as tokens_sold,
            -- Calculate P&L: sell revenue - buy cost
            (SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) - 
             SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END)) as position_pnl
          FROM user_trades
          GROUP BY token_address, token_name, token_symbol
        ),
        wallet_summary AS (
          SELECT 
            COUNT(*) as total_trades,
            COUNT(DISTINCT token_address) as unique_tokens,
            SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as total_buys,
            SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as total_sells,
            SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_invested,
            SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) as total_revenue,
            SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) - 
            SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_pnl,
            AVG(net_avax_amount) as avg_trade_size,
            MIN(timestamp) as first_trade_time,
            MAX(timestamp) as last_trade_time
          FROM user_trades
        )
        SELECT 
          ws.*,
          -- Calculate win rate based on profitable positions
          (SELECT COUNT(*) FROM position_pnl WHERE position_pnl > 0) as profitable_trades,
          (SELECT COUNT(*) FROM position_pnl WHERE position_pnl < 0) as losing_trades,
          (SELECT MAX(position_pnl) FROM position_pnl) as biggest_win,
          (SELECT MIN(position_pnl) FROM position_pnl) as biggest_loss
        FROM wallet_summary ws
      `

      const analysisResult = await client.query(analysisQuery, [address])
      
      if (analysisResult.rows.length === 0) {
        return NextResponse.json({
          success: false,
          error: 'No bonding curve trading data found for this wallet'
        }, { status: 404 })
      }

      const stats = analysisResult.rows[0]

      // Get recent trades with token symbols
      const recentTradesQuery = `
        SELECT 
          be.trade_type,
          be.token_address,
          td.name as token_name,
          td.symbol as token_symbol,
          be.avax_amount,
          be.token_amount,
          be.price_avax,
          be.protocol_fee + be.creator_fee + be.referral_fee as total_fees,
          CASE 
            WHEN be.trade_type = 'BUY' THEN -(be.avax_amount + be.protocol_fee + be.creator_fee + be.referral_fee)
            ELSE be.avax_amount - be.protocol_fee - be.creator_fee - be.referral_fee
          END as pnl_impact,
          be.timestamp,
          be.transaction_hash
        FROM bonding_events be
        LEFT JOIN token_deployments td ON be.token_address = td.id
        WHERE LOWER(be.user_address) = LOWER($1)
        ORDER BY be.timestamp DESC
        LIMIT 20
      `

      const recentTradesResult = await client.query(recentTradesQuery, [address])

      // Get current holdings (tokens bought - tokens sold)
      const holdingsQuery = `
        SELECT 
          be.token_address,
          td.name as token_name,
          td.symbol as token_symbol,
          SUM(CASE WHEN be.trade_type = 'BUY' THEN be.token_amount ELSE -be.token_amount END) as current_balance,
          SUM(CASE WHEN be.trade_type = 'BUY' THEN be.avax_amount + be.protocol_fee + be.creator_fee + be.referral_fee ELSE 0 END) as total_cost,
          COUNT(*) as trades
        FROM bonding_events be
        LEFT JOIN token_deployments td ON be.token_address = td.id
        WHERE LOWER(be.user_address) = LOWER($1)
        GROUP BY be.token_address, td.name, td.symbol
        HAVING SUM(CASE WHEN be.trade_type = 'BUY' THEN be.token_amount ELSE -be.token_amount END) > 0
        ORDER BY current_balance DESC
        LIMIT 10
      `

      const holdingsResult = await client.query(holdingsQuery, [address])

      // Format the response
      const userData = {
        address: address,
        label: walletLabel,
        totalPnl: parseFloat(stats.total_pnl || '0'),
        totalTrades: parseInt(stats.total_trades || '0'),
        totalVolume: parseFloat(stats.total_invested || '0') + parseFloat(stats.total_revenue || '0'),
        winRate: stats.total_trades > 0 ? 
          ((parseInt(stats.profitable_trades || '0') / parseInt(stats.total_trades || '0')) * 100) : 0,
        avgTradeSize: parseFloat(stats.avg_trade_size || '0'),
        firstTradeDate: stats.first_trade_time ? 
          new Date(parseInt(stats.first_trade_time) * 1000).toLocaleDateString() : 'N/A',
        lastTradeDate: stats.last_trade_time ? 
          new Date(parseInt(stats.last_trade_time) * 1000).toLocaleDateString() : 'N/A',
        profitableTrades: parseInt(stats.profitable_trades || '0'),
        losingTrades: parseInt(stats.losing_trades || '0'),
        biggestWin: parseFloat(stats.biggest_win || '0'),
        biggestLoss: parseFloat(stats.biggest_loss || '0'),
        uniqueTokens: parseInt(stats.unique_tokens || '0'),
        currentHoldings: holdingsResult.rows.map(holding => ({
          tokenAddress: holding.token_address,
          tokenName: holding.token_name || 'Unknown Token',
          tokenSymbol: holding.token_symbol || 'UNK',
          balance: parseFloat(holding.current_balance || '0'),
          totalCost: parseFloat(holding.total_cost || '0'),
          trades: parseInt(holding.trades || '0')
        })),
        recentTrades: recentTradesResult.rows.map(trade => ({
          date: new Date(parseInt(trade.timestamp) * 1000).toLocaleDateString(),
          type: trade.trade_type,
          token: trade.token_symbol || trade.token_name || 'Unknown',
          tokenAddress: trade.token_address,
          amount: parseFloat(trade.avax_amount || '0'),
          tokenAmount: parseFloat(trade.token_amount || '0'),
          price: parseFloat(trade.price_avax || '0'),
          fees: parseFloat(trade.total_fees || '0'),
          pnl: parseFloat(trade.pnl_impact || '0'),
          txHash: trade.transaction_hash
        }))
      }

      return NextResponse.json({
        success: true,
        data: userData
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('Bonding curve wallet analysis API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch bonding curve wallet analysis'
    }, { status: 500 })
  }
}