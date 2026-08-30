import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search as SearchIcon, FileText, ChevronRight } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import StatusBadge from '../components/common/StatusBadge.jsx'
import * as searchService from '../services/searchService.js'

const filters = [
  'All',
  'Criminal / Person',
  'Alias',
  'Phone Number',
  'Vehicle',
  'Location',
  'Organization',
  'FIR',
]

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState('All')
  const [results, setResults] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  async function runSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return
    setIsLoading(true)
    setHasSearched(true)
    const data = await searchService.search(query, activeFilter)
    setResults(data)
    setIsLoading(false)
  }

  const noResults =
    hasSearched &&
    !isLoading &&
    results &&
    results.entities.length === 0 &&
    results.firs.length === 0

  return (
    <AuthenticatedLayout title="Search Intelligence">
      <form onSubmit={runSearch} className="mb-4">
        <div className="relative">
          <SearchIcon
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary"
            size={18}
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search criminal, person, alias, phone number, vehicle, location, organization or FIR..."
            className="w-full rounded-md border border-border bg-white py-3 pl-10 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setActiveFilter(f)}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                activeFilter === f
                  ? 'border-navy bg-navy text-white'
                  : 'border-border bg-white text-text-secondary hover:bg-bg'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </form>

      {isLoading && (
        <div className="mt-6">
          <LoadingSpinner label="Searching intelligence records..." />
        </div>
      )}

      {noResults && (
        <p className="mt-6 text-sm text-text-secondary">
          No matching intelligence records found.
        </p>
      )}

      {results && !isLoading && (results.entities.length > 0 || results.firs.length > 0) && (
        <div className="mt-6 flex flex-col gap-6">
          {results.entities.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-text-secondary">
                Criminal / Entity Results
              </h3>
              <div className="flex flex-col gap-2">
                {results.entities.map((entity) => (
                  <button
                    key={entity.id}
                    onClick={() => navigate(`/entities/${entity.id}`)}
                    className="flex items-center justify-between rounded-md border border-border bg-white p-4 text-left hover:border-navy"
                  >
                    <div>
                      <p className="font-semibold text-navy">{entity.name}</p>
                      <p className="text-xs text-text-secondary">
                        {entity.type}
                        {entity.riskLevel ? ` • Risk: ${entity.riskLevel}` : ''}
                      </p>
                    </div>
                    <ChevronRight className="text-text-secondary" size={18} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {results.firs.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-text-secondary">
                FIR Results
              </h3>
              <div className="flex flex-col gap-2">
                {results.firs.map((fir) => (
                  <button
                    key={fir.id}
                    onClick={() => navigate(`/firs/${fir.id}`)}
                    className="flex items-center justify-between rounded-md border-l-4 border-l-warning border-y border-r border-border bg-white p-4 text-left hover:border-y-navy"
                  >
                    <div className="flex items-center gap-2">
                      <FileText size={16} className="text-warning" />
                      <div>
                        <p className="font-semibold text-navy">{fir.id}</p>
                        <p className="text-xs text-text-secondary">
                          {fir.firNumber} • {fir.offence?.crimeCategory}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={fir.status} />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </AuthenticatedLayout>
  )
}