import { useQuery } from '@tanstack/react-query'

import { fetchDailyTableCounts, type DailyTableCount } from '../api/dataCollections'

export const DAILY_TABLE_COUNTS_QUERY_KEY = 'daily-table-counts'

export const useDailyTableCounts = () => {
  return useQuery<DailyTableCount[], Error>({
    queryKey: [DAILY_TABLE_COUNTS_QUERY_KEY],
    queryFn: () => fetchDailyTableCounts(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}
