import { useQuery } from '@tanstack/react-query'

import { fetchOpsDqLatest, type OpsDqCheck } from '../api/ops'

export const OPS_DQ_LATEST_QUERY_KEY = ['ops', 'dq', 'latest'] as const

export const useOpsDqLatest = () => {
  return useQuery<OpsDqCheck[], Error>({
    queryKey: OPS_DQ_LATEST_QUERY_KEY,
    queryFn: fetchOpsDqLatest,
    staleTime: 120_000,
    refetchInterval: 120_000,
    refetchOnWindowFocus: true,
  })
}
