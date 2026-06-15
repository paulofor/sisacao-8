import { useQuery } from '@tanstack/react-query'

import { fetchQuantStrategyRegimePerformance } from '../api/ops'

export const useQuantStrategyRegimePerformance = () => useQuery({
  queryKey: ['quant-strategy-regime-performance'],
  queryFn: fetchQuantStrategyRegimePerformance,
})
