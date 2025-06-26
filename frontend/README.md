# Arena Terminal Frontend

A Next.js dashboard for Arena ecosystem analytics with wallet intelligence features.

## Features

### 🏠 Dashboard
- Real-time token analytics
- Trading activity monitoring
- Market overview and metrics

### 🔍 Explore
- Token discovery and search
- Detailed token analytics
- Migration tracking

### 🧠 Intel (NEW)
- **Wallet Analysis**: Deep dive into wallet trading patterns
- **P&L Tracking**: Comprehensive profit/loss analysis
- **Top Performers**: Leaderboard of most successful traders
- **Wallet Labels**: Meaningful identification of known wallets
- **Trading Activity**: Pattern analysis and behavioral insights

## Intel Features in Detail

### Wallet Intelligence
The Intel page provides Arkham Intelligence-style analysis for Arena ecosystem wallets:

- **Search by Address or Label**: Find wallets using their address or meaningful labels
- **Comprehensive Analytics**: Total P&L, win rate, trading volume, and activity patterns
- **Recent Trades**: View latest trading activity with profit/loss calculations
- **Top Performers**: See the most successful traders in the ecosystem
- **Wallet Labels**: Identify Arena users and known entities

### API Endpoints
- `/api/wallet/analysis/[address]` - Detailed wallet analysis
- `/api/wallet/search` - Search wallets by address or label
- `/api/wallet/top-performers` - Get top performing wallets

## Setup

### Prerequisites
- Node.js 18+
- PostgreSQL database with Arena trading data
- Environment variables configured

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment configuration:
```bash
cp env.example .env.local
```

3. Configure your environment variables in `.env.local`:
```env
# Database Configuration for Wallet Analysis
DB_HOST=localhost
DB_PORT=5432
DB_NAME=graph_query
DB_USER=postgres
DB_PASSWORD=your_password_here

# Next.js Configuration
NEXT_PUBLIC_APP_NAME=Arena Terminal
NEXT_PUBLIC_APP_VERSION=1.0.0
```

4. Start development server:
```bash
npm run dev
```

### Database Requirements

The Intel features require these PostgreSQL tables:

#### **Core Tables:**
- `bonding_events` - Trading activity data (BUY/SELL events)
- `token_deployments` - Token information and metadata
- `wallet_labels` - Wallet identification and user labels
- `user_activity` - Pre-calculated user performance metrics

#### **Table Schema Reference:**

**bonding_events:**
- `user_address` (VARCHAR) - Wallet address
- `token_address` (VARCHAR) - Token contract address
- `trade_type` (VARCHAR) - 'BUY' or 'SELL'
- `avax_amount` (NUMERIC) - AVAX amount traded
- `token_amount` (NUMERIC) - Token amount traded
- `price_avax` (NUMERIC) - Price per token in AVAX
- `timestamp` (BIGINT) - Unix timestamp
- `transaction_hash` (VARCHAR) - Transaction hash
- `protocol_fee`, `creator_fee`, `referral_fee` (NUMERIC) - Fee breakdown

**token_deployments:**
- `id` (VARCHAR) - Token contract address (Primary Key)
- `name` (VARCHAR) - Token name
- `symbol` (VARCHAR) - Token symbol
- `creator` (VARCHAR) - Creator wallet address
- `total_supply` (NUMERIC) - Total token supply

**wallet_labels:**
- `wallet_address` (VARCHAR) - Wallet address (Primary Key)
- `label` (VARCHAR) - Human-readable label
- `user_type` (VARCHAR) - User category
- `is_verified` (BOOLEAN) - Verification status
- `risk_level` (VARCHAR) - Risk assessment
- `tags` (TEXT[]) - Array of tags

**user_activity:**
- `user_address` (VARCHAR) - Wallet address
- `total_trades` (INTEGER) - Total number of trades
- `total_pnl_avax` (NUMERIC) - Total profit/loss
- `portfolio_roi` (NUMERIC) - Return on investment percentage
- `win_rate` (NUMERIC) - Percentage of profitable trades

Ensure your database contains the Arena trading data from the subgraph sync.

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DB_HOST` | PostgreSQL host | Yes | localhost |
| `DB_PORT` | PostgreSQL port | Yes | 5432 |
| `DB_NAME` | Database name | Yes | graph_query |
| `DB_USER` | Database username | Yes | postgres |
| `DB_PASSWORD` | Database password | Yes | (empty) |

## Usage

### Analyzing a Wallet
1. Go to `/intel`
2. Enter a wallet address (0x...) in the search bar
3. Click "Analyze" or select from suggestions
4. View comprehensive wallet analysis

### Viewing Top Performers
1. Visit the Intel page to see top performers automatically
2. Click on any performer to view detailed analysis
3. Use the search to find specific wallets

### Search Features
- **Autocomplete**: Type to see wallet suggestions
- **Label Search**: Search by wallet labels (e.g., "Arena User #123")
- **Address Search**: Direct wallet address lookup

## Development

### Project Structure
```
frontend/
├── app/
│   ├── intel/                 # Intel feature pages
│   │   ├── page.tsx          # Main intel page
│   │   └── wallet/[address]/  # Wallet detail page
│   ├── api/
│   │   └── wallet/           # Wallet analysis APIs
│   └── components/           # Shared components
├── lib/
│   └── database.ts           # Centralized database configuration
└── public/                   # Static assets
```

### Database Connection

The app uses a centralized database connection pool in `lib/database.ts` with the following features:
- Connection pooling for performance
- Automatic connection management
- Error handling and logging
- Environment variable configuration

### Adding New Features
1. Create API endpoints in `app/api/wallet/`
2. Add components in `app/components/`
3. Implement pages in `app/intel/`
4. Update navigation in `components/Navigation.tsx`

## Technology Stack

- **Frontend**: Next.js 14, React, TypeScript
- **Styling**: Tailwind CSS
- **Database**: PostgreSQL with `pg` client and connection pooling
- **Icons**: Lucide React
- **Charts**: Recharts

## Troubleshooting

### Database Connection Issues
1. Verify your `.env.local` file has correct database credentials
2. Ensure PostgreSQL is running and accessible
3. Check that the database contains the required tables
4. Test connection using the database scripts in the `scripts/` directory

### Common Table Name Errors
If you encounter "relation does not exist" errors, verify these table names:
- ✅ `bonding_events` (not `bonding_event`)
- ✅ `token_deployments` (not `token_deployment`) 
- ✅ `wallet_labels` (not `wallet_label`)
- ✅ `user_activity` (not `user_activities`)

### Development Issues
1. Make sure all dependencies are installed: `npm install`
2. Verify Node.js version is 18+
3. Check for TypeScript errors: `npm run build`

## Contributing

1. Follow the existing code patterns
2. Add proper TypeScript types
3. Include error handling in API routes
4. Test wallet analysis features with real data
5. Update documentation as needed 