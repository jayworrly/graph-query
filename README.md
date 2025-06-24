# Arena Terminal

A comprehensive blockchain analytics dashboard for the Arena protocol on Avalanche, featuring real-time token tracking, portfolio analysis, and trading insights.

## 🚀 Features

### 📊 **Dashboard Analytics**
- **Real-time token tracking** with live bonding progress
- **Market cap and volume analysis** 
- **Price charts and trading activity**
- **Migration status monitoring**

### 🔍 **Token Categories**
- **New Pairs** - Recently launched tokens
- **Close to Migration** - Tokens approaching bonding completion
- **Migrated Tokens** - Successfully migrated to DEX trading

### 💼 **Portfolio Tracking**
- **User activity analysis**
- **Trading history and performance**
- **P&L calculations**
- **Portfolio value tracking**

### 🗄️ **Database Integration**
- **PostgreSQL backend** with comprehensive schema
- **Subgraph data synchronization**
- **Historical data preservation**

## 🏗️ Architecture

```
Arena Terminal/
├── frontend/              # Next.js dashboard application
│   ├── app/
│   │   ├── api/          # API routes for data fetching
│   │   └── components/   # React components
│   └── lib/              # Utility libraries
├── arena-tracker/        # GraphQL subgraph for Avalanche
│   ├── src/             # Subgraph mappings
│   ├── schema.graphql   # GraphQL schema
│   └── subgraph.yaml    # Subgraph configuration
├── setup_graph_database.py  # Database setup script
├── sync_subgraph_to_db.py   # Data synchronization
└── migrate_addresses.py     # Database migration tools
```

## 🛠️ Installation

### Prerequisites
- **Node.js** (v18+)
- **Python** (v3.8+)
- **PostgreSQL** database
- **Git**

### 1. Clone Repository
```bash
git clone <repository-url>
cd arena-terminal
```

### 2. Frontend Setup
```bash
cd frontend
npm install
```

### 3. Subgraph Setup
```bash
cd arena-tracker
npm install
```

### 4. Database Setup
```bash
# Create .env file with database credentials
cp frontend/env.example .env

# Setup database tables
python setup_graph_database.py

# Sync data from subgraph
python sync_subgraph_to_db.py
```

## 🚀 Usage

### Start Development Server
```bash
cd frontend
npm run dev
```

The dashboard will be available at `http://localhost:3000` (or `http://localhost:3001` if 3000 is occupied).

### Sync Latest Data
```bash
# Sync recent data
python sync_subgraph_to_db.py

# Sync historical data (beyond 5000 records)
python sync_subgraph_to_db.py historical
```

### Database Migration
```bash
# Migrate address fields from BYTEA to VARCHAR
python migrate_addresses.py

# Check current schema
python check_schema.py
```

## 📊 API Endpoints

### Token Data
- `GET /api/tokens/new-pairs` - Recently launched tokens
- `GET /api/tokens/close-to-migration` - Tokens near migration
- `GET /api/tokens/migrated` - Successfully migrated tokens
- `GET /api/tokens/trading-activity` - Trading volume and activity

### Analytics
- `GET /api/tokens/analytics` - Token performance metrics
- `GET /api/tokens/protocol-comparison` - Cross-protocol analysis
- `GET /api/tokens/overview` - Dashboard overview data

## 🗄️ Database Schema

### Core Tables
- **`token_deployments`** - Token information and bonding progress
- **`bonding_events`** - All buy/sell transactions
- **`user_activity`** - User trading statistics and portfolio data

### Key Features
- **Real addresses** stored as `VARCHAR(66)` (not binary)
- **Comprehensive indexing** for fast queries
- **Foreign key relationships** for data integrity
- **Automatic timestamps** for tracking updates

## 🔧 Configuration

### Environment Variables
```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=your_database

# Subgraph URL
SUBGRAPH_URL=https://api.studio.thegraph.com/query/18408/arena-tracker/v0.0.5
```

### Subgraph Configuration
The subgraph tracks Arena protocol contracts:
- **Token Factory**: `0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e`
- **Migration Contract**: `0xF16784dcAf838a3e16bEF7711a62D12413c39BD1`

## 🚀 Deployment

### Frontend (Vercel/Netlify)
```bash
cd frontend
npm run build
npm start
```

### Database (Production)
1. Setup PostgreSQL instance
2. Run `python setup_graph_database.py`
3. Configure environment variables
4. Run initial sync: `python sync_subgraph_to_db.py`

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Arena Protocol**: [Official Website]
- **Subgraph**: [The Graph Studio]
- **Dashboard**: [Live Demo]

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Join our Discord community
- Follow us on Twitter

---

**Built with ❤️ for the Arena community** 