import { TokenCreated, Buy, Sell, TokenLPCreated } from "../generated/ArenaTokenFactory/ArenaTokenFactory"
import { TokenDeployment, BondingEvent, DailyStats, UserActivity, GlobalStats, PriceSnapshot } from "../generated/schema"
import { BigInt, BigDecimal, Address, Bytes } from "@graphprotocol/graph-ts"
import { ERC20 } from "../generated/ArenaTokenFactory/ERC20"

export function handleTokenCreated(event: TokenCreated): void {
  let tokenId = event.params.tokenId
  let params = event.params.params
  let tokenSupply = event.params.tokenSupply
  
  let tokenAddress = params.tokenContractAddress
  let tokenDeployment = new TokenDeployment(tokenAddress.toHexString())
  
  // Basic deployment info
  tokenDeployment.tokenAddress = tokenAddress
  tokenDeployment.creator = params.creatorAddress
  tokenDeployment.tokenId = tokenId
  tokenDeployment.deployedAt = event.block.timestamp
  
  // Fetch token metadata from contract
  let tokenContract = ERC20.bind(tokenAddress)
  
  // Try to get name, symbol, decimals from contract
  let nameResult = tokenContract.try_name()
  let symbolResult = tokenContract.try_symbol()
  let decimalsResult = tokenContract.try_decimals()
  let totalSupplyResult = tokenContract.try_totalSupply()
  
  tokenDeployment.name = nameResult.reverted ? `Token ${tokenAddress.toHexString().slice(-6)}` : nameResult.value
  tokenDeployment.symbol = symbolResult.reverted ? tokenAddress.toHexString().slice(-6).toUpperCase() : symbolResult.value
  tokenDeployment.decimals = decimalsResult.reverted ? 18 : decimalsResult.value
  tokenDeployment.totalSupply = totalSupplyResult.reverted ? tokenSupply : totalSupplyResult.value
  
  // Bonding curve data
  tokenDeployment.bondingProgress = BigDecimal.fromString("0")
  tokenDeployment.migrationStatus = params.lpDeployed ? "MIGRATED" : "BONDING"
  tokenDeployment.currentPriceAvax = BigDecimal.fromString("0.000001") // Starting price
  tokenDeployment.avaxRaised = BigDecimal.fromString("0")
  tokenDeployment.migrationThreshold = BigDecimal.fromString("503.15")
  tokenDeployment.pairAddress = params.pairAddress
  
  // Trading statistics
  tokenDeployment.totalAvaxVolume = BigDecimal.fromString("0")
  tokenDeployment.totalBuyVolume = BigDecimal.fromString("0")
  tokenDeployment.totalSellVolume = BigDecimal.fromString("0")
  tokenDeployment.totalTrades = 0
  tokenDeployment.totalBuys = 0
  tokenDeployment.totalSells = 0
  tokenDeployment.uniqueTraders = 0
  
  // Market data
  tokenDeployment.marketCapAvax = BigDecimal.fromString("0")
  tokenDeployment.liquidityAvax = BigDecimal.fromString("0")
  tokenDeployment.holders = 1 // Creator is first holder
  
  // Price history
  tokenDeployment.priceHigh24h = BigDecimal.fromString("0.000001")
  tokenDeployment.priceLow24h = BigDecimal.fromString("0.000001")
  tokenDeployment.volume24h = BigDecimal.fromString("0")
  tokenDeployment.priceChange24h = BigDecimal.fromString("0")
  
  // Timestamps
  tokenDeployment.lastTradeTimestamp = event.block.timestamp
  tokenDeployment.lastUpdateTimestamp = event.block.timestamp
  
  tokenDeployment.save()
  
  // Also save by tokenId for easy lookup in Buy/Sell events
  let tokenIdLookup = new TokenDeployment("token-" + tokenId.toString())
  tokenIdLookup.tokenAddress = tokenAddress
  tokenIdLookup.creator = params.creatorAddress
  tokenIdLookup.tokenId = tokenId
  tokenIdLookup.deployedAt = event.block.timestamp
  tokenIdLookup.name = tokenDeployment.name
  tokenIdLookup.symbol = tokenDeployment.symbol
  tokenIdLookup.decimals = tokenDeployment.decimals
  tokenIdLookup.totalSupply = tokenDeployment.totalSupply
  tokenIdLookup.bondingProgress = tokenDeployment.bondingProgress
  tokenIdLookup.migrationStatus = tokenDeployment.migrationStatus
  tokenIdLookup.currentPriceAvax = tokenDeployment.currentPriceAvax
  tokenIdLookup.avaxRaised = tokenDeployment.avaxRaised
  tokenIdLookup.migrationThreshold = tokenDeployment.migrationThreshold
  tokenIdLookup.pairAddress = tokenDeployment.pairAddress
  tokenIdLookup.totalAvaxVolume = tokenDeployment.totalAvaxVolume
  tokenIdLookup.totalBuyVolume = tokenDeployment.totalBuyVolume
  tokenIdLookup.totalSellVolume = tokenDeployment.totalSellVolume
  tokenIdLookup.totalTrades = tokenDeployment.totalTrades
  tokenIdLookup.totalBuys = tokenDeployment.totalBuys
  tokenIdLookup.totalSells = tokenDeployment.totalSells
  tokenIdLookup.uniqueTraders = tokenDeployment.uniqueTraders
  tokenIdLookup.marketCapAvax = tokenDeployment.marketCapAvax
  tokenIdLookup.liquidityAvax = tokenDeployment.liquidityAvax
  tokenIdLookup.holders = tokenDeployment.holders
  tokenIdLookup.priceHigh24h = tokenDeployment.priceHigh24h
  tokenIdLookup.priceLow24h = tokenDeployment.priceLow24h
  tokenIdLookup.volume24h = tokenDeployment.volume24h
  tokenIdLookup.priceChange24h = tokenDeployment.priceChange24h
  tokenIdLookup.lastTradeTimestamp = tokenDeployment.lastTradeTimestamp
  tokenIdLookup.lastUpdateTimestamp = tokenDeployment.lastUpdateTimestamp
  tokenIdLookup.save()
  
  // Update daily and global stats
  updateDailyStats(event.block.timestamp, BigDecimal.fromString("0"), true)
  updateGlobalStats(event.block.timestamp, BigDecimal.fromString("0"), true)
}

