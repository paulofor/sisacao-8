import { useQuery } from '@tanstack/react-query'

import { fetchNeuralTrainingRuns, type NeuralTrainingRun } from '../api/ops'

export const NEURAL_TRAINING_RUNS_QUERY_KEY = [
  'ops',
  'neural',
  'training-runs',
] as const

export const useNeuralTrainingRuns = () => {
  return useQuery<NeuralTrainingRun[], Error>({
    queryKey: NEURAL_TRAINING_RUNS_QUERY_KEY,
    queryFn: fetchNeuralTrainingRuns,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
