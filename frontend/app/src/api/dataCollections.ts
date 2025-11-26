import type { AxiosResponse } from 'axios'
import dayjs from 'dayjs'

import { apiClient } from './client'

export type DataCollectionMessageSeverity =
  | 'SUCCESS'
  | 'INFO'
  | 'WARNING'
  | 'ERROR'
  | 'CRITICAL'
  | 'UNKNOWN'

export interface DataCollectionMessage {
  id: string
  collector: string
  severity: DataCollectionMessageSeverity | string
  summary: string
  dataset: string
  createdAt: string
  metadata?: Record<string, unknown>
}

export interface DataCollectionMessagesFilters {
  severity?: DataCollectionMessageSeverity
  collector?: string
  limit?: number
}

export interface IntradayTickerSummary {
  ticker: string
  price?: number | null
  success: boolean
  error?: string | null
}

export interface IntradaySummary {
  updatedAt?: string | null
  totalTickers: number
  successfulTickers: number
  failedTickers: number
  tickers: IntradayTickerSummary[]
}

export interface IntradayDailyCount {
  date: string
  totalRecords: number
}

type RawMessage = Record<string, unknown>

const toIsoString = (value: unknown): string => {
  if (typeof value === 'string') {
    const parsed = dayjs(value)
    if (parsed.isValid()) {
      return parsed.toISOString()
    }
    return value
  }
  if (value instanceof Date) {
    return value.toISOString()
  }
  return dayjs().toISOString()
}

const normalizeSeverity = (value: unknown): DataCollectionMessageSeverity | string => {
  const normalized = typeof value === 'string' ? value.toUpperCase() : undefined
  if (!normalized) {
    return 'UNKNOWN'
  }
  if (
    normalized === 'SUCCESS' ||
    normalized === 'INFO' ||
    normalized === 'WARNING' ||
    normalized === 'ERROR' ||
    normalized === 'CRITICAL'
  ) {
    return normalized
  }
  return normalized
}

const asString = (value: unknown, fallback = ''): string => {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number') {
    return value.toString()
  }
  return fallback
}

const asNullableString = (value: unknown): string | null => {
  const result = asString(value).trim()
  return result ? result : null
}

const normalizeNumericString = (value: string): number | null => {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }

  const sanitized = trimmed.replace(/[^0-9.,-]/g, '')
  if (!sanitized) {
    return null
  }

  const commaIndex = sanitized.lastIndexOf(',')
  const dotIndex = sanitized.lastIndexOf('.')
  let normalized = sanitized

  if (commaIndex >= 0 && dotIndex >= 0) {
    if (commaIndex > dotIndex) {
      normalized = sanitized.replace(/\./g, '').replace(',', '.')
    } else {
      normalized = sanitized.replace(/,/g, '')
    }
  } else if (commaIndex >= 0) {
    normalized = sanitized.replace(',', '.')
  }

  const parsed = Number.parseFloat(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

const normalizePrice = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    return normalizeNumericString(value)
  }

  if (typeof value === 'object' && value !== null && 'toString' in value) {
    return normalizeNumericString(String(value))
  }

  return null
}

const extractTickerPrice = (ticker: unknown): number | null => {
  if (ticker === null || typeof ticker !== 'object') {
    return null
  }

  const data = ticker as Record<string, unknown>
  const candidates: Array<unknown> = [
    data.price,
    data.valor,
    data.preco,
    data.precoFechamento,
    data.preco_fechamento,
    data.lastPrice,
  ]

  for (const candidate of candidates) {
    const normalized = normalizePrice(candidate)
    if (normalized !== null) {
      return normalized
    }
  }

  return null
}

const extractMessageArray = (response: AxiosResponse<unknown>): RawMessage[] => {
  const { data } = response
  if (Array.isArray(data)) {
    return data as RawMessage[]
  }
  if (data && typeof data === 'object') {
    const items = (data as Record<string, unknown>).items
    if (Array.isArray(items)) {
      return items as RawMessage[]
    }
  }
  return []
}

