# Analysis Scripts

This directory contains organized scripts for wallet and profit analysis.

## Structure

### `/analysis/`
- `enhanced_profit_analysis.py` - Main profit analysis with wallet labels
- `quick_profit_analysis.py` - Fast aggregate P&L analysis
- `manual_pnl_calculator.py` - FIFO-based manual P&L calculation
- `wallet_profit_analysis.py` - Uses pre-calculated user_activity table
- `lookup_specific_wallet.py` - Detailed individual wallet lookup
- `profit_loss_analysis.sql` - SQL queries for P&L analysis

### `/import/`
- `fix_arena_import.py` - Import Arena users with wallet labeling
- `wallet_import_setup.py` - Setup wallet_labels table structure
- `import_avalanche_wallets.py` - Generic wallet import tool

### `/utils/`
- `check_data.py` - Database data validation
- `check_schema.py` - Database schema validation
- `migrate_addresses.py` - Address migration utilities

## Usage

Run analysis scripts from the project root:
```bash
python scripts/analysis/enhanced_profit_analysis.py
python scripts/analysis/lookup_specific_wallet.py
```

## Database Setup

1. Ensure PostgreSQL is running
2. Run `setup_graph_database.py` to create tables
3. Run `sync_subgraph_to_db.py` to import data
4. Run `scripts/import/wallet_import_setup.py` to setup wallet labels
5. Run `scripts/import/fix_arena_import.py` to import Arena users
