import { Link } from 'react-router-dom'
import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '../components/Button'
import { Input } from '../components/Input'
import { Badge } from '../components/Badge'
import {
  useActiveBulkScraping,
  useBulkScrapingStatus,
  usePauseBulkScraping,
  useResumeBulkScraping,
  useStartBulkScraping,
  useStopBulkScraping,
} from '../api/hooks'
import type { SearchStatus } from '../types'
import { searchStatusLabels } from '../i18n/fr'
import { ui } from '../theme/ui'

function bulkStatusVariant(status: SearchStatus): 'success' | 'danger' | 'neutral' {
  switch (status) {
    case 'completed':
    case 'stopped':
      return 'success'
    case 'failed':
      return 'danger'
    case 'pending':
    case 'running':
    case 'paused':
      return 'neutral'
    default: {
      const _exhaustive: never = status
      return _exhaustive
    }
  }
}

const BULK_JOB_STORAGE_KEY = 'gmb-bulk-job-id'

export function BulkPage() {
  const [country, setCountry] = useState('France')
  const [targetCount, setTargetCount] = useState('10000')
  const [jobId, setJobId] = useState<string | null>(() => localStorage.getItem(BULK_JOB_STORAGE_KEY))

  const startBulk = useStartBulkScraping()
  const pauseBulk = usePauseBulkScraping()
  const resumeBulk = useResumeBulkScraping()
  const stopBulk = useStopBulkScraping()
  const { data: activeJob } = useActiveBulkScraping()
  const { data: trackedStatus } = useBulkScrapingStatus(jobId, Boolean(jobId))
  const status = trackedStatus ?? activeJob ?? null

  useEffect(() => {
    if (activeJob?.job_id && !jobId) {
      setJobId(activeJob.job_id)
    }
  }, [activeJob, jobId])

  useEffect(() => {
    if (jobId) {
      localStorage.setItem(BULK_JOB_STORAGE_KEY, jobId)
      return
    }
    localStorage.removeItem(BULK_JOB_STORAGE_KEY)
  }, [jobId])

  const isActive = status?.status === 'running' || status?.status === 'paused'
  const isPaused = status?.status === 'paused'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const result = await startBulk.mutateAsync({
      country,
      target_count: Number(targetCount),
    })
    setJobId(result.job_id)
  }

  const progressPercent =
    status && status.total_queries > 0
      ? Math.round((status.completed_queries / status.total_queries) * 100)
      : 0

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h2 className={ui.pageTitle}>Scraping en masse — France</h2>
        <p className={ui.pageSubtitle}>
          Collectez des milliers d&apos;entreprises dans les villes et catégories françaises via Playwright.
          Google Maps limite à ~120 résultats par requête ; l&apos;outil enchaîne des combinaisons ville + catégorie
          jusqu&apos;à atteindre l&apos;objectif.
        </p>
        <p className={`mt-3 ${ui.cardMuted}`}>
          Les prospects sans site web sont enregistrés avec toutes les infos GMB sur la page{' '}
          <Link to="/prospects" className={ui.link}>
            Prospects
          </Link>
          . Les entreprises avec site web ne sont gardées que par nom pour éviter les doublons.
        </p>
      </div>

      <form onSubmit={handleSubmit} className={`space-y-4 p-6 ${ui.card}`}>
        <Input label="Pays" value={country} onChange={(e) => setCountry(e.target.value)} required />
        <Input
          label="Objectif (prospects sans site)"
          type="number"
          min={100}
          max={100000}
          value={targetCount}
          onChange={(e) => setTargetCount(e.target.value)}
          required
        />
        <p className={ui.cardMuted}>
          Plan par défaut : 45 villes × 12 catégories = 540 recherches Playwright. Arrêt automatique à
          l&apos;objectif. Les entreprises déjà scrapées sont ignorées à chaque exécution.
        </p>
        <Button type="submit" loading={startBulk.isPending} disabled={isActive} className="w-full">
          Démarrer le scraping en masse
        </Button>
      </form>

      {status && (
        <div className={`space-y-4 p-6 ${ui.card}`}>
          <div className="flex items-center gap-3">
            <h3 className={ui.heading}>Progression</h3>
            <Badge variant={bulkStatusVariant(status.status)}>{searchStatusLabels[status.status]}</Badge>
          </div>

          <div className={ui.progressTrack}>
            <div
              className="h-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className={`grid gap-2 text-sm sm:grid-cols-2 ${ui.body}`}>
            <p>Tâche : {status.job_id}</p>
            <p>Requêtes : {status.completed_queries} / {status.total_queries}</p>
            <p>Enregistrés : {status.prospects_saved} / {status.target_count}</p>
            <p>Trouvés (brut) : {status.prospects_found}</p>
            <p>Doublons ignorés : {status.prospects_skipped_duplicates}</p>
            {status.current_city && (
              <p>
                En cours : {status.current_category} à {status.current_city}
              </p>
            )}
          </div>

          {isActive && (
            <div className="flex flex-wrap gap-3 pt-2">
              {isPaused ? (
                <Button
                  variant="primary"
                  loading={resumeBulk.isPending}
                  onClick={() => resumeBulk.mutate(status.job_id)}
                >
                  Reprendre
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  loading={pauseBulk.isPending}
                  onClick={() => pauseBulk.mutate(status.job_id)}
                >
                  Pause
                </Button>
              )}
              <Button
                variant="danger"
                loading={stopBulk.isPending}
                onClick={() => stopBulk.mutate(status.job_id)}
              >
                Arrêter et enregistrer
              </Button>
            </div>
          )}

          {status.status === 'stopped' && (
            <p className={ui.success}>
              Scraping arrêté. Toutes les données collectées sont enregistrées en base.
            </p>
          )}

          {status.error && <p className={ui.error}>{status.error}</p>}
        </div>
      )}
    </div>
  )
}
