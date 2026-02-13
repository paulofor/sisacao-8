import { useQuery } from '@tanstack/react-query'

import { fetchIntradayLatestRecords, type IntradayLatestRecord } from '../api/dataCollections'

export const INTRADAY_LATEST_RECORDS_QUERY_KEY = 'intraday-latest-records'

export const useIntradayLatestRecords = () => {
  return useQuery<IntradayLatestRecord[], Error>({
    queryKey: [INTRADAY_LATEST_RECORDS_QUERY_KEY],
    queryFn: () => fetchIntradayLatestRecords(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}
