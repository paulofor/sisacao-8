import { keepPreviousData, useQuery } from '@tanstack/react-query'

import {
  fetchOpsSignalsHistory,
  type OpsSignalHistoryEntry,
  type OpsSignalsHistoryFilters,
} from '../api/ops'

export const OPS_SIGNALS_HISTORY_QUERY_KEY = ['ops', 'signals', 'history'] as const

export const useOpsSignalsHistory = (filters: OpsSignalsHistoryFilters) => {
  return useQuery<OpsSignalHistoryEntry[], Error>({
    queryKey: [...OPS_SIGNALS_HISTORY_QUERY_KEY, filters] as const,
    queryFn: () => fetchOpsSignalsHistory(filters),
    enabled: Boolean(filters.from && filters.to),
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  })
}
