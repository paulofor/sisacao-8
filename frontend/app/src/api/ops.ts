import dayjs from 'dayjs'

import { apiClient } from './client'

export type OpsHealthStatus = 'OK' | 'WARN' | 'FAIL' | 'ERROR' | 'PASS' | 'READY' | 'UNKNOWN' | string
export type OpsSignalSide = 'BUY' | 'SELL' | string

export interface OpsOverview {
  asOf: string | null
  lastTradingDay: string | null
  nextTradingDay: string | null
  pipelineHealth: OpsHealthStatus | null
  dqHealth: OpsHealthStatus | null
  signalsReady: boolean
  signalsCount: number
  lastSignalsGeneratedAt: string | null
}

export interface OpsPipelineJob {
  jobName: string
  lastRunAt: string | null
  lastStatus: OpsHealthStatus | null
  minutesSinceLastRun: number
  deadlineAt: string | null
  silent: boolean
  lastRunId: string | null
}

export interface OpsDqCheck {
  checkDate: string | null
  checkName: string
  status: OpsHealthStatus | null
  details: string | null
  createdAt: string | null
}

export interface OpsSignalNext {
  validFor: string | null
  ticker: string
  side: OpsSignalSide
  entry: number | null
  target: number | null
  stop: number | null
  score: number | null
  rank: number | null
  createdAt: string | null
}

export interface OpsSignalHistoryEntry extends OpsSignalNext {
  dateRef: string | null
}

export interface OpsSignalByDateEntry extends OpsSignalHistoryEntry {
  nextTradingDay: string | null
  nextDayHigh: number | null
  nextDayLow: number | null
}

export interface OpsSignalsHistoryFilters {
  from: string
  to: string
  limit?: number
}

export interface OpsBacktestTrade {
  dateRef: string | null
  ticker: string
  side: OpsSignalSide
  entry: number | null
  exit: number | null
  outcome: string | null
  pnlPct: number | null
  entryDate: string | null
  entryPrice: number | null
  exitDate: string | null
  exitPrice: number | null
  daysInTrade: number | null
  entryLimitPrice: number | null
  entrySignalScore: number | null
  createdAt: string | null
}

export interface OpsIncident {
  incidentId: string
  checkName: string
  checkDate: string | null
  severity: OpsHealthStatus | null
  source: string
  summary: string
  status: string
  runId: string | null
  createdAt: string | null
}

const asString = (value: unknown, fallback = ''): string => {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toString()
  }
  return fallback
}

const asNullableString = (value: unknown): string | null => {
  const normalized = asString(value).trim()
  return normalized ? normalized : null
}

const asUpperString = (value: unknown): string | null => {
  const normalized = asNullableString(value)
  return normalized ? normalized.toUpperCase() : null
}

const toBoolean = (value: unknown): boolean => {
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'number') {
    return value !== 0
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    return normalized === 'true' || normalized === '1' || normalized === 'yes'
  }
  return false
}

const toNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const sanitized = value.replace(/[^0-9.,-]/g, '').replace(',', '.')
    if (!sanitized) {
      return null
    }
    const parsed = Number.parseFloat(sanitized)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const toInteger = (value: unknown): number => {
  const parsed = toNumber(value)
  if (parsed === null) {
    return 0
  }
  return Math.trunc(parsed)
}

const toPositiveInteger = (value: unknown): number | undefined => {
  const parsed = toInteger(value)
  return parsed > 0 ? parsed : undefined
}

const toIsoDateTime = (value: unknown): string | null => {
  if (value instanceof Date) {
    return value.toISOString()
  }
  if (typeof value === 'string') {
    const parsed = dayjs(value)
    return parsed.isValid() ? parsed.toISOString() : value
  }
  return null
}

const toIsoDate = (value: unknown): string | null => {
  if (value instanceof Date) {
    return dayjs(value).format('YYYY-MM-DD')
  }
  if (typeof value === 'string') {
    const parsed = dayjs(value)
    return parsed.isValid() ? parsed.format('YYYY-MM-DD') : value
  }
  return null
}

