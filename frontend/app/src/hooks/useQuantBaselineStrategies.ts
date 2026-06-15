import { useQuery } from '@tanstack/react-query'

import { fetchQuantBaselineStrategies, type QuantBaselineStrategy } from '../api/ops'

export const useQuantBaselineStrategies = () => {
  return useQuery<QuantBaselineStrategy[], Error>({
    queryKey: ['ops', 'quant', 'strategies'],
    queryFn: fetchQuantBaselineStrategies,
    refetchInterval: 120_000,
    refetchOnWindowFocus: true,
  })
}
