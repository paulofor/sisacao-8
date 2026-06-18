import { useQuery } from '@tanstack/react-query'

import {
  fetchNeuralTrainingDataAllocation,
  type NeuralTrainingDataAllocation,
} from '../api/ops'

export const NEURAL_TRAINING_DATA_ALLOCATION_QUERY_KEY = [
  'ops',
  'neural',
  'training-data-allocation',
] as const

export const useNeuralTrainingDataAllocation = () => {
  return useQuery<NeuralTrainingDataAllocation[], Error>({
    queryKey: NEURAL_TRAINING_DATA_ALLOCATION_QUERY_KEY,
    queryFn: fetchNeuralTrainingDataAllocation,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
