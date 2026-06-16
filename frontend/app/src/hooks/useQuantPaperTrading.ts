import { useQuery } from '@tanstack/react-query'

import { fetchQuantPaperTrading } from '../api/ops'

export const useQuantPaperTrading = (limit = 100) => useQuery({
  queryKey: ['quant-paper-trading', limit],
  queryFn: () => fetchQuantPaperTrading(limit),
})
