import { useNavigate } from 'react-router-dom'
import { FilePlus, FileText, Search, Files, Users, Activity, Share2 } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import Button from '../components/common/Button.jsx'
import { useAuth } from '../contexts/AuthContext.jsx'

// Mock statistics — later replaced by a real backend summary endpoint.
const stats = [
  { label: 'Total FIRs', value: 11, icon: Files },
  { label: 'Criminal Records', value: 0, icon: Users },
  { label: 'Active Investigations', value: 0, icon: Activity },
  { label: 'Related Entities', value: 0, icon: Share2 },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <AuthenticatedLayout title="Dashboard">
      <h1 className="text-xl font-bold text-navy">
        Welcome to GOTHAM{user?.isGuest ? '' : `, ${user?.name}`}
      </h1>
      <p className="mt-1 text-sm text-text-secondary">
        AI-Powered Criminal Network Analysis System
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <div
            key={label}
            className="rounded-lg border border-border bg-white p-4"
          >
            <Icon className="h-5 w-5 text-primary" />
            <div className="mt-2 text-2xl font-bold text-navy">{value}</div>
            <div className="text-xs text-text-secondary">{label}</div>
          </div>
        ))}
      </div>

      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-text-secondary">
        Quick Actions
      </h2>
      <div className="mt-3 flex flex-wrap gap-3">
        <Button onClick={() => navigate('/firs/register')}>
          <FilePlus size={16} /> Register FIR
        </Button>
        <Button variant="secondary" onClick={() => navigate('/firs')}>
          <FileText size={16} /> View FIRs
        </Button>
        <Button variant="secondary" onClick={() => navigate('/search')}>
          <Search size={16} /> Search Criminal / Entity
        </Button>
      </div>
    </AuthenticatedLayout>
  )
}