import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { fetchOpsSignalsByDate, type OpsSignalByDateEntry } from '../api/ops'

export const OPS_SIGNALS_BY_DATE_QUERY_KEY = ['ops', 'signals', 'by-date'] as const

export const useOpsSignalsByDate = (date: string) => {
  return useQuery<OpsSignalByDateEntry[], Error>({
    queryKey: [...OPS_SIGNALS_BY_DATE_QUERY_KEY, date] as const,
    queryFn: () => fetchOpsSignalsByDate(date),
    enabled: Boolean(date),
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  })
}
