import { Menu, Search, UserCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext.jsx'

export default function Navbar({ title, onMenuClick }) {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-white px-4">
      <div className="flex items-center gap-3">
        <button
          className="rounded-md p-2 text-text-secondary hover:bg-bg lg:hidden"
          onClick={onMenuClick}
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/search')}
          className="rounded-md p-2 text-text-secondary hover:bg-bg"
          aria-label="Search"
        >
          <Search size={20} />
        </button>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <UserCircle size={22} />
          <span className="hidden sm:inline">{user?.name || 'User'}</span>
        </div>
      </div>
    </header>
  )
}