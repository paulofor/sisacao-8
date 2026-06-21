import { useQuery } from '@tanstack/react-query'

import { fetchNeuralEvolutionLeaderboard, type NeuralEvolutionLeaderboardEntry } from '../api/ops'

export const NEURAL_EVOLUTION_LEADERBOARD_QUERY_KEY = [
  'ops',
  'neural',
  'evolution',
  'leaderboard',
] as const

export const useNeuralEvolutionLeaderboard = () => {
  return useQuery<NeuralEvolutionLeaderboardEntry[], Error>({
    queryKey: NEURAL_EVOLUTION_LEADERBOARD_QUERY_KEY,
    queryFn: fetchNeuralEvolutionLeaderboard,
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}
