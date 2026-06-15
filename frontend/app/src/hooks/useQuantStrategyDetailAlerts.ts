import { useQuery } from '@tanstack/react-query'

import { fetchQuantStrategyDetailAlerts, type QuantStrategyDetailAlert } from '../api/ops'

export const useQuantStrategyDetailAlerts = () => {
  return useQuery<QuantStrategyDetailAlert[], Error>({
    queryKey: ['ops', 'quant', 'strategies', 'alerts'],
    queryFn: fetchQuantStrategyDetailAlerts,
    refetchInterval: 120_000,
    refetchOnWindowFocus: true,
  })
}
