import { useState, type FormEvent } from 'react'
import { Button } from '../components/Button'
import { Input } from '../components/Input'
import { Badge } from '../components/Badge'
import { useCreateSearch, useScrapingStatus, useStartScraping } from '../api/hooks'
import { searchStatusLabels } from '../i18n/fr'
import { ui } from '../theme/ui'

export function SearchPage() {
  const [country, setCountry] = useState('France')
  const [city, setCity] = useState('Paris')
  const [category, setCategory] = useState('Plombier')
  const [jobId, setJobId] = useState<string | null>(null)

  const createSearch = useCreateSearch()
  const startScraping = useStartScraping()
  const { data: jobStatus } = useScrapingStatus(jobId, Boolean(jobId))

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const search = await createSearch.mutateAsync({ country, city, category })
    const scraping = await startScraping.mutateAsync(search.id)
    setJobId(scraping.job_id)
  }

  const isSubmitting = createSearch.isPending || startScraping.isPending

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h2 className={ui.pageTitle}>Nouvelle recherche</h2>
        <p className={ui.pageSubtitle}>Créez une recherche et lancez le scraping Google Maps.</p>
      </div>

      <form onSubmit={handleSubmit} className={`space-y-4 p-6 ${ui.card}`}>
        <Input label="Pays" value={country} onChange={(e) => setCountry(e.target.value)} required />
        <Input label="Ville" value={city} onChange={(e) => setCity(e.target.value)} required />
        <Input label="Catégorie" value={category} onChange={(e) => setCategory(e.target.value)} required />
        <Button type="submit" loading={isSubmitting} className="w-full">
          Lancer le scraping
        </Button>
      </form>

      {jobStatus && (
        <div className={`space-y-3 p-6 ${ui.card}`}>
          <h3 className={ui.heading}>Statut du scraping</h3>
          <div className="flex items-center gap-3">
            <Badge variant={jobStatus.status === 'completed' ? 'success' : jobStatus.status === 'failed' ? 'danger' : 'neutral'}>
              {searchStatusLabels[jobStatus.status]}
            </Badge>
            <span className={ui.cardMuted}>Tâche : {jobStatus.job_id}</span>
          </div>
          <p className={ui.body}>Trouvés : {jobStatus.prospects_found}</p>
          <p className={ui.body}>Enregistrés : {jobStatus.prospects_saved}</p>
          {jobStatus.error && <p className={ui.error}>{jobStatus.error}</p>}
        </div>
      )}
    </div>
  )
}
