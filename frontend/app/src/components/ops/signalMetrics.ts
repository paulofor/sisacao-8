import type { OpsSignalSide } from '../../api/ops'

const isFiniteNumber = (value: number | null): value is number => {
  return typeof value === 'number' && Number.isFinite(value)
}

const normalizeSide = (side: OpsSignalSide | null | undefined) => {
  return typeof side === 'string' ? side.toUpperCase() : ''
}

export interface SignalTradeMetrics {
  upsidePct: number | null
  downsidePct: number | null
  riskReward: number | null
}

export const calculateSignalTradeMetrics = (
  side: OpsSignalSide | null | undefined,
  entry: number | null,
  target: number | null,
  stop: number | null,
): SignalTradeMetrics => {
  if (!isFiniteNumber(entry) || entry <= 0 || !isFiniteNumber(target) || !isFiniteNumber(stop)) {
    return { upsidePct: null, downsidePct: null, riskReward: null }
  }

  const normalizedSide = normalizeSide(side)

  if (normalizedSide === 'BUY') {
    const upside = ((target - entry) / entry) * 100
    const downside = ((entry - stop) / entry) * 100
    const riskReward = downside > 0 ? upside / downside : null

    return {
      upsidePct: Number.isFinite(upside) ? upside : null,
      downsidePct: Number.isFinite(downside) ? downside : null,
      riskReward: riskReward !== null && Number.isFinite(riskReward) ? riskReward : null,
    }
  }

  if (normalizedSide === 'SELL') {
    const upside = ((entry - target) / entry) * 100
    const downside = ((stop - entry) / entry) * 100
    const riskReward = downside > 0 ? upside / downside : null

    return {
      upsidePct: Number.isFinite(upside) ? upside : null,
      downsidePct: Number.isFinite(downside) ? downside : null,
      riskReward: riskReward !== null && Number.isFinite(riskReward) ? riskReward : null,
    }
  }

  return { upsidePct: null, downsidePct: null, riskReward: null }
}
