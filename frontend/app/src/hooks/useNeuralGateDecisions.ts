import { useQuery } from '@tanstack/react-query'

import { fetchNeuralGateDecisions, type NeuralGateDecisionAttempt } from '../api/ops'

export const NEURAL_GATE_DECISIONS_QUERY_KEY = [
  'ops',
  'neural',
  'gate-decisions',
] as const

export const useNeuralGateDecisions = () => {
  return useQuery<NeuralGateDecisionAttempt[], Error>({
    queryKey: NEURAL_GATE_DECISIONS_QUERY_KEY,
    queryFn: fetchNeuralGateDecisions,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
