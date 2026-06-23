import { useState } from 'react'
import { Badge } from '../components/Badge'
import { Select } from '../components/Select'
import { Input } from '../components/Input'
import { Spinner } from '../components/Spinner'
import { Button } from '../components/Button'
import { useProspects } from '../api/hooks'
import type { Prospect, WebsiteReason } from '../types'
import { websiteReasonLabels } from '../i18n/fr'
import { ui } from '../theme/ui'

function formatRating(rating: number | null): string {
  if (rating === null) return '—'
  return `${rating.toLocaleString('fr-FR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })} / 5`
}

function formatPhone(phone: string): string {
  const compact = phone.replace(/\s/g, '')
  if (compact.startsWith('+33') && compact.length === 12) {
    const national = `0${compact.slice(3)}`
    return national.replace(/(\d{2})(?=\d)/g, '$1 ').trim()
  }
  return phone
}

function formatLocation(prospect: Prospect): string {
  const parts = [prospect.city, prospect.country].filter(Boolean)
  return parts.length > 0 ? parts.join(', ') : '—'
}

function ProspectCard({ prospect }: { prospect: Prospect }) {
  if (prospect.has_website) {
    return (
      <article className={`space-y-4 p-5 ${ui.card}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <h3 className="text-lg font-semibold text-slate-900 break-words dark:text-white">
              {prospect.business_name}
            </h3>
            <p className={ui.cardMuted}>À vérifier manuellement</p>
          </div>
          <Badge variant="success">Avec site web</Badge>
        </div>

        <dl className="text-sm">
          <div>
            <dt className="text-slate-500">Site web</dt>
            <dd className="mt-0.5 break-all text-slate-800 dark:text-slate-200">
              {prospect.website ? (
                <a href={prospect.website} target="_blank" rel="noreferrer" className={ui.link}>
                  {prospect.website}
                </a>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>

        <p className="text-xs text-slate-500">
          Scrapé le {new Date(prospect.created_at).toLocaleString('fr-FR')}
        </p>
      </article>
    )
  }

  return (
    <article className={`space-y-4 p-5 ${ui.card}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <h3 className="text-lg font-semibold text-slate-900 break-words dark:text-white">
            {prospect.business_name}
          </h3>
          <p className={ui.cardMuted}>{prospect.category ?? '—'}</p>
        </div>
        <Badge variant={prospect.has_website ? 'success' : 'danger'}>
          {prospect.has_website ? 'Avec site web' : websiteReasonLabels[prospect.website_reason]}
        </Badge>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Adresse</dt>
          <dd className="mt-0.5 text-slate-800 break-words dark:text-slate-200">{prospect.address ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Ville / Pays</dt>
          <dd className="mt-0.5 text-slate-800 dark:text-slate-200">{formatLocation(prospect)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Téléphone</dt>
          <dd className="mt-0.5 text-slate-800 dark:text-slate-200">
            {prospect.phone ? (
              <a href={`tel:${prospect.phone.replace(/\s/g, '')}`} className={ui.link}>
                {formatPhone(prospect.phone)}
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Note Google</dt>
          <dd className="mt-0.5 text-slate-800 dark:text-slate-200">{formatRating(prospect.rating)}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Site web</dt>
          <dd className="mt-0.5 break-all text-slate-800 dark:text-slate-200">
            {prospect.website ? (
              <a href={prospect.website} target="_blank" rel="noreferrer" className={ui.link}>
                {prospect.website}
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Fiche Google Maps</dt>
          <dd className="mt-0.5 break-all">
            {prospect.maps_url ? (
              <a href={prospect.maps_url} target="_blank" rel="noreferrer" className={ui.link}>
                Ouvrir sur Google Maps
              </a>
            ) : (
              <span className="text-slate-800 dark:text-slate-200">—</span>
            )}
          </dd>
        </div>
        {!prospect.has_website && prospect.testimonials.length > 0 && (
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Témoignages clients</dt>
            <dd className="mt-2 space-y-3">
              {prospect.testimonials.map((testimonial, index) => (
                <blockquote
                  key={`${prospect.id}-testimonial-${index}`}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-slate-800 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-200"
                >
                  <p className="text-sm leading-relaxed">&ldquo;{testimonial.text}&rdquo;</p>
                  <footer className="mt-2 text-xs text-slate-500">
                    {testimonial.author ?? 'Client anonyme'}
                    {testimonial.rating !== null ? ` · ${testimonial.rating} ★` : ''}
                    {testimonial.date ? ` · ${testimonial.date}` : ''}
                  </footer>
                </blockquote>
              ))}
            </dd>
          </div>
        )}
      </dl>

      <p className="text-xs text-slate-500">
        Scrapé le {new Date(prospect.created_at).toLocaleString('fr-FR')}
      </p>
    </article>
  )
}

export function ProspectsPage() {
  const [city, setCity] = useState('')
  const [category, setCategory] = useState('')
  const [websiteStatus, setWebsiteStatus] = useState('')
  const [websiteReason, setWebsiteReason] = useState('')
  const [page, setPage] = useState(1)

  const hasWebsite =
    websiteStatus === 'with' ? true : websiteStatus === 'without' ? false : undefined

  const reasonFilter = websiteReason ? (websiteReason as WebsiteReason) : undefined

  const hasActiveFilters = Boolean(
    city.trim() || category.trim() || websiteReason || websiteStatus,
  )

  const { data, isLoading, isError } = useProspects({
    city: city.trim() || undefined,
    category: category.trim() || undefined,
    has_website: hasWebsite,
    website_reason: reasonFilter,
    page,
    page_size: 12,
  })

  function clearFilters() {
    setCity('')
    setCategory('')
    setWebsiteStatus('')
    setWebsiteReason('')
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className={ui.pageTitle}>Prospects</h2>
        <p className={ui.pageSubtitle}>
          Prospects sans site web — fiches GMB complètes pour la prospection. Les entreprises avec
          site web sont conservées avec leur nom et URL pour vérification manuelle.
        </p>
      </div>

      <div className={`space-y-4 p-4 ${ui.card}`}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Ville"
            value={city}
            onChange={(e) => {
              setCity(e.target.value)
              setPage(1)
            }}
            placeholder="Filtrer par ville"
          />
          <Input
            label="Catégorie"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setPage(1)
            }}
            placeholder="Filtrer par catégorie"
          />
          <Select
            label="Statut site web"
            value={websiteStatus}
            onChange={(e) => {
              setWebsiteStatus(e.target.value)
              setPage(1)
            }}
            options={[
              { label: 'Tous', value: '' },
              { label: 'Avec site web', value: 'with' },
              { label: 'Sans site web', value: 'without' },
            ]}
          />
          <Select
            label="Raison"
            value={websiteReason}
            onChange={(e) => {
              setWebsiteReason(e.target.value)
              setPage(1)
            }}
            options={[
              { label: 'Toutes', value: '' },
              { label: websiteReasonLabels.no_url, value: 'no_url' },
              { label: websiteReasonLabels.social_only, value: 'social_only' },
              { label: websiteReasonLabels.under_construction, value: 'under_construction' },
            ]}
          />
        </div>
        {hasActiveFilters && (
          <div className="flex justify-end">
            <Button variant="secondary" onClick={clearFilters}>
              Effacer les filtres
            </Button>
          </div>
        )}
      </div>

      {isLoading && <Spinner />}
      {isError && <p className={ui.error}>Impossible de charger les prospects.</p>}

      {data && (
        <>
          {data.items.length === 0 ? (
            <p className={`px-4 py-8 text-center ${ui.card} ${ui.cardMuted}`}>
              Aucun prospect trouvé.
            </p>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {data.items.map((prospect) => (
                <ProspectCard key={prospect.id} prospect={prospect} />
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className={ui.cardMuted}>
              Page {data.page} sur {data.total_pages} ({data.total} au total)
            </p>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Précédent
              </Button>
              <Button
                variant="secondary"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
