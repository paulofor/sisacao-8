import { useQuery } from '@tanstack/react-query'

import { fetchOpsOverview, type OpsOverview } from '../api/ops'

export const OPS_OVERVIEW_QUERY_KEY = ['ops', 'overview'] as const

export const useOpsOverview = () => {
  return useQuery<OpsOverview | null, Error>({
    queryKey: OPS_OVERVIEW_QUERY_KEY,
    queryFn: fetchOpsOverview,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
