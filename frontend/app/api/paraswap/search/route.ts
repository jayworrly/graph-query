import { NextRequest, NextResponse } from 'next/server'
import pool from '../../../../lib/database'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q')
    const limit = parseInt(searchParams.get('limit') || '5')

    if (!query || query.length < 3) {
      return NextResponse.json({
        success: true,
        data: { users: [] }
      })
    }

    const client = await pool.connect()

    try {
      // Search ParaSwap users by wallet address or label
      const searchQuery = `
        WITH user_stats AS (
          SELECT 
            real_user as address,
            COUNT(*) as trade_count
          FROM paraswap_arena_users 
          GROUP BY real_user
        )
        SELECT DISTINCT
          us.address,
          wl.label,
          us.trade_count
        FROM user_stats us
        LEFT JOIN wallet_labels wl ON LOWER(us.address) = LOWER(wl.wallet_address)
        WHERE 
          LOWER(us.address) LIKE LOWER($1) OR 
          LOWER(wl.label) LIKE LOWER($1)
        ORDER BY 
          CASE 
            WHEN LOWER(us.address) = LOWER($2) THEN 1
            WHEN LOWER(wl.label) = LOWER($2) THEN 2
            WHEN LOWER(us.address) LIKE LOWER($3) THEN 3
            WHEN LOWER(wl.label) LIKE LOWER($3) THEN 4
            ELSE 5
          END,
          us.trade_count DESC
        LIMIT $4
      `

      const searchPattern = `%${query}%`
      const exactMatch = query
      const prefixMatch = `${query}%`

      const result = await client.query(searchQuery, [
        searchPattern, exactMatch, prefixMatch, limit
      ])

      const users = result.rows.map(row => ({
        address: row.address,
        label: row.label,
        tradeCount: parseInt(row.trade_count || '0')
      }))

      return NextResponse.json({
        success: true,
        data: { users }
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('ParaSwap search API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to search ParaSwap users'
    }, { status: 500 })
  }
} 