const stringifyDetails = (value: unknown): string | null => {
  if (typeof value === 'string') {
    return value
  }
  if (value && typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return null
    }
  }
  return null
}

export const fetchOpsOverview = async (): Promise<OpsOverview | null> => {
  const response = await apiClient.get<unknown>('/ops/overview')
  const payload = response.data
  if (!payload || typeof payload !== 'object') {
    return null
  }
  const data = payload as Record<string, unknown>

  return {
    asOf: toIsoDateTime(data.asOf ?? data.timestamp),
    lastTradingDay: toIsoDate(data.lastTradingDay ?? data.last_trading_day),
    nextTradingDay: toIsoDate(data.nextTradingDay ?? data.next_trading_day),
    pipelineHealth: asUpperString(data.pipelineHealth ?? data.pipeline_health),
    dqHealth: asUpperString(data.dqHealth ?? data.dq_health),
    signalsReady: toBoolean(data.signalsReady ?? data.signals_ready),
    signalsCount: toInteger(data.signalsCount ?? data.signals_count),
    lastSignalsGeneratedAt: toIsoDateTime(data.lastSignalsGeneratedAt ?? data.last_signals_generated_at),
  }
}

export const fetchOpsPipeline = async (): Promise<OpsPipelineJob[]> => {
  const response = await apiClient.get<unknown>('/ops/pipeline')
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      jobName: asString(record.jobName ?? record.job_name ?? record.job) || '—',
      lastRunAt: toIsoDateTime(record.lastRunAt ?? record.last_run_at ?? record.lastRun),
      lastStatus: asUpperString(record.lastStatus ?? record.last_status ?? record.status),
      minutesSinceLastRun: toInteger(record.minutesSinceLastRun ?? record.minutes_since_last_run),
      deadlineAt: toIsoDateTime(record.deadlineAt ?? record.deadline_at ?? record.deadline),
      silent: toBoolean(record.silent ?? record.isSilent),
      lastRunId: asNullableString(record.lastRunId ?? record.last_run_id ?? record.runId),
    }
  })
}

export const fetchOpsDqLatest = async (): Promise<OpsDqCheck[]> => {
  const response = await apiClient.get<unknown>('/ops/dq/latest')
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      checkDate: toIsoDate(record.checkDate ?? record.check_date ?? record.data_ref),
      checkName: asString(record.checkName ?? record.check_name ?? record.name) || '—',
      status: asUpperString(record.status ?? record.result),
      details: stringifyDetails(record.details ?? record.observations ?? record.metadata),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at ?? record.timestamp),
    }
  })
}

export const fetchOpsSignalsNext = async (): Promise<OpsSignalNext[]> => {
  const response = await apiClient.get<unknown>('/ops/signals/next')
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      validFor: toIsoDate(record.validFor ?? record.valid_for ?? record.date),
      ticker: asString(record.ticker) || '—',
      side: (asUpperString(record.side) as OpsSignalSide) ?? '—',
      entry: toNumber(record.entry ?? record.entry_price ?? record.preco_entrada),
      target: toNumber(record.target ?? record.target_price ?? record.preco_alvo),
      stop: toNumber(record.stop ?? record.stop_loss ?? record.preco_stop),
      score: toNumber(record.score),
      rank: toNumber(record.rank),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at ?? record.timestamp),
    }
  })
}

