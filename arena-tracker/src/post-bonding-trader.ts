import { Swapped, Bought, Sold } from "../generated/PostBondingTrader/ParaswapAggregator"
import { 
  ParaswapTrade, 
  UserActivity, 
  TokenDeployment,
  ArenaTokenParaswapStats,
  RealTimeTradeAlert
} from "../generated/schema"
import { BigDecimal, Bytes, log, Address, ethereum, BigInt } from "@graphprotocol/graph-ts"

// WAVAX address on Avalanche
const WAVAX_ADDRESS = Address.fromString("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7")

// Arena Token Factory address for validation
const ARENA_TOKEN_FACTORY = Address.fromString("0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e")

// Known major tokens that we want to track (but not as Arena tokens)
const MAJOR_TOKENS = new Map<string, string>()
MAJOR_TOKENS.set("0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7", "WAVAX")
MAJOR_TOKENS.set("0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7", "USDt")
MAJOR_TOKENS.set("0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664", "USDC.e")
MAJOR_TOKENS.set("0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e", "USDC")

export function handleParaswapSwapped(event: Swapped): void {
  createParaswapTrade(event, "SWAPPED")
}

export function handleParaswapBought(event: Bought): void {
  createParaswapTrade(event, "BOUGHT")
}

export function handleParaswapSold(event: Sold): void {
  createParaswapTrade(event, "SOLD")
}

