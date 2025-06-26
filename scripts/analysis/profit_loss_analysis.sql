-- ================================================================================
-- WALLET PROFIT/LOSS ANALYSIS QUERIES
-- ================================================================================
-- This file contains comprehensive queries to analyze which wallets are making 
-- profit and which are losing money based on bonding_events data.
-- ================================================================================

-- ===========================================
-- 1. SIMPLE PROFIT/LOSS OVERVIEW
-- ===========================================
-- Basic analysis using the existing user_activity table with pre-calculated P&L

SELECT 
    user_address as wallet,
    total_trades,
    ROUND(total_volume_avax::numeric, 4) as total_volume_avax,
    ROUND(total_investment_avax::numeric, 4) as total_invested_avax,
    ROUND(realized_pnl_avax::numeric, 4) as realized_profit_loss,
    ROUND(unrealized_pnl_avax::numeric, 4) as unrealized_profit_loss,
    ROUND(total_pnl_avax::numeric, 4) as total_profit_loss,
    ROUND(portfolio_roi::numeric, 2) as roi_percentage,
    CASE 
        WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
        WHEN total_pnl_avax < 0 THEN 'LOSING'
        ELSE 'BREAK_EVEN'
    END as status,
    profitable_trades,
    losing_trades,
    ROUND(win_rate::numeric, 2) as win_rate_percent
FROM user_activity 
ORDER BY total_pnl_avax DESC;

-- ===========================================
-- 2. MANUAL CALCULATION FROM BONDING EVENTS
-- ===========================================
-- Calculate profit/loss by analyzing buy/sell trades from bonding_events table

WITH user_trades AS (
    SELECT 
        user_address,
        token_address,
        trade_type,
        avax_amount,
        token_amount,
        price_avax,
        timestamp,
        -- Calculate effective price per token (including fees)
        (avax_amount + protocol_fee + creator_fee + referral_fee) / token_amount as effective_price
    FROM bonding_events
    ORDER BY user_address, token_address, timestamp
),

user_positions AS (
    SELECT 
        user_address,
        token_address,
        SUM(CASE WHEN trade_type = 'BUY' THEN token_amount ELSE 0 END) as total_bought,
        SUM(CASE WHEN trade_type = 'SELL' THEN token_amount ELSE 0 END) as total_sold,
        SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount ELSE 0 END) as total_buy_cost,
        SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount ELSE 0 END) as total_sell_revenue,
        COUNT(*) as total_trades,
        SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
        SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades
    FROM user_trades
    GROUP BY user_address, token_address
),

user_portfolio_summary AS (
    SELECT 
        user_address,
        COUNT(DISTINCT token_address) as unique_tokens_traded,
        SUM(total_trades) as total_trades,
        SUM(total_buy_cost) as total_invested,
        SUM(total_sell_revenue) as total_revenue,
        SUM(total_sell_revenue - total_buy_cost) as realized_pnl,
        SUM(total_bought - total_sold) as net_tokens_held
    FROM user_positions
    GROUP BY user_address
)

SELECT 
    user_address as wallet,
    unique_tokens_traded,
    total_trades,
    ROUND(total_invested::numeric, 4) as total_invested_avax,
    ROUND(total_revenue::numeric, 4) as total_revenue_avax,
    ROUND(realized_pnl::numeric, 4) as realized_profit_loss_avax,
    ROUND((realized_pnl / NULLIF(total_invested, 0) * 100)::numeric, 2) as roi_percentage,
    CASE 
        WHEN realized_pnl > 0 THEN 'PROFITABLE' 
        WHEN realized_pnl < 0 THEN 'LOSING'
        ELSE 'BREAK_EVEN'
    END as status,
    ROUND(net_tokens_held::numeric, 4) as net_tokens_still_held
FROM user_portfolio_summary
WHERE total_invested > 0  -- Only include wallets that have actually traded
ORDER BY realized_pnl DESC;

-- ===========================================
-- 3. TOP PROFITABLE WALLETS
-- ===========================================

SELECT 
    user_address as wallet,
    ROUND(total_pnl_avax::numeric, 4) as total_profit_avax,
    ROUND(portfolio_roi::numeric, 2) as roi_percentage,
    total_trades,
    profitable_trades,
    losing_trades,
    ROUND(win_rate::numeric, 2) as win_rate_percent,
    ROUND(largest_win_avax::numeric, 4) as biggest_win_avax,
    unique_tokens_traded
FROM user_activity 
WHERE total_pnl_avax > 0
ORDER BY total_pnl_avax DESC
LIMIT 20;

-- ===========================================
-- 4. BIGGEST LOSERS
-- ===========================================

SELECT 
    user_address as wallet,
    ROUND(total_pnl_avax::numeric, 4) as total_loss_avax,
    ROUND(portfolio_roi::numeric, 2) as roi_percentage,
    total_trades,
    profitable_trades,
    losing_trades,
    ROUND(win_rate::numeric, 2) as win_rate_percent,
    ROUND(largest_loss_avax::numeric, 4) as biggest_loss_avax,
    unique_tokens_traded
FROM user_activity 
WHERE total_pnl_avax < 0
ORDER BY total_pnl_avax ASC
LIMIT 20;

-- ===========================================
-- 5. DETAILED PER-TOKEN PROFIT/LOSS
-- ===========================================

