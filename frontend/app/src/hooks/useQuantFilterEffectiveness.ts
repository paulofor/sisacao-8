import { useQuery } from '@tanstack/react-query'

import { fetchQuantFilterEffectiveness } from '../api/ops'

export const useQuantFilterEffectiveness = () => useQuery({
  queryKey: ['quant-filter-effectiveness'],
  queryFn: fetchQuantFilterEffectiveness,
})