function createParaswapTrade(event: ethereum.Event, tradeType: string): void {
  let startTime = event.block.timestamp
  
  // Create unique ID for this trade
  let tradeId = event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  
  // Cast the event to get the parameters
  let swappedEvent = changetype<Swapped>(event)
  
  // Token analysis using on-chain data
  let srcTokenAddress = swappedEvent.params.srcToken.toHexString().toLowerCase()
  let destTokenAddress = swappedEvent.params.destToken.toHexString().toLowerCase()
  
  let srcIsArena = isArenaTokenOnChain(swappedEvent.params.srcToken)
  let destIsArena = isArenaTokenOnChain(swappedEvent.params.destToken)
  let srcIsAVAX = isAVAXToken(swappedEvent.params.srcToken)
  let destIsAVAX = isAVAXToken(swappedEvent.params.destToken)
  let srcIsMajor = isMajorToken(swappedEvent.params.srcToken)
  let destIsMajor = isMajorToken(swappedEvent.params.destToken)
  
  // Process trades that involve either Arena tokens OR major tokens
  // This captures: Arena<->AVAX, Arena<->USDC, Arena<->Arena, AVAX<->USDC, etc.
  if (!srcIsArena && !destIsArena && !srcIsMajor && !destIsMajor) {
    log.debug("Skipping trade between unknown tokens: {} -> {}", [srcTokenAddress, destTokenAddress])
    return
  }
  
  // Create ParaswapTrade entity
  let trade = new ParaswapTrade(tradeId)
  
  trade.uuid = swappedEvent.params.uuid
  
  // Trade participants
  trade.initiator = swappedEvent.params.initiator
  trade.beneficiary = swappedEvent.params.beneficiary
  trade.partner = swappedEvent.params.partner
  
  // Token information
  trade.srcToken = swappedEvent.params.srcToken
  trade.destToken = swappedEvent.params.destToken
  trade.srcAmount = swappedEvent.params.srcAmount.toBigDecimal()
  trade.receivedAmount = swappedEvent.params.receivedAmount.toBigDecimal()
  trade.expectedAmount = swappedEvent.params.expectedAmount.toBigDecimal()
  
  // Enhanced token categorization
  trade.srcTokenIsArena = srcIsArena
  trade.destTokenIsArena = destIsArena
  
  // Link to Arena token entity if available (only if subgraph has indexed it)
  let arenaTokenAddress: string | null = null
  if (srcIsArena) {
    arenaTokenAddress = srcTokenAddress
  } else if (destIsArena) {
    arenaTokenAddress = destTokenAddress
  }
  
  if (arenaTokenAddress) {
    // Try to load from subgraph's indexed data (not external database)
    let tokenDeployment = TokenDeployment.load(arenaTokenAddress)
    if (tokenDeployment) {
      trade.arenaToken = arenaTokenAddress
    } else {
      // Token not yet indexed by subgraph, but still likely Arena token
      log.info("Arena token detected but not yet indexed: {}", [arenaTokenAddress])
    }
  }
  
  // Trade analysis and categorization
  trade.tradeType = tradeType
  
  // Determine if this is a buy/sell for Arena tokens specifically
  if ((srcIsAVAX || srcIsMajor) && destIsArena) {
    trade.isBuy = true  // Buying Arena token with AVAX/major token
  } else if (srcIsArena && (destIsAVAX || destIsMajor)) {
    trade.isBuy = false // Selling Arena token for AVAX/major token
  } else if (srcIsArena && destIsArena) {
    trade.isBuy = true  // Arena to Arena swap (count as buy)
  } else {
    // Major token to major token (AVAX -> USDC, etc.)
    trade.isBuy = false // Not really a buy/sell of Arena tokens
  }
  
  // Calculate AVAX values
  trade.avaxValueIn = calculateAVAXValue(swappedEvent.params.srcToken, trade.srcAmount, srcIsAVAX)
  trade.avaxValueOut = calculateAVAXValue(swappedEvent.params.destToken, trade.receivedAmount, destIsAVAX)
  
  // Estimate USD value (using AVAX as proxy)
  trade.estimatedUsdValue = trade.avaxValueIn.plus(trade.avaxValueOut).div(BigDecimal.fromString("2"))
  
  // Price and slippage calculations
  if (trade.srcAmount.gt(BigDecimal.fromString("0"))) {
    trade.priceRatio = trade.receivedAmount.div(trade.srcAmount)
  } else {
    trade.priceRatio = BigDecimal.fromString("0")
  }
  
  if (trade.expectedAmount.gt(BigDecimal.fromString("0"))) {
    let slippageDiff = trade.expectedAmount.minus(trade.receivedAmount)
    trade.slippagePercent = slippageDiff.div(trade.expectedAmount).times(BigDecimal.fromString("100"))
  } else {
    trade.slippagePercent = BigDecimal.fromString("0")
  }
  
  // Fee information
  trade.feePercent = swappedEvent.params.feePercent.toBigDecimal().div(BigDecimal.fromString("10000"))
  trade.feeAmount = trade.srcAmount.times(trade.feePercent).div(BigDecimal.fromString("100"))
  
  // Context information
  trade.timestamp = event.block.timestamp
  trade.blockNumber = event.block.number
  trade.transactionHash = event.transaction.hash
  trade.gasPrice = event.transaction.gasPrice
  trade.gasUsed = event.receipt ? event.receipt!.gasUsed : event.transaction.gasLimit
  
  // Performance tracking
  trade.processingLatency = event.block.timestamp.minus(startTime)
  
  trade.save()
  
  // Update Arena token Paraswap stats (only for Arena tokens)
  if (arenaTokenAddress) {
    updateArenaTokenParaswapStats(arenaTokenAddress, trade)
  }
  
  // Create real-time alerts for significant trades
  createTradeAlert(trade)
  
  // Update user activity
  updateUserActivityForParaswapTrade(swappedEvent.params.initiator, trade)
  if (!swappedEvent.params.initiator.equals(swappedEvent.params.beneficiary)) {
    updateUserActivityForParaswapTrade(swappedEvent.params.beneficiary, trade)
  }
  
  // Enhanced logging with token categories
  let srcTokenType = srcIsArena ? "Arena" : (srcIsMajor ? (MAJOR_TOKENS.get(srcTokenAddress) || "Major") : "Unknown")
  let destTokenType = destIsArena ? "Arena" : (destIsMajor ? (MAJOR_TOKENS.get(destTokenAddress) || "Major") : "Unknown")
  
  log.info("Paraswap {} trade: {} ({}) -> {} ({}), {} AVAX value, {}% slippage", [
    tradeType,
    srcTokenAddress.slice(0, 10),
    srcTokenType,
    destTokenAddress.slice(0, 10), 
    destTokenType,
    trade.estimatedUsdValue.toString(),
    trade.slippagePercent.toString()
  ])
}

function isArenaTokenOnChain(tokenAddress: Bytes): boolean {
  let addr = tokenAddress.toHexString().toLowerCase()
  
  // Not an Arena token if it's a major token
  if (MAJOR_TOKENS.has(addr)) {
    return false
  }
  
  // Skip null address
  if (addr == "0x0000000000000000000000000000000000000000") {
    return false
  }
  
  // Check if this token exists in our subgraph's indexed TokenDeployment entities
  // (This only works for tokens the subgraph has already seen via TokenCreated events)
  let tokenDeployment = TokenDeployment.load(addr)
  if (tokenDeployment != null) {
    log.info("Confirmed Arena token from subgraph index: {}", [addr])
    return true
  }
  
  // Heuristic approach for tokens not yet indexed:
  // If it's not a major token and has a valid address, assume it could be Arena token
  // This is permissive but helps catch new Arena tokens before they're indexed
  if (addr.length == 42) {
    log.info("Potential Arena token (not yet indexed): {}", [addr])
    return true  // Be permissive for now
  }
  
  return false
}