export function handleBuy(event: Buy): void {
  // Load token deployment by tokenId
  let tokenDeployment = getTokenDeploymentByTokenId(event.params.tokenId)
  if (tokenDeployment == null) {
    return // Skip if token not found
  }
  
  let bondingEvent = new BondingEvent(
    event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  )
  
  // Convert amounts from Wei to readable units
  let avaxAmount = event.params.cost.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let tokenAmount = event.params.tokenAmount.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let protocolFee = event.params.protocolFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let creatorFee = event.params.creatorFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let referralFee = event.params.referralFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  
  // Calculate new cumulative AVAX raised
  let newAvaxRaised = tokenDeployment.avaxRaised.plus(avaxAmount)
  
  // Calculate bonding progress
  let progressPercent = newAvaxRaised.div(tokenDeployment.migrationThreshold).times(BigDecimal.fromString("100"))
  if (progressPercent.gt(BigDecimal.fromString("100"))) {
    progressPercent = BigDecimal.fromString("100")
  }
  
  // Calculate current price from token supply and AVAX cost
  let currentPrice = avaxAmount.div(tokenAmount)
  
  // Create bonding event
  bondingEvent.token = tokenDeployment.id
  bondingEvent.user = event.params.user
  bondingEvent.avaxAmount = avaxAmount
  bondingEvent.tokenAmount = tokenAmount
  bondingEvent.priceAvax = currentPrice
  bondingEvent.bondingProgress = progressPercent
  bondingEvent.cumulativeAvax = newAvaxRaised
  bondingEvent.tradeType = "BUY"
  bondingEvent.protocolFee = protocolFee
  bondingEvent.creatorFee = creatorFee
  bondingEvent.referralFee = referralFee
  bondingEvent.timestamp = event.block.timestamp
  bondingEvent.blockNumber = event.block.number
  bondingEvent.transactionHash = event.transaction.hash
  bondingEvent.gasPrice = event.transaction.gasPrice
  bondingEvent.gasUsed = BigInt.fromI32(0) // Gas used not available in event context
  
  bondingEvent.save()
  
  // Update token deployment statistics
  tokenDeployment.bondingProgress = progressPercent
  tokenDeployment.totalAvaxVolume = tokenDeployment.totalAvaxVolume.plus(avaxAmount)
  tokenDeployment.totalBuyVolume = tokenDeployment.totalBuyVolume.plus(avaxAmount)
  tokenDeployment.totalTrades = tokenDeployment.totalTrades + 1
  tokenDeployment.totalBuys = tokenDeployment.totalBuys + 1
  tokenDeployment.currentPriceAvax = currentPrice
  tokenDeployment.avaxRaised = newAvaxRaised
  tokenDeployment.lastTradeTimestamp = event.block.timestamp
  tokenDeployment.lastUpdateTimestamp = event.block.timestamp
  
  // Update 24h price tracking
  let dayAgo = event.block.timestamp.minus(BigInt.fromI32(86400))
  if (currentPrice.gt(tokenDeployment.priceHigh24h) || tokenDeployment.lastTradeTimestamp.lt(dayAgo)) {
    tokenDeployment.priceHigh24h = currentPrice
  }
  if (currentPrice.lt(tokenDeployment.priceLow24h) || tokenDeployment.lastTradeTimestamp.lt(dayAgo)) {
    tokenDeployment.priceLow24h = currentPrice
  }
  
  // Calculate market cap
  let circulatingSupply = tokenDeployment.totalSupply.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  tokenDeployment.marketCapAvax = currentPrice.times(circulatingSupply)
  
  // Update migration status
  if (progressPercent.ge(BigDecimal.fromString("80"))) {
    tokenDeployment.migrationStatus = "CLOSE_TO_MIGRATION"
  }
  if (progressPercent.ge(BigDecimal.fromString("100"))) {
    tokenDeployment.migrationStatus = "MIGRATED"
  }
  
  tokenDeployment.save()
  
  // Also update the tokenId lookup copy
  let tokenIdLookup = TokenDeployment.load("token-" + event.params.tokenId.toString())
  if (tokenIdLookup != null) {
    tokenIdLookup.bondingProgress = tokenDeployment.bondingProgress
    tokenIdLookup.totalAvaxVolume = tokenDeployment.totalAvaxVolume
    tokenIdLookup.totalBuyVolume = tokenDeployment.totalBuyVolume
    tokenIdLookup.totalTrades = tokenDeployment.totalTrades
    tokenIdLookup.totalBuys = tokenDeployment.totalBuys
    tokenIdLookup.currentPriceAvax = tokenDeployment.currentPriceAvax
    tokenIdLookup.avaxRaised = tokenDeployment.avaxRaised
    tokenIdLookup.lastTradeTimestamp = tokenDeployment.lastTradeTimestamp
    tokenIdLookup.lastUpdateTimestamp = tokenDeployment.lastUpdateTimestamp
    tokenIdLookup.priceHigh24h = tokenDeployment.priceHigh24h
    tokenIdLookup.priceLow24h = tokenDeployment.priceLow24h
    tokenIdLookup.marketCapAvax = tokenDeployment.marketCapAvax
    tokenIdLookup.migrationStatus = tokenDeployment.migrationStatus
    tokenIdLookup.save()
  }
  
  // Update user activity
  updateUserActivity(event.params.user, avaxAmount, tokenAmount, BigDecimal.fromString("0"), protocolFee.plus(creatorFee).plus(referralFee), event.block.timestamp)
  
  // Create price snapshot (hourly)
  createPriceSnapshot(tokenDeployment, currentPrice, avaxAmount, event.block.timestamp, "HOURLY")
  
  // Update daily and global stats
  updateDailyStats(event.block.timestamp, avaxAmount, false)
  updateGlobalStats(event.block.timestamp, avaxAmount, false)
}

