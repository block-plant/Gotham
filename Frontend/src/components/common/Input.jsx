import { forwardRef } from 'react'

const Input = forwardRef(function Input(
  { label, error, hint, className = '', ...rest },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-text-primary">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={`rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40 ${
          error ? 'border-danger' : 'border-border'
        } ${className}`}
        {...rest}
      />
      {hint && !error && (
        <span className="text-xs text-text-secondary">{hint}</span>
      )}
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  )
})

export default Input