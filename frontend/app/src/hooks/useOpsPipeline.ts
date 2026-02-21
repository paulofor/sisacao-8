import { useQuery } from '@tanstack/react-query'

import { fetchOpsPipeline, type OpsPipelineJob } from '../api/ops'

export const OPS_PIPELINE_QUERY_KEY = ['ops', 'pipeline'] as const

export const useOpsPipeline = () => {
  return useQuery<OpsPipelineJob[], Error>({
    queryKey: OPS_PIPELINE_QUERY_KEY,
    queryFn: fetchOpsPipeline,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