export const fetchOpsSignalsHistory = async (
  filters: OpsSignalsHistoryFilters,
): Promise<OpsSignalHistoryEntry[]> => {
  const response = await apiClient.get<unknown>('/ops/signals/history', {
    params: {
      from: filters.from,
      to: filters.to,
      limit: toPositiveInteger(filters.limit) ?? undefined,
    },
  })
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      dateRef: toIsoDate(record.dateRef ?? record.date_ref ?? record.generated_at),
      validFor: toIsoDate(record.validFor ?? record.valid_for ?? record.validDate),
      ticker: asString(record.ticker) || '—',
      side: (asUpperString(record.side) as OpsSignalSide) ?? '—',
      entry: toNumber(record.entry ?? record.entry_price ?? record.preco_entrada),
      target: toNumber(record.target ?? record.target_price ?? record.preco_alvo),
      stop: toNumber(record.stop ?? record.stop_loss ?? record.preco_stop),
      score: toNumber(record.score),
      rank: toNumber(record.rank),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at ?? record.timestamp),
    }
  })
}

export const fetchOpsSignalsByDate = async (date: string): Promise<OpsSignalByDateEntry[]> => {
  const response = await apiClient.get<unknown>('/ops/signals/by-date', { params: { date } })
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      dateRef: toIsoDate(record.dateRef ?? record.date_ref),
      validFor: toIsoDate(record.validFor ?? record.valid_for ?? record.validDate),
      ticker: asString(record.ticker) || '—',
      side: (asUpperString(record.side) as OpsSignalSide) ?? '—',
      entry: toNumber(record.entry ?? record.entry_price ?? record.preco_entrada),
      target: toNumber(record.target ?? record.target_price ?? record.preco_alvo),
      stop: toNumber(record.stop ?? record.stop_loss ?? record.preco_stop),
      score: toNumber(record.score),
      rank: toNumber(record.rank),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at ?? record.timestamp),
      nextTradingDay: toIsoDate(record.nextTradingDay ?? record.next_trading_day),
      nextDayHigh: toNumber(record.nextDayHigh ?? record.next_day_high ?? record.high),
      nextDayLow: toNumber(record.nextDayLow ?? record.next_day_low ?? record.low),
    }
  })
}

export const fetchOpsIncidentsOpen = async (): Promise<OpsIncident[]> => {
  const response = await apiClient.get<unknown>('/ops/incidents/open')
  const items = Array.isArray(response.data) ? response.data : []

  return items.map((item) => {
    const record = item as Record<string, unknown>

    return {
      incidentId: asString(record.incidentId ?? record.incident_id ?? record.id) || '—',
      checkName: asString(record.checkName ?? record.check_name ?? record.metric) || '—',
      checkDate: toIsoDate(record.checkDate ?? record.check_date ?? record.date_ref),
      severity: asUpperString(record.severity ?? record.priority),
      source: asString(record.source ?? record.origin) || '—',
      summary: asString(record.summary ?? record.description ?? 'Sem descrição'),
      status: asUpperString(record.status) ?? '—',
      runId: asNullableString(record.runId ?? record.run_id),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at ?? record.timestamp),
    }
  })
}


export const fetchOpsBacktestTrades = async (limit = 50): Promise<OpsBacktestTrade[]> => {
  const response = await apiClient.get<unknown>('/ops/backtest/trades', { params: { limit } })
  const items = Array.isArray(response.data) ? response.data : []
  return items.map((item) => {
    const record = item as Record<string, unknown>
    return {
      dateRef: toIsoDate(record.dateRef ?? record.date_ref),
      ticker: asString(record.ticker) || '—',
      side: (asUpperString(record.side) as OpsSignalSide) ?? '—',
      entry: toNumber(record.entry),
      exit: toNumber(record.exit),
      outcome: asNullableString(record.outcome),
      pnlPct: toNumber(record.pnlPct ?? record.pnl_pct),
      entryDate: toIsoDate(record.entryDate ?? record.entry_date ?? record.trade_entry_date),
      entryPrice: toNumber(record.entryPrice ?? record.entry_price ?? record.trade_entry_price ?? record.entry),
      exitDate: toIsoDate(record.exitDate ?? record.exit_date ?? record.trade_exit_date),
      exitPrice: toNumber(record.exitPrice ?? record.exit_price ?? record.trade_exit_price ?? record.exit),
      daysInTrade: toNumber(record.daysInTrade ?? record.days_in_trade ?? record.holding_days ?? record.days),
      entryLimitPrice: toNumber(record.entryLimitPrice ?? record.entry_limit_price ?? record.limit_price ?? record.trigger_price),
      entrySignalScore: toNumber(record.entrySignalScore ?? record.entry_signal_score ?? record.signal_score ?? record.score),
      createdAt: toIsoDateTime(record.createdAt ?? record.created_at),
    }
  })
}

