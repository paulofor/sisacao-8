import { useQuery } from '@tanstack/react-query'

import { fetchOpsBacktestTrades } from '../api/ops'

export const useOpsBacktestTrades = (limit = 50) => {
  return useQuery({
    queryKey: ['ops', 'backtest', 'trades', limit],
    queryFn: () => fetchOpsBacktestTrades(limit),
    refetchInterval: 120000,
  })
}