function isMajorToken(tokenAddress: Bytes): boolean {
  let addr = tokenAddress.toHexString().toLowerCase()
  return MAJOR_TOKENS.has(addr)
}

function isAVAXToken(tokenAddress: Bytes): boolean {
  let addr = tokenAddress.toHexString().toLowerCase()
  return addr == "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7" || // WAVAX
         addr == "0x0000000000000000000000000000000000000000"    // ETH (represents AVAX)
}

function calculateAVAXValue(tokenAddress: Bytes, amount: BigDecimal, isAVAX: boolean): BigDecimal {
  if (isAVAX) {
    return amount
  }
  
  // For major stablecoins, you could use approximate USD to AVAX conversion
  let addr = tokenAddress.toHexString().toLowerCase()
  if (addr == "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7" || // USDt
      addr == "0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664" || // USDC.e  
      addr == "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e") { // USDC
    // Rough approximation: 1 USD ≈ 0.025 AVAX (when AVAX = $40)
    // You could make this more sophisticated with price oracles
    return amount.times(BigDecimal.fromString("0.025"))
  }
  
  // For non-AVAX tokens, you could:
  // 1. Look up price from DEX pairs indexed by subgraph
  // 2. Use price oracle data if available
  // 3. For now, return 0 and calculate elsewhere
  return BigDecimal.fromString("0")
}

function updateArenaTokenParaswapStats(tokenAddress: string, trade: ParaswapTrade): void {
  let stats = ArenaTokenParaswapStats.load(tokenAddress)
  
  if (stats == null) {
    stats = new ArenaTokenParaswapStats(tokenAddress)
    stats.token = tokenAddress
    stats.totalParaswapTrades = 0
    stats.totalParaswapVolumeAvax = BigDecimal.fromString("0")
    stats.totalBuyVolumeAvax = BigDecimal.fromString("0")
    stats.totalSellVolumeAvax = BigDecimal.fromString("0")
    stats.trades24h = 0
    stats.volume24hAvax = BigDecimal.fromString("0")
    stats.lastParaswapPrice = BigDecimal.fromString("0")
    stats.priceHigh24h = BigDecimal.fromString("0")
    stats.priceLow24h = BigDecimal.fromString("999999999")
    stats.averageSlippage = BigDecimal.fromString("0")
    stats.largestTrade = BigDecimal.fromString("0")
    stats.firstParaswapTrade = trade.timestamp
    stats.lastParaswapTrade = trade.timestamp
    stats.lastUpdateTimestamp = trade.timestamp
  }
  
  // Update counters
  stats.totalParaswapTrades = stats.totalParaswapTrades + 1
  stats.lastParaswapTrade = trade.timestamp
  stats.lastUpdateTimestamp = trade.timestamp
  
  // Update volume
  let tradeVolume = trade.avaxValueIn.plus(trade.avaxValueOut).div(BigDecimal.fromString("2"))
  stats.totalParaswapVolumeAvax = stats.totalParaswapVolumeAvax.plus(tradeVolume)
  
  if (trade.isBuy) {
    stats.totalBuyVolumeAvax = stats.totalBuyVolumeAvax.plus(tradeVolume)
  } else {
    stats.totalSellVolumeAvax = stats.totalSellVolumeAvax.plus(tradeVolume)
  }
  
  // Update 24h data (simplified - you might want more sophisticated time window logic)
  let twentyFourHours = BigInt.fromI32(86400)
  let timeDiff = trade.timestamp.minus(stats.lastUpdateTimestamp)
  if (timeDiff.lt(twentyFourHours)) {
    stats.trades24h = stats.trades24h + 1
    stats.volume24hAvax = stats.volume24hAvax.plus(tradeVolume)
  }
  
  // Update price tracking
  if (trade.priceRatio.gt(BigDecimal.fromString("0"))) {
    stats.lastParaswapPrice = trade.priceRatio
    
    if (trade.priceRatio.gt(stats.priceHigh24h)) {
      stats.priceHigh24h = trade.priceRatio
    }
    
    if (trade.priceRatio.lt(stats.priceLow24h)) {
      stats.priceLow24h = trade.priceRatio
    }
  }
  
  // Update slippage tracking
  if (stats.totalParaswapTrades == 1) {
    stats.averageSlippage = trade.slippagePercent
  } else {
    let oldAvg = stats.averageSlippage.times(BigDecimal.fromString((stats.totalParaswapTrades - 1).toString()))
    stats.averageSlippage = oldAvg.plus(trade.slippagePercent).div(BigDecimal.fromString(stats.totalParaswapTrades.toString()))
  }
  
  // Track largest trade
  if (tradeVolume.gt(stats.largestTrade)) {
    stats.largestTrade = tradeVolume
  }
  
  stats.save()
}

