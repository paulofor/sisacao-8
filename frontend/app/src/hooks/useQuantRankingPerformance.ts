import { useQuery } from '@tanstack/react-query'

import { fetchQuantRankingPerformance } from '../api/ops'

export const useQuantRankingPerformance = () => {
  return useQuery({
    queryKey: ['quant-ranking-performance'],
    queryFn: fetchQuantRankingPerformance,
    staleTime: 60_000,
  })
}
