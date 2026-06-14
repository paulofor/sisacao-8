import { useQuery } from '@tanstack/react-query'

import { fetchQuantTickerCoverage, type QuantTickerCoverage } from '../api/ops'

export const QUANT_TICKER_COVERAGE_QUERY_KEY = ['ops', 'quant', 'ticker-coverage'] as const

export const useQuantTickerCoverage = (limit = 100) => {
  return useQuery<QuantTickerCoverage[], Error>({
    queryKey: [...QUANT_TICKER_COVERAGE_QUERY_KEY, limit],
    queryFn: () => fetchQuantTickerCoverage(limit),
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
