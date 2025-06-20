# Arena Explore Page API Documentation

## Overview
The Arena Explore Page API provides endpoints to fetch token data for the three main categories displayed on the explore page:
- **New Pairs**: Recently created tokens
- **Close to Migration**: Tokens approaching bonding curve completion
- **Migrated Tokens**: Tokens that have successfully migrated to DEX trading

## API Endpoints

### 1. New Pairs
**Endpoint:** `GET /api/tokens/new-pairs`

**Description:** Fetches recently created tokens from the Arena platform.

**Query Parameters:**
- `limit` (optional): Number of tokens to return (default: 50, max: 100)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "address": "0x...",
      "name": "Token Name",
      "symbol": "SYMBOL",
      "decimals": 18,
      "totalSupply": "1000000000",
      "creator": "0x...",
      "launched": "2024-01-01T00:00:00.000Z",
      "price": 0.001,
      "marketCap": 10000,
      "volume24h": 0,
      "holders": 1,
      "liquidity": 0
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 2. Close to Migration
**Endpoint:** `GET /api/tokens/close-to-migration`

**Description:** Fetches tokens that are close to completing their bonding curve and migrating to DEX trading.

**Query Parameters:**
- `limit` (optional): Number of tokens to return (default: 20, max: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "address": "0x...",
      "name": "Token Name",
      "symbol": "SYMBOL",
      "decimals": 18,
      "creator": "0x...",
      "launched": "2024-01-01T00:00:00.000Z",
      "price": 0.085,
      "marketCap": 85000,
      "volume24h": 45000,
      "holders": 234,
      "migrationProgress": 94,
      "timeToMigration": "8 hours",
      "liquidity": 850
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 3. Migrated Tokens
**Endpoint:** `GET /api/tokens/migrated`

**Description:** Fetches tokens that have successfully migrated to DEX trading.

**Query Parameters:**
- `limit` (optional): Number of tokens to return (default: 20, max: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "address": "0x...",
      "name": "Token Name",
      "symbol": "SYMBOL",
      "decimals": 18,
      "creator": "0x...",
      "launched": "2024-01-01T00:00:00.000Z",
      "migratedAt": "2024-01-03T00:00:00.000Z",
      "price": 0.15,
      "marketCap": 150000,
      "volume24h": 85000,
      "holders": 456,
      "liquidity": 75000,
      "pairAddress": "0x..."
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 4. Token Search
**Endpoint:** `GET /api/tokens/search`

**Description:** Search for tokens by name, symbol, or address across all categories.

**Query Parameters:**
- `q` (required): Search query (minimum 2 characters)
- `limit` (optional): Number of results to return (default: 20, max: 50)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "address": "0x...",
      "name": "Token Name",
      "symbol": "SYMBOL",
      "decimals": 18,
      "creator": "0x...",
      "launched": "2024-01-01T00:00:00.000Z",
      "price": 0.001,
      "marketCap": 10000,
      "volume24h": 5000,
      "holders": 1,
      "category": "new-pairs",
      "liquidity": 0
    }
  ],
  "count": 1,
  "query": "search term",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Data Sources

### Database Integration
The API endpoints integrate with your existing PostgreSQL database:
- **Primary Table:** `token_deployments` - Contains token deployment information
- **Supplementary Table:** `user_summary` - Contains creator and price information

### Blockchain Integration
- **Network:** Avalanche C-Chain
- **RPC Endpoint:** Configurable via `NEXT_PUBLIC_RPC_URL`
- **Contracts:** 
  - Token Factory: `0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e`
  - Arena Factory: `0xF16784dcAf838a3e16bEF7711a62D12413c39BD1`

### Fallback Data
Each endpoint includes fallback data to ensure the frontend always has content to display, even when:
- Database is unavailable
- RPC endpoints are down
- No real data exists

## Environment Configuration

Create a `.env.local` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/arena_db

# RPC Configuration
NEXT_PUBLIC_RPC_URL=https://api.avax.network/ext/bc/C/rpc

# Node Environment
NODE_ENV=development
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description",
  "data": [],
  "count": 0
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `500` - Internal Server Error

## Performance Considerations

1. **Database Queries:** Optimized with proper indexing on `token_address`, `deployed_at`, and `lp_deployed`
2. **Blockchain Calls:** Uses `multicall` for efficient batch requests
3. **Caching:** Consider implementing Redis caching for frequently accessed data
4. **Rate Limiting:** Implement rate limiting for production deployment

## Integration with Frontend

The `BlockchainService` class has been updated to use these API endpoints:

```typescript
// Example usage
const blockchainService = new BlockchainService()
const newPairs = await blockchainService.getNewPairs(20)
const closeTo Migration = await blockchainService.getCloseToMigration(10)
const migrated = await blockchainService.getMigratedTokens(15)
```

## Next Steps

1. **Install Dependencies:** Run `npm install` to install the `pg` and `@types/pg` packages
2. **Database Setup:** Ensure your PostgreSQL database is running and accessible
3. **Environment Variables:** Configure your `.env.local` file with the correct database and RPC URLs
4. **Testing:** Test each endpoint with sample data
5. **Optimization:** Add database indexes and consider caching strategies for production

## Support

For issues or questions about the API:
1. Check the console logs for detailed error messages
2. Verify database connectivity
3. Ensure RPC endpoint is accessible
4. Review the fallback data if real data is unavailable 