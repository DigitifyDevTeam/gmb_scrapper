import { StatCard } from '../components/StatCard'
import { Spinner } from '../components/Spinner'
import { useProspectStats } from '../api/hooks'
import { ui } from '../theme/ui'

export function DashboardPage() {
  const { data, isLoading, isError } = useProspectStats()

  if (isLoading) return <Spinner />
  if (isError || !data) {
    return <p className={ui.error}>Impossible de charger les statistiques.</p>
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className={ui.pageTitle}>Tableau de bord</h2>
        <p className={ui.pageSubtitle}>Vue d&apos;ensemble des entreprises locales découvertes.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Total entreprises" value={data.total} accent="indigo" />
        <StatCard label="Sans site web" value={data.without_website} accent="rose" />
        <StatCard label="Avec site web" value={data.with_website} accent="emerald" />
      </div>
    </div>
  )
}
