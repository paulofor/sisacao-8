import { useQuery } from '@tanstack/react-query'

import { fetchNeuralChampionMonitoring } from '../api/ops'

export const useNeuralChampionMonitoring = () => {
  return useQuery({
    queryKey: ['ops', 'neural', 'champion-monitoring'],
    queryFn: fetchNeuralChampionMonitoring,
    refetchInterval: 5 * 60 * 1000,
  })
}