export interface QuantDataInventorySummary {
  activeTickers: number
  totalTickers: number
  dailyTickers: number
  intradayTickers: number
  firstAvailableDate: string | null
  lastAvailableDate: string | null
  dailyCandles: number
  intradayCandles: number
  validDataPct: number | null
  lastUpdate: string | null
}

export interface QuantTickerCoverage {
  ticker: string
  company: string | null
  active: boolean
  firstDate: string | null
  lastDate: string | null
  daysWithData: number
  expectedDays: number
  coveragePct: number | null
  avgFinancialVolume: number | null
  invalidPriceDays: number
  invalidVolumeDays: number
  duplicateDays: number
  eligibilityStatus: string
}


export interface QuantBaselineStrategy {
  strategyId: string
  strategyFamily: string
  strategyVersion: string
  hypothesis: string | null
  configuredStatus: string | null
  generatedSignals: number
  signalDays: number
  lastSignalDate: string | null
  trades: number | null
  expectancyNetPct: number | null
  profitFactor: number | null
  maxDrawdownPct: number | null
  robustnessScore: number | null
  computedStatus: string | null
}

export interface QuantStrategyDetailAlert {
  strategyId: string
  strategyVersion: string
  generatedSignals: number
  trades: number | null
  expectancyNetPct: number | null
  profitFactor: number | null
  maxDrawdownPct: number | null
  alerts: string[]
}

export interface QuantDataQualityIncident {
  incidentType: string
  severity: string
  ticker: string
  incidentDate: string | null
  recommendation: string | null
}

export const fetchQuantDataInventorySummary = async (): Promise<QuantDataInventorySummary | null> => {
  const response = await apiClient.get<unknown>('/ops/quant/inventory-summary')
  const data = response.data as Record<string, unknown> | null
  if (!data || typeof data !== 'object') {
    return null
  }
  return {
    activeTickers: toInteger(data.activeTickers ?? data.active_tickers),
    totalTickers: toInteger(data.totalTickers ?? data.total_tickers),
    dailyTickers: toInteger(data.dailyTickers ?? data.daily_tickers),
    intradayTickers: toInteger(data.intradayTickers ?? data.intraday_tickers),
    firstAvailableDate: toIsoDate(data.firstAvailableDate ?? data.first_available_date),
    lastAvailableDate: toIsoDate(data.lastAvailableDate ?? data.last_available_date),
    dailyCandles: toInteger(data.dailyCandles ?? data.daily_candles),
    intradayCandles: toInteger(data.intradayCandles ?? data.intraday_candles),
    validDataPct: toNumber(data.validDataPct ?? data.valid_data_pct),
    lastUpdate: toIsoDateTime(data.lastUpdate ?? data.last_update),
  }
}

export const fetchQuantTickerCoverage = async (limit = 100): Promise<QuantTickerCoverage[]> => {
  const response = await apiClient.get<unknown>('/ops/quant/ticker-coverage', { params: { limit } })
  const items = Array.isArray(response.data) ? response.data : []
  return items.map((item) => {
    const record = item as Record<string, unknown>
    return {
      ticker: asString(record.ticker, '—'),
      company: asNullableString(record.company ?? record.empresa),
      active: toBoolean(record.active ?? record.ativo),
      firstDate: toIsoDate(record.firstDate ?? record.first_date),
      lastDate: toIsoDate(record.lastDate ?? record.last_date),
      daysWithData: toInteger(record.daysWithData ?? record.days_with_data),
      expectedDays: toInteger(record.expectedDays ?? record.expected_days),
      coveragePct: toNumber(record.coveragePct ?? record.coverage_pct),
      avgFinancialVolume: toNumber(record.avgFinancialVolume ?? record.avg_financial_volume),
      invalidPriceDays: toInteger(record.invalidPriceDays ?? record.invalid_price_days),
      invalidVolumeDays: toInteger(record.invalidVolumeDays ?? record.invalid_volume_days),
      duplicateDays: toInteger(record.duplicateDays ?? record.duplicate_days),
      eligibilityStatus: asString(record.eligibilityStatus ?? record.eligibility_status, '—'),
    }
  })
}

