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

