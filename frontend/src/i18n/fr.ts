import type { SearchStatus, WebsiteReason } from '../types'

export const searchStatusLabels: Record<SearchStatus, string> = {
  pending: 'En attente',
  running: 'En cours',
  paused: 'En pause',
  stopped: 'Arrêté',
  completed: 'Terminé',
  failed: 'Échec',
}

export const websiteReasonLabels: Record<WebsiteReason, string> = {
  no_url: 'Pas de site web',
  dns_failure: 'Échec DNS',
  http_failure: 'En construction',
  social_only: 'Réseaux sociaux uniquement',
  under_construction: 'En construction',
  valid: 'Site valide',
}
