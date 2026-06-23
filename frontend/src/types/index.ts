export type SearchStatus = 'pending' | 'running' | 'paused' | 'stopped' | 'completed' | 'failed'

export type WebsiteReason =
  | 'no_url'
  | 'dns_failure'
  | 'http_failure'
  | 'social_only'
  | 'under_construction'
  | 'valid'

export interface Testimonial {
  author: string | null
  rating: number | null
  text: string
  date: string | null
}

export interface Search {
  id: number
  country: string
  city: string
  category: string
  status: SearchStatus
  created_at: string
}

export interface SearchCreate {
  country: string
  city: string
  category: string
}

export interface Prospect {
  id: number
  search_id: number
  business_name: string
  category: string | null
  address: string | null
  phone: string | null
  website: string | null
  rating: number | null
  review_count: number | null
  maps_url: string | null
  has_website: boolean
  website_reason: WebsiteReason
  testimonials: Testimonial[]
  created_at: string
  city: string | null
  country: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ProspectStats {
  total: number
  with_website: number
  without_website: number
}

export interface ScrapingStartResponse {
  job_id: string
  search_id: number
  status: SearchStatus
}

export interface ScrapingStatusResponse {
  job_id: string
  search_id: number
  status: SearchStatus
  prospects_found: number
  prospects_saved: number
  error: string | null
}

export interface BulkScrapingStartRequest {
  country?: string
  target_count?: number
  cities?: string[]
  categories?: string[]
  max_queries?: number
}

export interface BulkScrapingStartResponse {
  job_id: string
  country: string
  target_count: number
  total_queries: number
  status: SearchStatus
}

export interface BulkScrapingStatusResponse {
  job_id: string
  country: string
  target_count: number
  total_queries: number
  completed_queries: number
  prospects_found: number
  prospects_saved: number
  prospects_saved_with_website: number
  prospects_saved_total: number
  prospects_skipped_duplicates: number
  current_city: string | null
  current_category: string | null
  status: SearchStatus
  error: string | null
}
