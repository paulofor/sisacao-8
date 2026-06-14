import { useQuery } from '@tanstack/react-query'

import { fetchQuantDataQualityIncidents, type QuantDataQualityIncident } from '../api/ops'

export const QUANT_DQ_INCIDENTS_QUERY_KEY = ['ops', 'quant', 'data-quality-incidents'] as const

export const useQuantDataQualityIncidents = (limit = 100) => {
  return useQuery<QuantDataQualityIncident[], Error>({
    queryKey: [...QUANT_DQ_INCIDENTS_QUERY_KEY, limit],
    queryFn: () => fetchQuantDataQualityIncidents(limit),
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
