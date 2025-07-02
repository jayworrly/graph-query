-- subgraph_sync_status

            SELECT 
                COUNT(*) as total_paraswap_trades,
                MAX(block_number) as latest_block_indexed,
                MAX(timestamp) as latest_timestamp
            FROM paraswap_trades
        ;

-- arena_token_activity

            SELECT 
                COUNT(DISTINCT arena_token) as active_arena_tokens,
                SUM(CASE WHEN timestamp > EXTRACT(epoch FROM NOW() - INTERVAL '24 hours') THEN 1 ELSE 0 END) as trades_24h
            FROM paraswap_trades 
            WHERE arena_token IS NOT NULL
        ;

-- indexing_performance

            SELECT 
                DATE_TRUNC('hour', TO_TIMESTAMP(timestamp)) as hour,
                COUNT(*) as trades_per_hour
            FROM paraswap_trades 
            WHERE timestamp > EXTRACT(epoch FROM NOW() - INTERVAL '24 hours')
            GROUP BY hour
            ORDER BY hour DESC
        ;

