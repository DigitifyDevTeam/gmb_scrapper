interface StatCardProps {
  label: string
  value: number | string
  accent?: 'indigo' | 'emerald' | 'rose'
}

const accents = {
  indigo:
    'border-indigo-200 bg-indigo-50 text-indigo-800 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300',
  emerald:
    'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300',
  rose: 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300',
}

export function StatCard({ label, value, accent = 'indigo' }: StatCardProps) {
  return (
    <div className={`rounded-2xl border p-6 ${accents[accent]}`}>
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{value}</p>
    </div>
  )
}
