import { useQuery } from '@tanstack/react-query'

import { fetchOpsSignalsNext, type OpsSignalNext } from '../api/ops'

export const OPS_SIGNALS_NEXT_QUERY_KEY = ['ops', 'signals', 'next'] as const

export const useOpsSignalsNext = () => {
  return useQuery<OpsSignalNext[], Error>({
    queryKey: OPS_SIGNALS_NEXT_QUERY_KEY,
    queryFn: fetchOpsSignalsNext,
    staleTime: 300_000,
    refetchInterval: 300_000,
    refetchOnWindowFocus: true,
  })
}
