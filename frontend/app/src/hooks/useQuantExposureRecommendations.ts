import { useQuery } from '@tanstack/react-query'

import { fetchQuantExposureRecommendations } from '../api/ops'

export const useQuantExposureRecommendations = (limit = 90) => useQuery({
  queryKey: ['quant-exposure-recommendations', limit],
  queryFn: () => fetchQuantExposureRecommendations(limit),
})
