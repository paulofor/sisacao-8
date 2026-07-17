import { useQuery } from '@tanstack/react-query'

import { fetchNeuralEvolutionActivity, type NeuralEvolutionActivity } from '../api/ops'

export const NEURAL_EVOLUTION_ACTIVITY_QUERY_KEY = ['ops', 'neural', 'evolution', 'activity'] as const

export const useNeuralEvolutionActivity = () => useQuery<NeuralEvolutionActivity[], Error>({
  queryKey: NEURAL_EVOLUTION_ACTIVITY_QUERY_KEY,
  queryFn: fetchNeuralEvolutionActivity,
  staleTime: 60_000,
  refetchInterval: 60_000,
  refetchOnWindowFocus: true,
})
