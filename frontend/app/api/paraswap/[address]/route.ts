import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

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

      // Get comprehensive ParaSwap trading analysis
      const analysisQuery = `
        WITH user_stats AS (
          SELECT 
            real_user,
            COUNT(*) as total_trades,
            SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN label = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
            COUNT(DISTINCT token_address) as unique_tokens,
            COUNT(DISTINCT tx_hash) as unique_transactions,
            MIN(block_number) as first_block,
            MAX(block_number) as last_block,
            MIN(created_at) as first_trade,
            MAX(created_at) as last_trade
          FROM paraswap_arena_users 
          WHERE LOWER(real_user) = LOWER($1)
          GROUP BY real_user
        ),
        token_diversity AS (
          SELECT 
            COUNT(DISTINCT token_address) as total_tokens_traded,
            token_address as most_traded_token,
            COUNT(*) as most_traded_count
          FROM paraswap_arena_users
          WHERE LOWER(real_user) = LOWER($1)
          GROUP BY token_address
          ORDER BY COUNT(*) DESC
          LIMIT 1
        )
        SELECT 
          us.*,
          td.total_tokens_traded,
          td.most_traded_token,
          td.most_traded_count,
          CASE 
            WHEN us.total_trades > 0 
            THEN (us.buy_trades::float / us.total_trades * 100)
            ELSE 0 
          END as buy_percentage
        FROM user_stats us
        CROSS JOIN token_diversity td
      `

      const analysisResult = await client.query(analysisQuery, [address])
      
      if (analysisResult.rows.length === 0) {
        return NextResponse.json({
          success: false,
          error: 'No ParaSwap trading data found for this wallet'
        }, { status: 404 })
      }

      const stats = analysisResult.rows[0]

      // Get recent ParaSwap trades
      const recentTradesQuery = `
        SELECT 
          pau.label as trade_type,
          pau.token_address,
          pau.amount,
          pau.block_number,
          pau.tx_hash,
          pau.created_at
        FROM paraswap_arena_users pau
        WHERE LOWER(pau.real_user) = LOWER($1)
        ORDER BY pau.block_number DESC, pau.created_at DESC
        LIMIT 20
      `

      const recentTradesResult = await client.query(recentTradesQuery, [address])

      // Get top traded tokens for this user
      const topTokensQuery = `
        SELECT 
          token_address,
          COUNT(*) as trade_count,
          SUM(CASE WHEN label = 'BUY' THEN 1 ELSE 0 END) as buys,
          SUM(CASE WHEN label = 'SELL' THEN 1 ELSE 0 END) as sells
        FROM paraswap_arena_users
        WHERE LOWER(real_user) = LOWER($1)
        GROUP BY token_address
        ORDER BY trade_count DESC
        LIMIT 10
      `

      const topTokensResult = await client.query(topTokensQuery, [address])

      // Format the response
      const userData = {
        address: address,
        label: walletLabel,
        totalTrades: parseInt(stats.total_trades || '0'),
        buyTrades: parseInt(stats.buy_trades || '0'),
        sellTrades: parseInt(stats.sell_trades || '0'),
        buyPercentage: parseFloat(stats.buy_percentage || '0'),
        uniqueTokens: parseInt(stats.unique_tokens || '0'),
        uniqueTransactions: parseInt(stats.unique_transactions || '0'),
        firstBlock: parseInt(stats.first_block || '0'),
        lastBlock: parseInt(stats.last_block || '0'),
        firstTradeDate: stats.first_trade ? new Date(stats.first_trade).toLocaleDateString() : 'N/A',
        lastTradeDate: stats.last_trade ? new Date(stats.last_trade).toLocaleDateString() : 'N/A',
        mostTradedToken: stats.most_traded_token,
        mostTradedCount: parseInt(stats.most_traded_count || '0'),
        recentTrades: recentTradesResult.rows.map(trade => ({
          date: new Date(trade.created_at).toLocaleDateString(),
          type: trade.trade_type,
          tokenAddress: trade.token_address,
          amount: trade.amount?.toString() || '0',
          blockNumber: parseInt(trade.block_number || '0'),
          txHash: trade.tx_hash
        })),
        topTokens: topTokensResult.rows.map(token => ({
          address: token.token_address,
          tradeCount: parseInt(token.trade_count || '0'),
          buys: parseInt(token.buys || '0'),
          sells: parseInt(token.sells || '0'),
          buyPercentage: Math.round((parseInt(token.buys || '0') / parseInt(token.trade_count || '1')) * 100)
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
    console.error('ParaSwap wallet analysis API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch ParaSwap wallet analysis'
    }, { status: 500 })
  }
} 