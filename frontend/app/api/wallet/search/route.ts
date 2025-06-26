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
      // Search for wallets by address or label
      const searchQuery = `
        SELECT DISTINCT
          wl.wallet_address,
          wl.label,
          COUNT(be.id) as trade_count,
          MAX(be.timestamp) as last_activity
        FROM wallet_labels wl
        LEFT JOIN bonding_events be ON LOWER(be.user_address) = LOWER(wl.wallet_address)
        WHERE 
          LOWER(wl.wallet_address) LIKE LOWER($1) OR
          LOWER(wl.label) LIKE LOWER($1)
        GROUP BY wl.wallet_address, wl.label
        ORDER BY 
          CASE WHEN LOWER(wl.wallet_address) = LOWER($2) THEN 1 ELSE 2 END,
          trade_count DESC,
          last_activity DESC NULLS LAST
        LIMIT $3
      `

      const searchPattern = `%${query}%`
      const exactQuery = query

      const result = await client.query(searchQuery, [searchPattern, exactQuery, limit])

      const wallets = result.rows.map(row => ({
        address: row.wallet_address,
        label: row.label,
        tradeCount: parseInt(row.trade_count || '0'),
        lastActivity: row.last_activity ? new Date(row.last_activity).toLocaleDateString() : null
      }))

      return NextResponse.json({
        success: true,
        data: {
          wallets,
          total: wallets.length
        }
      })

    } finally {
      client.release()
    }

  } catch (error) {
    console.error('Wallet search API error:', error)
    return NextResponse.json({
      success: false,
      error: 'Failed to search wallets'
    }, { status: 500 })
  }
} 