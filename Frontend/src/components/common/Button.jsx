import { Loader2 } from 'lucide-react'

const variants = {
  primary: 'bg-navy text-white hover:bg-[#0a2340] disabled:bg-[#0B2A4A]/50',
  secondary: 'bg-white text-navy border border-border hover:bg-bg',
  danger: 'bg-danger text-white hover:bg-[#b91c1c]',
}

export default function Button({
  children,
  variant = 'primary',
  isLoading = false,
  type = 'button',
  className = '',
  ...rest
}) {
  return (
    <button
      type={type}
      disabled={isLoading || rest.disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...rest}
    >
      {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
}