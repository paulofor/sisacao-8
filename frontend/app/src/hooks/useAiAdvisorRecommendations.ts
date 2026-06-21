import { useMutation } from '@tanstack/react-query'

import {
  requestAiAdvisorRecommendations,
  type AiAdvisorRequest,
  type AiAdvisorResponse,
} from '../api/ops'

export const useAiAdvisorRecommendations = () => {
  return useMutation<AiAdvisorResponse, Error, AiAdvisorRequest>({
    mutationFn: requestAiAdvisorRecommendations,
  })
}
