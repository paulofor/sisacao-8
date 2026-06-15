import { useQuery } from '@tanstack/react-query'

import { fetchQuantMarketRegime } from '../api/ops'

export const useQuantMarketRegime = (limit = 90) => useQuery({
  queryKey: ['quant-market-regime', limit],
  queryFn: () => fetchQuantMarketRegime(limit),
})
