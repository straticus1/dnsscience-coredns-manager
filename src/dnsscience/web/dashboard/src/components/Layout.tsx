import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Server,
  Database,
  Search,
  Settings,
  GitCompare,
  ArrowRightLeft,
  Activity
} from 'lucide-react'
import { useStore } from '../store'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Service', href: '/service', icon: Server },
  { name: 'Cache', href: '/cache', icon: Database },
  { name: 'Query', href: '/query', icon: Search },
  { name: 'Config', href: '/config', icon: Settings },
  { name: 'Compare', href: '/compare', icon: GitCompare },
  { name: 'Migrate', href: '/migrate', icon: ArrowRightLeft },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { resolver, setResolver } = useStore()

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700">
        <div className="p-6">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-primary-500" />
            DNS Science
          </h1>
        </div>

        {/* Resolver Toggle */}
        <div className="px-4 mb-4">
          <div className="flex bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setResolver('coredns')}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                resolver === 'coredns'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              CoreDNS
            </button>
            <button
              onClick={() => setResolver('unbound')}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                resolver === 'unbound'
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Unbound
            </button>
          </div>
        </div>

        <nav className="px-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
