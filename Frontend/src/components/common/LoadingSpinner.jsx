import { Loader2 } from 'lucide-react'

export default function LoadingSpinner({ label = 'Loading...', size = 20 }) {
  return (
    <div className="flex items-center gap-2 text-sm text-text-secondary">
      <Loader2 className="animate-spin" size={size} />
      <span>{label}</span>
    </div>
  )
}