const ensureId = (message: RawMessage): string => {
  return (
    asString(message.id) ||
    asString(message.message_id) ||
    asString(message.event_id) ||
    asString(message.insertId) ||
    asString(message.created_at) ||
    asString(message.timestamp) ||
    `${Date.now()}-${Math.random()}`
  )
}

const ensureCollector = (message: RawMessage): string => {
  return (
    asString(message.collector) ||
    asString(message.source) ||
    asString(message.functionName) ||
    asString(message.pipeline) ||
    'desconhecido'
  )
}

const ensureDataset = (message: RawMessage): string => {
  return (
    asString(message.dataset) ||
    asString(message.table) ||
    asString(message.target_table) ||
    asString(message.resource) ||
    '—'
  )
}

const ensureSummary = (message: RawMessage): string => {
  return (
    asString(message.summary) ||
    asString(message.message) ||
    asString(message.description) ||
    'Mensagem não informada'
  )
}

const ensureCreatedAt = (message: RawMessage): string => {
  const rawTimestamp =
    message.createdAt ??
    message.created_at ??
    message.timestamp ??
    message.event_timestamp ??
    message.inserted_at ??
    new Date()

  return toIsoString(rawTimestamp)
}

export const fetchDataCollectionMessages = async (
  filters: DataCollectionMessagesFilters = {},
): Promise<DataCollectionMessage[]> => {
  const response = await apiClient.get<unknown>('/data-collections/messages', {
    params: {
      severity: filters.severity,
      collector: filters.collector,
      limit: filters.limit,
    },
  })

  return extractMessageArray(response)
    .map((item) => ({
      id: ensureId(item),
      collector: ensureCollector(item),
      severity: normalizeSeverity(item.severity ?? item.status ?? item.level),
      summary: ensureSummary(item),
      dataset: ensureDataset(item),
      createdAt: ensureCreatedAt(item),
      metadata: (item.metadata as Record<string, unknown> | undefined) ?? undefined,
    }))
    .sort((a, b) => dayjs(b.createdAt).valueOf() - dayjs(a.createdAt).valueOf())
}

const toInteger = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.trunc(value)
  }

  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10)
    return Number.isNaN(parsed) ? 0 : parsed
  }

  return 0
}

const toIsoDateString = (value: unknown): string => {
  if (typeof value === 'string') {
    const parsed = dayjs(value)
    if (parsed.isValid()) {
      return parsed.format('YYYY-MM-DD')
    }
    return value
  }

  if (value instanceof Date) {
    return dayjs(value).format('YYYY-MM-DD')
  }

  return ''
}

export const fetchIntradayDailyCounts = async (): Promise<IntradayDailyCount[]> => {
  const response = await apiClient.get<unknown>('/data-collections/intraday-daily-counts')
  const items = Array.isArray(response.data) ? response.data : []

  return items
    .map((item) => {
      const record = item as Record<string, unknown>
      const date = toIsoDateString(record.date ?? record.data ?? record.data_ref)
      const totalRecords = toInteger(record.totalRecords ?? record.total_registros ?? record.total)

      return { date, totalRecords }
    })
    .filter((item) => Boolean(item.date))
    .sort((a, b) => dayjs(b.date).valueOf() - dayjs(a.date).valueOf())
}

export const fetchIntradaySummary = async (): Promise<IntradaySummary> => {
  const response = await apiClient.get<unknown>('/data-collections/intraday-summary')
  const summary = response.data as Record<string, unknown>
  const tickers = Array.isArray(summary.tickers) ? summary.tickers : []

  return {
    updatedAt: asNullableString(summary.updatedAt),
    totalTickers: toInteger(summary.totalTickers),
    successfulTickers: toInteger(summary.successfulTickers),
    failedTickers: toInteger(summary.failedTickers),
    tickers: tickers.map((ticker) => {
      const tickerData = ticker as Record<string, unknown>

      return {
        ticker: asString(tickerData.ticker),
        price: extractTickerPrice(ticker),
        success: Boolean(tickerData.success),
        error: asNullableString(tickerData.error),
      }
    }),
  }
}

