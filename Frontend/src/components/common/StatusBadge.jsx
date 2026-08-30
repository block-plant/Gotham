const styles = {
  Registered: 'bg-primary/10 text-primary',
  'Under Investigation': 'bg-warning/10 text-warning',
  Closed: 'bg-success/10 text-success',
}

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] || 'bg-bg text-text-secondary'
      }`}
    >
      {status}
    </span>
  )
}