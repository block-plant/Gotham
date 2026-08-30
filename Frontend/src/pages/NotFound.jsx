import { Link } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-4 text-center">
      <ShieldAlert className="mb-3 text-navy" size={40} />
      <h1 className="text-2xl font-bold text-navy">404 — Page Not Found</h1>
      <p className="mt-2 text-sm text-text-secondary">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/dashboard"
        className="mt-5 rounded-md bg-navy px-4 py-2 text-sm font-medium text-white hover:bg-[#0a2340]"
      >
        Back to Dashboard
      </Link>
    </div>
  )
}