export function handleSell(event: Sell): void {
  // Load token deployment by tokenId
  let tokenDeployment = getTokenDeploymentByTokenId(event.params.tokenId)
  if (tokenDeployment == null) {
    return // Skip if token not found
  }
  
  let bondingEvent = new BondingEvent(
    event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  )
  
  // Convert amounts from Wei to readable units
  let avaxAmount = event.params.reward.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let tokenAmount = event.params.tokenAmount.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let protocolFee = event.params.protocolFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let creatorFee = event.params.creatorFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  let referralFee = event.params.referralFee.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  
  // Calculate current price from token amount and AVAX reward
  let currentPrice = avaxAmount.div(tokenAmount)
  
  // Calculate new cumulative AVAX raised (subtract for sells)
  let newAvaxRaised = tokenDeployment.avaxRaised.minus(avaxAmount)
  if (newAvaxRaised.lt(BigDecimal.fromString("0"))) {
    newAvaxRaised = BigDecimal.fromString("0")
  }
  
  // Calculate bonding progress
  let progressPercent = newAvaxRaised.div(tokenDeployment.migrationThreshold).times(BigDecimal.fromString("100"))
  if (progressPercent.gt(BigDecimal.fromString("100"))) {
    progressPercent = BigDecimal.fromString("100")
  }
  
  // Create bonding event
  bondingEvent.token = tokenDeployment.id
  bondingEvent.user = event.params.user
  bondingEvent.avaxAmount = avaxAmount
  bondingEvent.tokenAmount = tokenAmount
  bondingEvent.priceAvax = currentPrice
  bondingEvent.bondingProgress = progressPercent
  bondingEvent.cumulativeAvax = newAvaxRaised
  bondingEvent.tradeType = "SELL"
  bondingEvent.protocolFee = protocolFee
  bondingEvent.creatorFee = creatorFee
  bondingEvent.referralFee = referralFee
  bondingEvent.timestamp = event.block.timestamp
  bondingEvent.blockNumber = event.block.number
  bondingEvent.transactionHash = event.transaction.hash
  bondingEvent.gasPrice = event.transaction.gasPrice
  bondingEvent.gasUsed = BigInt.fromI32(0)
  
  bondingEvent.save()
  
  // Update token deployment statistics
  tokenDeployment.bondingProgress = progressPercent
  tokenDeployment.totalAvaxVolume = tokenDeployment.totalAvaxVolume.plus(avaxAmount)
  tokenDeployment.totalSellVolume = tokenDeployment.totalSellVolume.plus(avaxAmount)
  tokenDeployment.totalTrades = tokenDeployment.totalTrades + 1
  tokenDeployment.totalSells = tokenDeployment.totalSells + 1
  tokenDeployment.currentPriceAvax = currentPrice
  tokenDeployment.avaxRaised = newAvaxRaised
  tokenDeployment.lastTradeTimestamp = event.block.timestamp
  tokenDeployment.lastUpdateTimestamp = event.block.timestamp
  
  // Update 24h price tracking
  let dayAgo = event.block.timestamp.minus(BigInt.fromI32(86400))
  if (currentPrice.gt(tokenDeployment.priceHigh24h) || tokenDeployment.lastTradeTimestamp.lt(dayAgo)) {
    tokenDeployment.priceHigh24h = currentPrice
  }
  if (currentPrice.lt(tokenDeployment.priceLow24h) || tokenDeployment.lastTradeTimestamp.lt(dayAgo)) {
    tokenDeployment.priceLow24h = currentPrice
  }
  
  // Calculate market cap
  let circulatingSupply = tokenDeployment.totalSupply.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  tokenDeployment.marketCapAvax = currentPrice.times(circulatingSupply)
  
  // Update migration status based on progress
  if (progressPercent.lt(BigDecimal.fromString("80"))) {
    tokenDeployment.migrationStatus = "BONDING"
  } else if (progressPercent.lt(BigDecimal.fromString("100"))) {
    tokenDeployment.migrationStatus = "CLOSE_TO_MIGRATION"
  }
  
  tokenDeployment.save()
  
  // Also update the tokenId lookup copy
  let tokenIdLookupSell = TokenDeployment.load("token-" + event.params.tokenId.toString())
  if (tokenIdLookupSell != null) {
    tokenIdLookupSell.bondingProgress = tokenDeployment.bondingProgress
    tokenIdLookupSell.totalAvaxVolume = tokenDeployment.totalAvaxVolume
    tokenIdLookupSell.totalSellVolume = tokenDeployment.totalSellVolume
    tokenIdLookupSell.totalTrades = tokenDeployment.totalTrades
    tokenIdLookupSell.totalSells = tokenDeployment.totalSells
    tokenIdLookupSell.currentPriceAvax = tokenDeployment.currentPriceAvax
    tokenIdLookupSell.avaxRaised = tokenDeployment.avaxRaised
    tokenIdLookupSell.lastTradeTimestamp = tokenDeployment.lastTradeTimestamp
    tokenIdLookupSell.lastUpdateTimestamp = tokenDeployment.lastUpdateTimestamp
    tokenIdLookupSell.priceHigh24h = tokenDeployment.priceHigh24h
    tokenIdLookupSell.priceLow24h = tokenDeployment.priceLow24h
    tokenIdLookupSell.marketCapAvax = tokenDeployment.marketCapAvax
    tokenIdLookupSell.migrationStatus = tokenDeployment.migrationStatus
    tokenIdLookupSell.save()
  }
  
  // Update user activity
  updateUserActivity(event.params.user, avaxAmount, BigDecimal.fromString("0"), tokenAmount, protocolFee.plus(creatorFee).plus(referralFee), event.block.timestamp)
  
  // Create price snapshot (hourly)
  createPriceSnapshot(tokenDeployment, currentPrice, avaxAmount, event.block.timestamp, "HOURLY")
  
  // Update daily and global stats
  updateDailyStats(event.block.timestamp, avaxAmount, false)
  updateGlobalStats(event.block.timestamp, avaxAmount, false)
}

