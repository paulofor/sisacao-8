import type { OpsBacktestTrade } from '../../api/ops'

const NON_EXECUTED_OUTCOMES = new Set(['NO_FILL', 'NO FILL', 'NOT_FILLED', 'NOT FILLED'])

export const normalizeBacktestOutcome = (outcome: string | null | undefined): string => {
  const normalized = (outcome ?? '').trim().toUpperCase()
  return normalized || 'UNKNOWN'
}

export const isExecutedBacktestTrade = (trade: OpsBacktestTrade): boolean => {
  if (NON_EXECUTED_OUTCOMES.has(normalizeBacktestOutcome(trade.outcome))) {
    return false
  }

  return Boolean(trade.entryDate || trade.entryPrice !== null || trade.exitDate || trade.exitPrice !== null)
}
