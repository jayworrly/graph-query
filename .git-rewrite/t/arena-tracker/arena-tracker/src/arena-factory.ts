import {
  PairCreated as PairCreatedEvent,
  ProtocolFeeInfoSet as ProtocolFeeInfoSetEvent,
} from "../generated/ArenaFactory/ArenaFactory"
import { PairCreated, ProtocolFeeInfoSet } from "../generated/schema"

export function handlePairCreated(event: PairCreatedEvent): void {
  let entity = new PairCreated(
    event.transaction.hash.concatI32(event.logIndex.toI32()),
  )
  entity.token0 = event.params.token0
  entity.token1 = event.params.token1
  entity.pair = event.params.pair
  entity.param3 = event.params.param3

  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash

  entity.save()
}

export function handleProtocolFeeInfoSet(event: ProtocolFeeInfoSetEvent): void {
  let entity = new ProtocolFeeInfoSet(
    event.transaction.hash.concatI32(event.logIndex.toI32()),
  )
  entity.feeReceiverAddress = event.params.feeReceiverAddress
  entity.feePercentageInBps = event.params.feePercentageInBps
  entity.previousFeePercentageInBps = event.params.previousFeePercentageInBps

  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash

  entity.save()
}