export function handleTokenLPCreated(event: TokenLPCreated): void {
  // Load token deployment by tokenId
  let tokenDeployment = getTokenDeploymentByTokenId(event.params.tokenId)
  if (tokenDeployment == null) {
    return // Skip if token not found
  }
  
  // Update migration status to MIGRATED
  tokenDeployment.migrationStatus = "MIGRATED"
  tokenDeployment.bondingProgress = BigDecimal.fromString("100")
  tokenDeployment.liquidityAvax = event.params.amountAVAX.toBigDecimal().div(BigDecimal.fromString("1000000000000000000"))
  tokenDeployment.lastUpdateTimestamp = event.block.timestamp
  
  tokenDeployment.save()
  
  // Update global stats
  let globalStats = GlobalStats.load("global")
  if (globalStats != null) {
    globalStats.migratedTokens = globalStats.migratedTokens + 1
    globalStats.activeTokens = globalStats.activeTokens - 1
    globalStats.save()
  }
}

function getTokenDeploymentByTokenId(tokenId: BigInt): TokenDeployment | null {
  // Create a lookup ID based on tokenId
  let lookupId = "token-" + tokenId.toString()
  
  // For now, we'll need to iterate through token deployments to find the matching tokenId
  // This is not optimal but works until we implement a proper mapping
  // In a production system, you'd want to maintain a separate TokenIdMapping entity
  
  // Since we can't easily iterate in AssemblyScript, we'll use a workaround
  // We'll store tokens with a predictable ID pattern and try to load them
  
  // Alternative approach: try to load by tokenId directly
  // This assumes we modify the token creation to also store by tokenId
  let tokenDeployment = TokenDeployment.load(lookupId)
  if (tokenDeployment != null) {
    return tokenDeployment
  }
  
  // If not found, return null for now
  // In the real implementation, you'd want to handle this better
  return null
}

