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

export interface OpsSignalsHistoryFilters {
  from: string
  to: string
  limit?: number
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
