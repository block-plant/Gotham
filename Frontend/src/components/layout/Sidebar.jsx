import { NavLink } from 'react-router-dom'
import {
  Shield,
  LayoutDashboard,
  FilePlus,
  FileText,
  Search,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext.jsx'

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/firs/register', label: 'Register FIR', icon: FilePlus },
  { to: '/firs', label: 'FIR Records', icon: FileText },
  { to: '/search', label: 'Search Intelligence', icon: Search },
]

export default function Sidebar({ onNavigate }) {
  const { logout } = useAuth()

  return (
    <div className="flex h-full flex-col bg-navy text-white">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-5">
        <Shield className="h-6 w-6" />
        <div>
          <div className="text-sm font-bold leading-tight">GOTHAM</div>
          <div className="text-[10px] leading-tight text-white/60">
            C N A
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-white/10 font-medium text-white'
                  : 'text-white/70 hover:bg-white/5 hover:text-white'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 border-t border-white/10 px-5 py-4 text-sm text-white/70 hover:text-white"
      >
        <LogOut size={18} />
        Logout
      </button>
    </div>
  )
}