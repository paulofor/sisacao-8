export type TestStatus = 'passed' | 'failed' | 'unknown'

export interface GoogleFinanceParserTestResult {
  testName: string
  description: string
  status: TestStatus
  details: {
    ticker: string
    exchange: string
    priceText: string
    parsedPrice: number
    htmlFixture: string
  }
}

const TEST_RESULT_URL = '/test-results/google-finance-parser.json'

export const fetchGoogleFinanceParserTestResult = async (): Promise<GoogleFinanceParserTestResult> => {
  const response = await fetch(TEST_RESULT_URL, {
    headers: {
      'Cache-Control': 'no-cache',
    },
  })

  if (!response.ok) {
    throw new Error('Não foi possível carregar o resultado do teste do parser do Google Finance')
  }

  const data = (await response.json()) as GoogleFinanceParserTestResult

  return data
}

