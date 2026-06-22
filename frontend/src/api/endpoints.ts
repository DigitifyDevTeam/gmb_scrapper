import { apiClient } from './client'
import type {
  BulkScrapingStartRequest,
  BulkScrapingStartResponse,
  BulkScrapingStatusResponse,
  PaginatedResponse,
  Prospect,
  ProspectStats,
  ScrapingStartResponse,
  ScrapingStatusResponse,
  Search,
  SearchCreate,
  WebsiteReason,
} from '../types'

function cleanParams<T extends Record<string, unknown>>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as Partial<T>
}

export const searchesApi = {
  create: async (payload: SearchCreate): Promise<Search> => {
    const { data } = await apiClient.post<Search>('/searches', payload)
    return data
  },
  list: async (): Promise<{ items: Search[]; total: number }> => {
    const { data } = await apiClient.get<{ items: Search[]; total: number }>('/searches')
    return data
  },
  get: async (id: number): Promise<Search> => {
    const { data } = await apiClient.get<Search>(`/searches/${id}`)
    return data
  },
}

export const scrapingApi = {
  start: async (searchId: number): Promise<ScrapingStartResponse> => {
    const { data } = await apiClient.post<ScrapingStartResponse>('/scraping/start', {
      search_id: searchId,
    })
    return data
  },
  status: async (jobId: string): Promise<ScrapingStatusResponse> => {
    const { data } = await apiClient.get<ScrapingStatusResponse>(`/scraping/status/${jobId}`)
    return data
  },
  bulkStart: async (payload: BulkScrapingStartRequest): Promise<BulkScrapingStartResponse> => {
    const { data } = await apiClient.post<BulkScrapingStartResponse>('/scraping/bulk/start', payload)
    return data
  },
  bulkStatus: async (jobId: string): Promise<BulkScrapingStatusResponse> => {
    const { data } = await apiClient.get<BulkScrapingStatusResponse>(`/scraping/bulk/status/${jobId}`)
    return data
  },
  bulkActive: async (): Promise<BulkScrapingStatusResponse | null> => {
    const { data } = await apiClient.get<BulkScrapingStatusResponse | null>('/scraping/bulk/active')
    return data
  },
  bulkPause: async (jobId: string): Promise<BulkScrapingStatusResponse> => {
    const { data } = await apiClient.post<BulkScrapingStatusResponse>(`/scraping/bulk/pause/${jobId}`)
    return data
  },
  bulkResume: async (jobId: string): Promise<BulkScrapingStatusResponse> => {
    const { data } = await apiClient.post<BulkScrapingStatusResponse>(`/scraping/bulk/resume/${jobId}`)
    return data
  },
  bulkStop: async (jobId: string): Promise<BulkScrapingStatusResponse> => {
    const { data } = await apiClient.post<BulkScrapingStatusResponse>(`/scraping/bulk/stop/${jobId}`)
    return data
  },
}

export const prospectsApi = {
  list: async (params: {
    city?: string
    category?: string
    has_website?: boolean
    website_reason?: WebsiteReason
    page?: number
    page_size?: number
  }): Promise<PaginatedResponse<Prospect>> => {
    const { data } = await apiClient.get<PaginatedResponse<Prospect>>('/prospects', {
      params: cleanParams(params),
    })
    return data
  },
  get: async (id: number): Promise<Prospect> => {
    const { data } = await apiClient.get<Prospect>(`/prospects/${id}`)
    return data
  },
  stats: async (): Promise<ProspectStats> => {
    const { data } = await apiClient.get<ProspectStats>('/prospects/stats')
    return data
  },
}
