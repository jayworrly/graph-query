import { SignerSet as SignerSetEvent } from "../generated/TransparentUpgradeableProxy/TransparentUpgradeableProxy"
import { SignerSet } from "../generated/schema"

export function handleSignerSet(event: SignerSetEvent): void {
  let entity = new SignerSet(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  )
  
  entity.user = event.params.user
  entity.signer = event.params.signer
  entity.previousSigner = event.params.previousSigner
  
  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash

  entity.save()
}
