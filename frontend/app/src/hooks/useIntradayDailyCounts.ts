import { useQuery } from '@tanstack/react-query'

import { fetchIntradayDailyCounts, type IntradayDailyCount } from '../api/dataCollections'

export const INTRADAY_DAILY_COUNTS_QUERY_KEY = 'intraday-daily-counts'

export const useIntradayDailyCounts = () => {
  return useQuery<IntradayDailyCount[], Error>({
    queryKey: [INTRADAY_DAILY_COUNTS_QUERY_KEY],
    queryFn: () => fetchIntradayDailyCounts(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}
