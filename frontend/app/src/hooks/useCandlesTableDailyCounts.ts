import { useQuery } from '@tanstack/react-query'

import { fetchCandlesTableDailyCounts } from '../api/dataCollections'

export const CANDLES_TABLE_DAILY_COUNTS_QUERY_KEY = 'candles-table-daily-counts'

export const useCandlesTableDailyCounts = () => {
  return useQuery({
    queryKey: [CANDLES_TABLE_DAILY_COUNTS_QUERY_KEY],
    queryFn: fetchCandlesTableDailyCounts,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}
