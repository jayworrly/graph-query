import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q')
    const limit = parseInt(searchParams.get('limit') || '10')

    if (!query || query.length < 3) {
      return NextResponse.json({
        success: false,
        error: 'Search query must be at least 3 characters'
      }, { status: 400 })
    }

    const client = await pool.connect()

    try {
      // Search for ParaSwap users by address, include their trading stats
      const searchQuery = `
        SELECT 
          pau.real_user as address,
          wl.label,
          COUNT(*) as trade_count,
          SUM(CASE WHEN pau.label = 'BUY' THEN 1 ELSE 0 END) as buy_count,
          SUM(CASE WHEN pau.label = 'SELL' THEN 1 ELSE 0 END) as sell_count,
          COUNT(DISTINCT pau.token_address) as unique_tokens,
          MAX(pau.created_at) as last_activity
        FROM paraswap_arena_users pau
        LEFT JOIN wallet_labels wl ON LOWER(wl.wallet_address) = LOWER(pau.real_user)
        WHERE LOWER(pau.real_user) LIKE LOWER($1) OR LOWER(wl.label) LIKE LOWER($1)
        GROUP BY pau.real_user, wl.label
        ORDER BY 
          CASE WHEN LOWER(pau.real_user) = LOWER($2) THEN 1 ELSE 2 END,
          trade_count DESC,
          last_activity DESC NULLS LAST
        LIMIT $3
      `

      const searchPattern = `%${query}%`
      const exactQuery = query

      const result = await client.query(searchQuery, [searchPattern, exactQuery, limit])

      const users = result.rows.map(row => ({
        address: row.address,
        label: row.label,
        tradeCount: parseInt(row.trade_count || '0'),
        buyCount: parseInt(row.buy_count || '0'),
        sellCount: parseInt(row.sell_count || '0'),
        uniqueTokens: parseInt(row.unique_tokens || '0'),
        lastActivity: row.last_activity ? new Date(row.last_activity).toLocaleDateString() : null
      }))

      return NextResponse.json({
        success: true,
        data: {
          users,
          total: users.length,
          source: 'paraswap'
        }
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('ParaSwap user search API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to search ParaSwap users'
    }, { status: 500 })
  }
} 