function updateUserActivity(userAddress: Address, avaxAmount: BigDecimal, tokensBought: BigDecimal, tokensSold: BigDecimal, feesSpent: BigDecimal, timestamp: BigInt): void {
  let userActivity = UserActivity.load(userAddress.toHexString())
  if (userActivity == null) {
    userActivity = new UserActivity(userAddress.toHexString())
    userActivity.userAddress = userAddress
    userActivity.totalTrades = 0
    userActivity.totalVolumeAvax = BigDecimal.fromString("0")
    userActivity.totalTokensBought = BigDecimal.fromString("0")
    userActivity.totalTokensSold = BigDecimal.fromString("0")
    userActivity.totalFeesSpent = BigDecimal.fromString("0")
    userActivity.uniqueTokensTraded = 0
    userActivity.firstTradeTimestamp = timestamp
    userActivity.lastTradeTimestamp = timestamp
  }
  
  userActivity.totalTrades = userActivity.totalTrades + 1
  userActivity.totalVolumeAvax = userActivity.totalVolumeAvax.plus(avaxAmount)
  userActivity.totalTokensBought = userActivity.totalTokensBought.plus(tokensBought)
  userActivity.totalTokensSold = userActivity.totalTokensSold.plus(tokensSold)
  userActivity.totalFeesSpent = userActivity.totalFeesSpent.plus(feesSpent)
  userActivity.lastTradeTimestamp = timestamp
  
  userActivity.save()
}

