import { useQuery } from '@tanstack/react-query'

import { fetchQuantCommittee } from '../api/ops'

export const useQuantCommittee = (limit = 100) => useQuery({
  queryKey: ['quant-committee', limit],
  queryFn: () => fetchQuantCommittee(limit),
})
