import { createPublicClient, http } from 'viem'
import { avalanche } from 'viem/chains'

// RPC limits
const MAX_BLOCKS_PER_REQUEST = 2000
const MAX_RETRIES = 3
const RETRY_DELAY = 1000

// Client instance
const client = createPublicClient({
  chain: avalanche,
  transport: http(process.env.NEXT_PUBLIC_RPC_URL || 'https://api.avax.network/ext/bc/C/rpc')
})

/**
 * Safely fetch logs in batches to avoid RPC limits
 */
export async function fetchLogsInBatches(params: {
  address: string
  event: any
  fromBlock: bigint
  toBlock: bigint | 'latest'
  maxBlocksPerBatch?: number
}) {
  const {
    address,
    event,
    fromBlock,
    toBlock,
    maxBlocksPerBatch = MAX_BLOCKS_PER_REQUEST
  } = params

  const currentBlock = toBlock === 'latest' ? await client.getBlockNumber() : toBlock
  const totalBlocks = Number(currentBlock - fromBlock)

  // If within limits, fetch directly
  if (totalBlocks <= maxBlocksPerBatch) {
    return await fetchLogsWithRetry({
      address: address as `0x${string}`,
      event,
      fromBlock,
      toBlock: currentBlock
    })
  }

  // Batch fetch
  const allLogs: any[] = []
  let currentFromBlock = fromBlock

  while (currentFromBlock < currentBlock) {
    const currentToBlock = currentFromBlock + BigInt(maxBlocksPerBatch)
    const actualToBlock = currentToBlock > currentBlock ? currentBlock : currentToBlock

    try {
      const logs = await fetchLogsWithRetry({
        address: address as `0x${string}`,
        event,
        fromBlock: currentFromBlock,
        toBlock: actualToBlock
      })

      allLogs.push(...logs)
      currentFromBlock = actualToBlock + 1n

      // Small delay between batches to be nice to RPC
      if (currentFromBlock < currentBlock) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    } catch (error) {
      console.error(`Error fetching logs for blocks ${currentFromBlock} to ${actualToBlock}:`, error)
      // Continue with next batch even if one fails
      currentFromBlock = actualToBlock + 1n
    }
  }

  return allLogs
}

/**
 * Fetch logs with retry logic
 */
async function fetchLogsWithRetry(params: {
  address: `0x${string}`
  event: any
  fromBlock: bigint
  toBlock: bigint
}) {
  let lastError: Error | null = null

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      return await client.getLogs(params)
    } catch (error: any) {
      lastError = error
      
      // If it's a block range error, don't retry
      if (error.message?.includes('too many blocks') || error.message?.includes('maximum is set to')) {
        throw error
      }

      // Wait before retrying
      if (attempt < MAX_RETRIES - 1) {
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (attempt + 1)))
      }
    }
  }

  throw lastError || new Error('Failed to fetch logs after retries')
}

/**
 * Get a safe block range for the last N hours
 */
export function getSafeBlockRange(hours: number, currentBlock?: bigint): { fromBlock: bigint, maxBlocks: number } {
  // Avalanche has ~2 second block time
  const blocksPerHour = 1800 // 3600 seconds / 2 seconds per block
  const requestedBlocks = hours * blocksPerHour
  
  // Limit to safe range
  const maxBlocks = Math.min(requestedBlocks, MAX_BLOCKS_PER_REQUEST)
  const fromBlock = currentBlock ? currentBlock - BigInt(maxBlocks) : 0n

  return { fromBlock, maxBlocks }
}

/**
 * Format block range error messages
 */
export function formatBlockRangeError(error: any): string {
  if (error.message?.includes('too many blocks')) {
    return 'Requested too many blocks. Try reducing the time range or use batch fetching.'
  }
  if (error.message?.includes('maximum is set to')) {
    const match = error.message.match(/maximum is set to (\d+)/)
    const maxBlocks = match ? match[1] : '2048'
    return `RPC endpoint limits requests to ${maxBlocks} blocks. Consider using smaller time ranges.`
  }
  return error.message || 'Unknown blockchain error'
} 