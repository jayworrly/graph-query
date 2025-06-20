export const config = {
  rpcUrl: process.env.NEXT_PUBLIC_RPC_URL || 'https://api.avax.network/ext/bc/C/rpc',
  chainId: parseInt(process.env.NEXT_PUBLIC_CHAIN_ID || '43114'),
  networkName: process.env.NEXT_PUBLIC_NETWORK_NAME || 'Avalanche',
  
  // DEX Router addresses for Avalanche
  dexRouters: {
    traderjoe: '0x60aE616a2155Ee3d9A68541Ba4544862310933d4',
    pangolin: '0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106',
    sushiswap: '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'
  },
  
  // Factory addresses for pair discovery
  dexFactories: {
    traderjoe: '0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10',
    pangolin: '0xefa94DE7a4656D787667C749f7E1223D71E9FD88',
    sushiswap: '0xc35DADB65012eC5796536bD9864eD8773aBc74C4'
  },

  avalancheRpcUrl: process.env.AVALANCHE_RPC_URL || 'https://api.avax.network/ext/bc/C/rpc',
  arenaTokenFactoryAddress: process.env.ARENA_TOKEN_FACTORY_ADDRESS || '0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e',
  arenaPairFactoryAddress: process.env.ARENA_PAIR_FACTORY_ADDRESS || '0xF16784dcAf838a3e16bEF7711a62D12413c39BD1',
  dexScreenerApiUrl: 'https://api.dexscreener.com/latest/dex',
  
  // Database configuration
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'arena',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'password',
  },
  
  // Arena Subgraph endpoint
  arenaSubgraphUrl: process.env.ARENA_SUBGRAPH_URL || 'https://api.studio.thegraph.com/query/18408/arena-tracker/v0.0.5'
} 