SELECT 
    utp.user_address as wallet,
    td.name as token_name,
    td.symbol as token_symbol,
    utp.token_address,
    ROUND(utp.current_balance::numeric, 4) as current_holdings,
    ROUND(utp.total_bought::numeric, 4) as total_bought,
    ROUND(utp.total_sold::numeric, 4) as total_sold,
    ROUND(utp.average_buy_price::numeric, 8) as avg_buy_price,
    ROUND(utp.average_sell_price::numeric, 8) as avg_sell_price,
    ROUND(utp.realized_pnl_avax::numeric, 4) as realized_pnl,
    ROUND(utp.unrealized_pnl_avax::numeric, 4) as unrealized_pnl,
    ROUND(utp.total_pnl_avax::numeric, 4) as total_pnl,
    utp.is_open as position_open,
    utp.total_trades,
    utp.total_buys,
    utp.total_sells
FROM user_token_positions utp
JOIN token_deployments td ON utp.token_address = td.id
WHERE utp.total_pnl_avax != 0  -- Only show positions with profit/loss
ORDER BY utp.total_pnl_avax DESC;

-- ===========================================
-- 6. TRADING PERFORMANCE SUMMARY
-- ===========================================

SELECT 
    CASE 
        WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
        WHEN total_pnl_avax < 0 THEN 'LOSING'
        ELSE 'BREAK_EVEN'
    END as trader_category,
    COUNT(*) as number_of_wallets,
    ROUND(AVG(total_pnl_avax)::numeric, 4) as avg_pnl_per_wallet,
    ROUND(SUM(total_pnl_avax)::numeric, 4) as total_category_pnl,
    ROUND(AVG(portfolio_roi)::numeric, 2) as avg_roi_percentage,
    ROUND(AVG(win_rate)::numeric, 2) as avg_win_rate,
    SUM(total_trades) as total_trades_in_category
FROM user_activity
GROUP BY 
    CASE 
        WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
        WHEN total_pnl_avax < 0 THEN 'LOSING'
        ELSE 'BREAK_EVEN'
    END
ORDER BY total_category_pnl DESC;

-- ===========================================
-- 7. RECENT TRADING ACTIVITY WITH P&L
-- ===========================================

SELECT 
    be.user_address as wallet,
    be.token_address,
    td.name as token_name,
    be.trade_type,
    ROUND(be.avax_amount::numeric, 4) as avax_amount,
    ROUND(be.token_amount::numeric, 4) as token_amount,
    ROUND(be.price_avax::numeric, 8) as price_per_token,
    TO_TIMESTAMP(be.timestamp) as trade_time,
    be.transaction_hash,
    -- Get current P&L for this user
    ua.total_pnl_avax as current_total_pnl,
    ua.portfolio_roi as current_roi_percentage
FROM bonding_events be
JOIN token_deployments td ON be.token_address = td.id
LEFT JOIN user_activity ua ON be.user_address = ua.user_address
ORDER BY be.timestamp DESC
LIMIT 50;

-- ===========================================
-- 8. WALLET PERFORMANCE RANKING
-- ===========================================

SELECT 
    ROW_NUMBER() OVER (ORDER BY total_pnl_avax DESC) as rank,
    user_address as wallet,
    ROUND(total_pnl_avax::numeric, 4) as total_profit_loss,
    ROUND(portfolio_roi::numeric, 2) as roi_percentage,
    total_trades,
    ROUND(win_rate::numeric, 2) as win_rate_percent,
    unique_tokens_traded,
    CASE 
        WHEN total_pnl_avax > 100 THEN 'WHALE_WINNER'
        WHEN total_pnl_avax > 10 THEN 'BIG_WINNER'
        WHEN total_pnl_avax > 1 THEN 'WINNER'
        WHEN total_pnl_avax > 0 THEN 'SMALL_WINNER'
        WHEN total_pnl_avax = 0 THEN 'BREAK_EVEN'
        WHEN total_pnl_avax > -1 THEN 'SMALL_LOSER'
        WHEN total_pnl_avax > -10 THEN 'LOSER'
        WHEN total_pnl_avax > -100 THEN 'BIG_LOSER'
        ELSE 'WHALE_LOSER'
    END as trader_tier
FROM user_activity
WHERE total_trades > 0
ORDER BY total_pnl_avax DESC;

-- ===========================================
-- 9. QUICK STATISTICS
-- ===========================================

SELECT 
    'OVERALL_STATISTICS' as metric_type,
    COUNT(*) as total_active_wallets,
    SUM(CASE WHEN total_pnl_avax > 0 THEN 1 ELSE 0 END) as profitable_wallets,
    SUM(CASE WHEN total_pnl_avax < 0 THEN 1 ELSE 0 END) as losing_wallets,
    SUM(CASE WHEN total_pnl_avax = 0 THEN 1 ELSE 0 END) as break_even_wallets,
    ROUND((SUM(CASE WHEN total_pnl_avax > 0 THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 2) as percent_profitable,
    ROUND(SUM(total_pnl_avax)::numeric, 4) as total_ecosystem_pnl,
    ROUND(AVG(total_pnl_avax)::numeric, 4) as avg_wallet_pnl
FROM user_activity
WHERE total_trades > 0; 