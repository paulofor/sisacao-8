import { useQuery } from '@tanstack/react-query'

import { fetchQuantRobustness } from '../api/ops'

export const useQuantRobustness = () => useQuery({
  queryKey: ['quant-robustness'],
  queryFn: fetchQuantRobustness,
})
