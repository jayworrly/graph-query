# Database Schema Reference

This document provides the correct table names and column references for the Arena Terminal frontend to prevent common naming errors.

## 🗄️ Table Names (Correct)

| Table | Description | Common Mistake |
|-------|-------------|----------------|
| `bonding_events` | Trading activity data | ❌ `bonding_event` |
| `token_deployments` | Token information | ❌ `token_deployment` |
| `wallet_labels` | Wallet identification | ❌ `wallet_label` |
| `user_activity` | User performance metrics | ❌ `user_activities` |

## 📋 Column Names (Correct)

### bonding_events Table
| Column | Type | Description | Common Mistake |
|--------|------|-------------|----------------|
| `user_address` | VARCHAR | Wallet address | ❌ `trader` |
| `token_address` | VARCHAR | Token contract address | ✅ Correct |
| `trade_type` | VARCHAR | 'BUY' or 'SELL' | ❌ `event_type` |
| `avax_amount` | NUMERIC | AVAX amount traded | ✅ Correct |
| `token_amount` | NUMERIC | Token amount traded | ✅ Correct |
| `price_avax` | NUMERIC | Price per token | ✅ Correct |
| `timestamp` | BIGINT | Unix timestamp | ❌ `block_timestamp` |
| `transaction_hash` | VARCHAR | Transaction hash | ✅ Correct |
| `protocol_fee` | NUMERIC | Protocol fee | ✅ Correct |
| `creator_fee` | NUMERIC | Creator fee | ✅ Correct |
| `referral_fee` | NUMERIC | Referral fee | ✅ Correct |

### token_deployments Table
| Column | Type | Description | Common Mistake |
|--------|------|-------------|----------------|
| `id` | VARCHAR | Token contract address (PK) | ❌ `token_address` |
| `name` | VARCHAR | Token name | ✅ Correct |
| `symbol` | VARCHAR | Token symbol | ✅ Correct |
| `creator` | VARCHAR | Creator wallet address | ✅ Correct |
| `total_supply` | NUMERIC | Total token supply | ✅ Correct |

### wallet_labels Table
| Column | Type | Description | Common Mistake |
|--------|------|-------------|----------------|
| `wallet_address` | VARCHAR | Wallet address (PK) | ✅ Correct |
| `label` | VARCHAR | Human-readable label | ✅ Correct |
| `user_type` | VARCHAR | User category | ✅ Correct |
| `is_verified` | BOOLEAN | Verification status | ✅ Correct |
| `risk_level` | VARCHAR | Risk assessment | ✅ Correct |
| `tags` | TEXT[] | Array of tags | ✅ Correct |

### user_activity Table
| Column | Type | Description | Common Mistake |
|--------|------|-------------|----------------|
| `user_address` | VARCHAR | Wallet address | ✅ Correct |
| `total_trades` | INTEGER | Total number of trades | ✅ Correct |
| `total_pnl_avax` | NUMERIC | Total profit/loss | ✅ Correct |
| `portfolio_roi` | NUMERIC | Return on investment % | ✅ Correct |
| `win_rate` | NUMERIC | Percentage of profitable trades | ✅ Correct |

## 🔗 Common JOIN Patterns

### Wallet Analysis Query
```sql
-- Correct way to join bonding_events with token_deployments
FROM bonding_events be
LEFT JOIN token_deployments td ON be.token_address = td.id

-- Correct way to join with wallet_labels
LEFT JOIN wallet_labels wl ON LOWER(be.user_address) = LOWER(wl.wallet_address)
```

### User Activity Query
```sql
-- Correct way to join user_activity with wallet_labels
FROM user_activity ua
LEFT JOIN wallet_labels wl ON ua.user_address = wl.wallet_address
```

## ⚠️ Common Errors to Avoid

1. **Table Names:**
   - ❌ `FROM bonding_event` → ✅ `FROM bonding_events`
   - ❌ `FROM token_deployment` → ✅ `FROM token_deployments`

2. **Column Names:**
   - ❌ `WHERE trader = '...'` → ✅ `WHERE user_address = '...'`
   - ❌ `event_type = 'BUY'` → ✅ `trade_type = 'BUY'`
   - ❌ `block_timestamp` → ✅ `timestamp`

3. **JOIN Conditions:**
   - ❌ `ON be.token_address = td.token_address` → ✅ `ON be.token_address = td.id`
   - ❌ `ON be.trader = wl.wallet_address` → ✅ `ON be.user_address = wl.wallet_address`

## 🧪 Testing Your Queries

Before implementing in the frontend, test your SQL queries using the scripts in the `scripts/` directory:

```bash
# Test database connection and schema
python scripts/utils/check_schema.py

# Check data availability
python scripts/utils/check_data.py

# Test wallet analysis
python scripts/analysis/lookup_specific_wallet.py
```

## 📝 Quick Reference

**Always use these exact names:**
- Tables: `bonding_events`, `token_deployments`, `wallet_labels`, `user_activity`
- User column: `user_address` (not `trader`)
- Trade type: `trade_type` (not `event_type`)
- Timestamp: `timestamp` (not `block_timestamp`)
- Token join: `be.token_address = td.id` (not `td.token_address`) 