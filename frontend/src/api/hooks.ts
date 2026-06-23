import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { prospectsApi, scrapingApi, searchesApi } from './endpoints'
import type { BulkScrapingStartRequest, SearchCreate, WebsiteReason } from '../types'

export const queryKeys = {
  searches: ['searches'] as const,
  prospects: (filters: Record<string, unknown>) => ['prospects', filters] as const,
  prospectStats: ['prospect-stats'] as const,
  scrapingStatus: (jobId: string) => ['scraping-status', jobId] as const,
  bulkScrapingStatus: (jobId: string) => ['bulk-scraping-status', jobId] as const,
  bulkScrapingActive: ['bulk-scraping-active'] as const,
}

export function useSearches() {
  return useQuery({
    queryKey: queryKeys.searches,
    queryFn: () => searchesApi.list(),
  })
}

export function useCreateSearch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: SearchCreate) => searchesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.searches })
    },
  })
}

export function useStartScraping() {
  return useMutation({
    mutationFn: (searchId: number) => scrapingApi.start(searchId),
  })
}

export function useScrapingStatus(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.scrapingStatus(jobId ?? ''),
    queryFn: () => scrapingApi.status(jobId!),
    enabled: enabled && Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' ? 2000 : false
    },
  })
}

export function useStartBulkScraping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: BulkScrapingStartRequest) => scrapingApi.bulkStart(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.bulkScrapingStatus(data.job_id), data)
      queryClient.setQueryData(queryKeys.bulkScrapingActive, data)
      void queryClient.invalidateQueries({ queryKey: queryKeys.bulkScrapingActive })
    },
  })
}

export function useBulkScrapingStatus(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.bulkScrapingStatus(jobId ?? ''),
    queryFn: () => scrapingApi.bulkStatus(jobId!),
    enabled: enabled && Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'paused' ? 5000 : false
    },
  })
}

export function useActiveBulkScraping() {
  return useQuery({
    queryKey: queryKeys.bulkScrapingActive,
    queryFn: () => scrapingApi.bulkActive(),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'paused' ? 5000 : false
    },
  })
}

export function usePauseBulkScraping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => scrapingApi.bulkPause(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.bulkScrapingStatus(data.job_id), data)
    },
  })
}

export function useResumeBulkScraping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => scrapingApi.bulkResume(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.bulkScrapingStatus(data.job_id), data)
      queryClient.setQueryData(queryKeys.bulkScrapingActive, data)
      void queryClient.invalidateQueries({ queryKey: queryKeys.bulkScrapingActive })
    },
  })
}

export function useStopBulkScraping() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => scrapingApi.bulkStop(jobId),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.bulkScrapingStatus(data.job_id), data)
      if (data.status === 'stopped') {
        queryClient.setQueryData(queryKeys.bulkScrapingActive, null)
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.bulkScrapingActive })
      void queryClient.invalidateQueries({ queryKey: queryKeys.prospectStats })
      void queryClient.invalidateQueries({ queryKey: ['prospects'] })
    },
  })
}

export function useProspects(filters: {
  city?: string
  category?: string
  has_website?: boolean
  website_reason?: WebsiteReason
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: queryKeys.prospects(filters),
    queryFn: () => prospectsApi.list(filters),
  })
}

export function useProspectStats() {
  return useQuery({
    queryKey: queryKeys.prospectStats,
    queryFn: () => prospectsApi.stats(),
  })
}