function createTradeAlert(trade: ParaswapTrade): void {
  let alertId = trade.transactionHash.toHexString() + "-" + trade.timestamp.toString()
  
  // Determine trade significance
  let tradeValue = trade.avaxValueIn.plus(trade.avaxValueOut).div(BigDecimal.fromString("2"))
  let significance = "SMALL"
  
  if (tradeValue.gt(BigDecimal.fromString("100"))) {
    significance = "WHALE"
  } else if (tradeValue.gt(BigDecimal.fromString("10"))) {
    significance = "LARGE"
  } else if (tradeValue.gt(BigDecimal.fromString("1"))) {
    significance = "MEDIUM"
  }
  
  // Only create alerts for significant trades or high slippage
  if (significance == "LARGE" || significance == "WHALE" || 
      trade.slippagePercent.gt(BigDecimal.fromString("5"))) {
    
    let alert = new RealTimeTradeAlert(alertId)
    alert.paraswapTrade = trade.id
    alert.alertType = tradeValue.gt(BigDecimal.fromString("50")) ? "WHALE_ACTIVITY" : "LARGE_BUY"
    alert.significance = significance
    alert.tradeValueAvax = tradeValue
    alert.priceImpact = trade.slippagePercent
    alert.volumeRatio = BigDecimal.fromString("0") // Calculate against 24h volume if needed
    alert.timestamp = trade.timestamp
    alert.blockNumber = trade.blockNumber
    
    alert.save()
    
    log.warning("🚨 Trade Alert: {} AVAX {} with {}% slippage", [
      tradeValue.toString(),
      significance,
      trade.slippagePercent.toString()
    ])
  }
}

function updateUserActivityForParaswapTrade(userAddress: Bytes, trade: ParaswapTrade): void {
  let userId = userAddress.toHexString()
  let user = UserActivity.load(userId)
  
  if (user == null) {
    user = new UserActivity(userId)
    user.userAddress = userAddress
    user.totalTrades = 0
    user.totalVolumeAvax = BigDecimal.fromString("0")
    user.totalTokensBought = BigDecimal.fromString("0")
    user.totalTokensSold = BigDecimal.fromString("0")
    user.totalFeesSpent = BigDecimal.fromString("0")
    user.uniqueTokensTraded = 0
    user.firstTradeTimestamp = trade.timestamp
    user.lastTradeTimestamp = trade.timestamp
    
    // Initialize portfolio tracking
    user.currentPortfolioValueAvax = BigDecimal.fromString("0")
    user.totalInvestmentAvax = BigDecimal.fromString("0")
    user.realizedPnLAvax = BigDecimal.fromString("0")
    user.unrealizedPnLAvax = BigDecimal.fromString("0")
    user.totalPnLAvax = BigDecimal.fromString("0")
    
    // Initialize performance metrics
    user.winRate = BigDecimal.fromString("0")
    user.profitableTrades = 0
    user.losingTrades = 0
    user.averageProfitPerTrade = BigDecimal.fromString("0")
    user.averageLossPerTrade = BigDecimal.fromString("0")
    user.largestWinAvax = BigDecimal.fromString("0")
    user.largestLossAvax = BigDecimal.fromString("0")
    
    // Initialize risk metrics
    user.sharpeRatio = BigDecimal.fromString("0")
    user.maxDrawdownAvax = BigDecimal.fromString("0")
    user.portfolioRoi = BigDecimal.fromString("0")
  }
  
  // Update basic stats
  user.totalTrades = user.totalTrades + 1
  user.lastTradeTimestamp = trade.timestamp
  
  // Update fees
  user.totalFeesSpent = user.totalFeesSpent.plus(trade.feeAmount)
  
  // Update volume with AVAX equivalent
  let tradeVolume = trade.avaxValueIn.plus(trade.avaxValueOut).div(BigDecimal.fromString("2"))
  user.totalVolumeAvax = user.totalVolumeAvax.plus(tradeVolume)
  
  // Update token amounts
  if (trade.isBuy) {
    user.totalTokensBought = user.totalTokensBought.plus(trade.receivedAmount)
  } else {
    user.totalTokensSold = user.totalTokensSold.plus(trade.srcAmount)
  }
  
  user.save()
} 