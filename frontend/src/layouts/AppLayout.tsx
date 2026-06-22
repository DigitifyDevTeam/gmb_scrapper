import { NavLink, Outlet } from 'react-router-dom'
import { ThemeToggle } from '../components/ThemeToggle'

const navItems = [
  { to: '/', label: 'Tableau de bord' },
  { to: '/search', label: 'Recherche' },
  { to: '/bulk', label: 'Scraping en masse' },
  { to: '/prospects', label: 'Prospects' },
]

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col md:flex-row">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden dark:border-slate-800 dark:bg-slate-900/80">
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Website scrapper</h1>
          </div>
          <ThemeToggle />
        </header>

        <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900/50 md:flex">
          <div className="mb-8">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Website scrapper</h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Prospection B2B</p>
          </div>
          <nav className="space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto pt-6">
            <ThemeToggle />
          </div>
        </aside>

        <main className="flex-1 p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
