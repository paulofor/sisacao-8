import { useQuery } from '@tanstack/react-query'

import {
  type DataCollectionMessage,
  type DataCollectionMessagesFilters,
  fetchDataCollectionMessages,
} from '../api/dataCollections'

export const DATA_COLLECTION_MESSAGES_QUERY_KEY = 'data-collection-messages'

export const useDataCollectionMessages = (filters: DataCollectionMessagesFilters = {}) => {
  return useQuery<DataCollectionMessage[], Error>({
    queryKey: [DATA_COLLECTION_MESSAGES_QUERY_KEY, filters],
    queryFn: () => fetchDataCollectionMessages(filters),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
}

