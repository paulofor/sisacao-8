import { useQuery } from '@tanstack/react-query'

import { fetchIntradaySummary, type IntradaySummary } from '../api/dataCollections'

export const INTRADAY_SUMMARY_QUERY_KEY = 'intraday-summary'

export const useIntradaySummary = () => {
  return useQuery<IntradaySummary, Error>({
    queryKey: [INTRADAY_SUMMARY_QUERY_KEY],
    queryFn: () => fetchIntradaySummary(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}
