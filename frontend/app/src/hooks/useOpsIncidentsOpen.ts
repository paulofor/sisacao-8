import { useQuery } from '@tanstack/react-query'

import { fetchOpsIncidentsOpen, type OpsIncident } from '../api/ops'

export const OPS_INCIDENTS_OPEN_QUERY_KEY = ['ops', 'incidents', 'open'] as const

export const useOpsIncidentsOpen = () => {
  return useQuery<OpsIncident[], Error>({
    queryKey: OPS_INCIDENTS_OPEN_QUERY_KEY,
    queryFn: fetchOpsIncidentsOpen,
    staleTime: 120_000,
    refetchInterval: 120_000,
    refetchOnWindowFocus: true,
  })
}
