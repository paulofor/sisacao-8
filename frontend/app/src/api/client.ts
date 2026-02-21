import axios, { type AxiosRequestConfig } from 'axios'

const DEFAULT_BASE_URL = ''

const configuredBaseURL = import.meta.env.VITE_API_BASE_URL as string | undefined

const baseURLCandidates = Array.from(
  new Set(
    configuredBaseURL && configuredBaseURL.length > 0
      ? [configuredBaseURL, DEFAULT_BASE_URL]
      : [DEFAULT_BASE_URL],
  ),
)

type RetryableAxiosRequestConfig = AxiosRequestConfig & {
  __baseUrlCandidateIndex?: number
}

export const apiClient = axios.create({
  baseURL: baseURLCandidates[0],
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const requestConfig = error.config as RetryableAxiosRequestConfig | undefined
    const currentBaseUrlCandidateIndex = requestConfig?.__baseUrlCandidateIndex ?? 0
    const nextBaseUrlCandidateIndex = currentBaseUrlCandidateIndex + 1

    const responseStatus = error.response?.status as number | undefined
    const canRetryOnStatus =
      responseStatus === 404 ||
      responseStatus === 502 ||
      responseStatus === 503 ||
      responseStatus === 504

    if (!requestConfig || nextBaseUrlCandidateIndex >= baseURLCandidates.length || !canRetryOnStatus) {
      return Promise.reject(error)
    }

    requestConfig.baseURL = baseURLCandidates[nextBaseUrlCandidateIndex]
    requestConfig.__baseUrlCandidateIndex = nextBaseUrlCandidateIndex

    return apiClient.request(requestConfig)
  },
)
