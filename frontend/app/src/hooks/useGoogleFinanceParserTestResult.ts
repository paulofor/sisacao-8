import { useQuery } from '@tanstack/react-query'

import { fetchGoogleFinanceParserTestResult, type GoogleFinanceParserTestResult } from '../api/testResults'

export const GOOGLE_FINANCE_TEST_RESULT_QUERY_KEY = 'google-finance-parser-test-result'

export const useGoogleFinanceParserTestResult = () => {
  return useQuery<GoogleFinanceParserTestResult, Error>({
    queryKey: [GOOGLE_FINANCE_TEST_RESULT_QUERY_KEY],
    queryFn: fetchGoogleFinanceParserTestResult,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  })
}