export const fetchQuantDataQualityIncidents = async (limit = 100): Promise<QuantDataQualityIncident[]> => {
  const response = await apiClient.get<unknown>('/ops/quant/data-quality-incidents', { params: { limit } })
  const items = Array.isArray(response.data) ? response.data : []
  return items.map((item) => {
    const record = item as Record<string, unknown>
    return {
      incidentType: asString(record.incidentType ?? record.incident_type, '—'),
      severity: asString(record.severity, '—'),
      ticker: asString(record.ticker, '—'),
      incidentDate: toIsoDate(record.incidentDate ?? record.incident_date),
      recommendation: asNullableString(record.recommendation),
    }
  })
}


export const fetchQuantBaselineStrategies = async (): Promise<QuantBaselineStrategy[]> => {
  const response = await apiClient.get<unknown>('/ops/quant/strategies')
  const items = Array.isArray(response.data) ? response.data : []
  return items.map((item) => {
    const record = item as Record<string, unknown>
    return {
      strategyId: asString(record.strategyId ?? record.strategy_id, '—'),
      strategyFamily: asString(record.strategyFamily ?? record.strategy_family, '—'),
      strategyVersion: asString(record.strategyVersion ?? record.strategy_version, '—'),
      hypothesis: asNullableString(record.hypothesis),
      configuredStatus: asNullableString(record.configuredStatus ?? record.configured_status),
      generatedSignals: toInteger(record.generatedSignals ?? record.generated_signals),
      signalDays: toInteger(record.signalDays ?? record.signal_days),
      lastSignalDate: toIsoDate(record.lastSignalDate ?? record.last_signal_date),
      trades: toNumber(record.trades),
      expectancyNetPct: toNumber(record.expectancyNetPct ?? record.expectancy_net_pct),
      profitFactor: toNumber(record.profitFactor ?? record.profit_factor),
      maxDrawdownPct: toNumber(record.maxDrawdownPct ?? record.max_drawdown_pct),
      robustnessScore: toNumber(record.robustnessScore ?? record.robustness_score),
      computedStatus: asNullableString(record.computedStatus ?? record.computed_status),
    }
  })
}

export const fetchQuantStrategyDetailAlerts = async (): Promise<QuantStrategyDetailAlert[]> => {
  const response = await apiClient.get<unknown>('/ops/quant/strategies/alerts')
  const items = Array.isArray(response.data) ? response.data : []
  return items.map((item) => {
    const record = item as Record<string, unknown>
    const rawAlerts = record.alerts
    const alerts = Array.isArray(rawAlerts)
      ? rawAlerts.map((alert) => asString(alert)).filter(Boolean)
      : asString(rawAlerts).split('|').map((alert) => alert.trim()).filter(Boolean)

    return {
      strategyId: asString(record.strategyId ?? record.strategy_id, '—'),
      strategyVersion: asString(record.strategyVersion ?? record.strategy_version, '—'),
      generatedSignals: toInteger(record.generatedSignals ?? record.generated_signals),
      trades: toNumber(record.trades),
      expectancyNetPct: toNumber(record.expectancyNetPct ?? record.expectancy_net_pct),
      profitFactor: toNumber(record.profitFactor ?? record.profit_factor),
      maxDrawdownPct: toNumber(record.maxDrawdownPct ?? record.max_drawdown_pct),
      alerts,
    }
  })
}