function createPriceSnapshot(token: TokenDeployment, price: BigDecimal, volume: BigDecimal, timestamp: BigInt, period: string): void {
  let hourTimestamp = timestamp.toI32() / 3600 * 3600
  let snapshotId = token.id + "-" + hourTimestamp.toString()
  
  let snapshot = PriceSnapshot.load(snapshotId)
  if (snapshot == null) {
    snapshot = new PriceSnapshot(snapshotId)
    snapshot.token = token.id
    snapshot.priceAvax = price
    snapshot.volumeAvax = BigDecimal.fromString("0")
    snapshot.trades = 0
    snapshot.timestamp = BigInt.fromI32(hourTimestamp)
    snapshot.period = period
  }
  
  snapshot.volumeAvax = snapshot.volumeAvax.plus(volume)
  snapshot.trades = snapshot.trades + 1
  snapshot.priceAvax = price // Update to latest price in this hour
  
  snapshot.save()
}

function updateDailyStats(timestamp: BigInt, volume: BigDecimal, isNewToken: boolean): void {
  let dayTimestamp = timestamp.toI32() / 86400
  let dayId = dayTimestamp.toString()
  
  let dailyStats = DailyStats.load(dayId)
  if (dailyStats == null) {
    dailyStats = new DailyStats(dayId)
    dailyStats.date = dayId
    dailyStats.totalTokens = 0
    dailyStats.newTokens = 0
    dailyStats.migratedTokens = 0
    dailyStats.totalVolume = BigDecimal.fromString("0")
    dailyStats.totalTrades = 0
    dailyStats.uniqueTraders = 0
    dailyStats.totalProtocolFees = BigDecimal.fromString("0")
    dailyStats.totalCreatorFees = BigDecimal.fromString("0")
    dailyStats.totalReferralFees = BigDecimal.fromString("0")
    dailyStats.averageTokenPrice = BigDecimal.fromString("0")
    dailyStats.totalMarketCap = BigDecimal.fromString("0")
    dailyStats.totalLiquidity = BigDecimal.fromString("0")
  }
  
  if (isNewToken) {
    dailyStats.totalTokens = dailyStats.totalTokens + 1
    dailyStats.newTokens = dailyStats.newTokens + 1
  } else {
    dailyStats.totalVolume = dailyStats.totalVolume.plus(volume)
    dailyStats.totalTrades = dailyStats.totalTrades + 1
    dailyStats.totalProtocolFees = dailyStats.totalProtocolFees.plus(volume.times(BigDecimal.fromString("0.02")))
    dailyStats.totalCreatorFees = dailyStats.totalCreatorFees.plus(volume.times(BigDecimal.fromString("0.01")))
  }
  
  dailyStats.save()
}

function updateGlobalStats(timestamp: BigInt, volume: BigDecimal, isNewToken: boolean): void {
  let globalStats = GlobalStats.load("global")
  if (globalStats == null) {
    globalStats = new GlobalStats("global")
    globalStats.totalTokensCreated = 0
    globalStats.totalVolumeAllTime = BigDecimal.fromString("0")
    globalStats.totalTradesAllTime = 0
    globalStats.totalUsersAllTime = 0
    globalStats.activeTokens = 0
    globalStats.migratedTokens = 0
    globalStats.totalValueLocked = BigDecimal.fromString("0")
    globalStats.lastUpdateTimestamp = timestamp
  }
  
  if (isNewToken) {
    globalStats.totalTokensCreated = globalStats.totalTokensCreated + 1
    globalStats.activeTokens = globalStats.activeTokens + 1
  } else {
    globalStats.totalVolumeAllTime = globalStats.totalVolumeAllTime.plus(volume)
    globalStats.totalTradesAllTime = globalStats.totalTradesAllTime + 1
  }
  
  globalStats.lastUpdateTimestamp = timestamp
  globalStats.save()
} 