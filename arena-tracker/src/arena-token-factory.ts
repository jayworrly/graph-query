import { TokenCreated, TokenBonded } from "../generated/ArenaTokenFactory/ArenaTokenFactory"
import { TokenDeployment, BondingEvent, DailyStats } from "../generated/schema"
import { BigInt, BigDecimal } from "@graphprotocol/graph-ts"

export function handleTokenCreated(event: TokenCreated): void {
  let tokenId = event.params.tokenId
  let params = event.params.params
  let tokenSupply = event.params.tokenSupply
  
  let tokenAddress = params.tokenContractAddress
  let tokenDeployment = new TokenDeployment(tokenAddress.toHexString())
  
  tokenDeployment.tokenAddress = tokenAddress
  tokenDeployment.creator = params.creatorAddress
  tokenDeployment.tokenId = tokenId
  tokenDeployment.deployedAt = event.block.timestamp
  tokenDeployment.bondingProgress = BigDecimal.fromString("0")
  tokenDeployment.migrationStatus = params.lpDeployed ? "MIGRATED" : "BONDING"
  tokenDeployment.totalVolume = BigInt.fromI32(0)
  tokenDeployment.totalTrades = 0
  
  tokenDeployment.save()
  
  // Update daily stats
  updateDailyStats(event.block.timestamp, BigInt.fromI32(0), 0)
}

export function handleTokenBonded(event: TokenBonded): void {
  let bondingEvent = new BondingEvent(
    event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  )
  
  // Load token deployment
  let tokenDeployment = TokenDeployment.load(event.params.tokenAddress.toHexString())
  if (tokenDeployment == null) {
    return // Skip if token not found
  }
  
  bondingEvent.token = tokenDeployment.id
  bondingEvent.user = event.params.user
  bondingEvent.avaxAmount = event.params.avaxAmount
  bondingEvent.tokenAmount = event.params.tokenAmount
  bondingEvent.bondingProgress = event.params.bondingProgress.toBigDecimal().div(BigDecimal.fromString("100"))
  bondingEvent.tradeType = "BUY"
  bondingEvent.timestamp = event.block.timestamp
  bondingEvent.blockNumber = event.block.number
  bondingEvent.transactionHash = event.transaction.hash
  
  bondingEvent.save()
  
  // Update token deployment
  tokenDeployment.bondingProgress = bondingEvent.bondingProgress
  tokenDeployment.totalVolume = tokenDeployment.totalVolume.plus(event.params.avaxAmount)
  tokenDeployment.totalTrades = tokenDeployment.totalTrades + 1
  
  // Update migration status based on bonding progress
  if (bondingEvent.bondingProgress.ge(BigDecimal.fromString("0.8"))) {
    tokenDeployment.migrationStatus = "CLOSE_TO_MIGRATION"
  }
  if (bondingEvent.bondingProgress.ge(BigDecimal.fromString("1"))) {
    tokenDeployment.migrationStatus = "MIGRATED"
  }
  
  tokenDeployment.save()
  
  // Update daily stats
  updateDailyStats(event.block.timestamp, event.params.avaxAmount, 1)
}

function updateDailyStats(timestamp: BigInt, volume: BigInt, trades: i32): void {
  let dayTimestamp = timestamp.toI32() / 86400
  let dayId = dayTimestamp.toString()
  
  let dailyStats = DailyStats.load(dayId)
  if (dailyStats == null) {
    dailyStats = new DailyStats(dayId)
    dailyStats.date = dayId
    dailyStats.totalTokens = 0
    dailyStats.totalVolume = BigInt.fromI32(0)
    dailyStats.totalTrades = 0
    dailyStats.uniqueTraders = 0
  }
  
  if (trades == 0) {
    dailyStats.totalTokens = dailyStats.totalTokens + 1
  } else {
    dailyStats.totalVolume = dailyStats.totalVolume.plus(volume)
    dailyStats.totalTrades = dailyStats.totalTrades + trades
  }
  
  dailyStats.save()
} 