import { useQuery } from '@tanstack/react-query'

import { fetchQuantDataInventorySummary, type QuantDataInventorySummary } from '../api/ops'

export const QUANT_INVENTORY_SUMMARY_QUERY_KEY = ['ops', 'quant', 'inventory-summary'] as const

export const useQuantDataInventorySummary = () => {
  return useQuery<QuantDataInventorySummary | null, Error>({
    queryKey: QUANT_INVENTORY_SUMMARY_QUERY_KEY,
    queryFn: fetchQuantDataInventorySummary,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
