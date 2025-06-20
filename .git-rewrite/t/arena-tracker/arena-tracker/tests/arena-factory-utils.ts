import { newMockEvent } from "matchstick-as"
import { ethereum, Address, BigInt } from "@graphprotocol/graph-ts"
import {
  PairCreated,
  ProtocolFeeInfoSet
} from "../generated/ArenaFactory/ArenaFactory"

export function createPairCreatedEvent(
  token0: Address,
  token1: Address,
  pair: Address,
  param3: BigInt
): PairCreated {
  let pairCreatedEvent = changetype<PairCreated>(newMockEvent())

  pairCreatedEvent.parameters = new Array()

  pairCreatedEvent.parameters.push(
    new ethereum.EventParam("token0", ethereum.Value.fromAddress(token0))
  )
  pairCreatedEvent.parameters.push(
    new ethereum.EventParam("token1", ethereum.Value.fromAddress(token1))
  )
  pairCreatedEvent.parameters.push(
    new ethereum.EventParam("pair", ethereum.Value.fromAddress(pair))
  )
  pairCreatedEvent.parameters.push(
    new ethereum.EventParam("param3", ethereum.Value.fromUnsignedBigInt(param3))
  )

  return pairCreatedEvent
}

export function createProtocolFeeInfoSetEvent(
  feeReceiverAddress: Address,
  feePercentageInBps: BigInt,
  previousFeePercentageInBps: BigInt
): ProtocolFeeInfoSet {
  let protocolFeeInfoSetEvent = changetype<ProtocolFeeInfoSet>(newMockEvent())

  protocolFeeInfoSetEvent.parameters = new Array()

  protocolFeeInfoSetEvent.parameters.push(
    new ethereum.EventParam(
      "feeReceiverAddress",
      ethereum.Value.fromAddress(feeReceiverAddress)
    )
  )
  protocolFeeInfoSetEvent.parameters.push(
    new ethereum.EventParam(
      "feePercentageInBps",
      ethereum.Value.fromUnsignedBigInt(feePercentageInBps)
    )
  )
  protocolFeeInfoSetEvent.parameters.push(
    new ethereum.EventParam(
      "previousFeePercentageInBps",
      ethereum.Value.fromUnsignedBigInt(previousFeePercentageInBps)
    )
  )

  return protocolFeeInfoSetEvent
}
