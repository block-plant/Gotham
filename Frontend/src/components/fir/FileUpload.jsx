import { useRef, useState } from 'react'
import { UploadCloud, File, X } from 'lucide-react'

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']

function formatBytes(bytes) {
  if (!bytes) return '0 KB'
  const kb = bytes / 1024
  return kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`
}

export default function FileUpload({ file, onFileSelect, onFileRemove }) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')

  function handleFiles(fileList) {
    const selected = fileList?.[0]
    if (!selected) return
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError('Only PDF, JPG, JPEG, or PNG files are supported.')
      return
    }
    setError('')
    onFileSelect(selected)
  }

  return (
    <div>
      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          className={`flex flex-col items-center justify-center rounded-md border-2 border-dashed px-4 py-8 text-center ${
            isDragging ? 'border-primary bg-primary/5' : 'border-border bg-bg'
          }`}
        >
          <UploadCloud className="mb-2 text-text-secondary" size={28} />
          <p className="text-sm text-text-secondary">
            Drag and drop your FIR document here
          </p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-3 rounded-md border border-border bg-white px-3 py-1.5 text-sm font-medium text-navy hover:bg-bg"
          >
            Browse Files
          </button>
          <p className="mt-2 text-xs text-text-secondary">PDF, JPG, JPEG, PNG</p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      ) : (
        <div className="flex items-center justify-between rounded-md border border-border bg-white px-3 py-2">
          <div className="flex items-center gap-2 overflow-hidden">
            <File className="shrink-0 text-primary" size={18} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-text-primary">
                {file.name}
              </p>
              <p className="text-xs text-text-secondary">
                {file.type || 'Unknown type'} • {formatBytes(file.size)}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onFileRemove}
            className="shrink-0 rounded-md p-1 text-text-secondary hover:bg-bg hover:text-danger"
            aria-label="Remove file"
          >
            <X size={16} />
          </button>
        </div>
      )}
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
}