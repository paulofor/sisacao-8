import { useQuery } from '@tanstack/react-query'

import { fetchQuantRankingDaily } from '../api/ops'

export const useQuantRankingDaily = (limit = 150) => {
  return useQuery({
    queryKey: ['quant-ranking-daily', limit],
    queryFn: () => fetchQuantRankingDaily(limit),
    staleTime: 60_000,
  })
}
