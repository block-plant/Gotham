import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search as SearchIcon, Eye } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import StatusBadge from '../components/common/StatusBadge.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import * as firService from '../services/firService.js'

const PAGE_SIZE = 6

export default function FirList() {
  const navigate = useNavigate()
  const [firs, setFirs] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    firService.getAllFirs().then((data) => {
      setFirs(data)
      setIsLoading(false)
    })
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return firs
    return firs.filter((fir) =>
      [fir.id, fir.firNumber, fir.complainant?.fullName, fir.offence?.crimeCategory]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(q)),
    )
  }, [firs, query])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <AuthenticatedLayout title="FIR Records">
      <div className="mb-4 flex items-center gap-2">
        <div className="relative w-full max-w-sm">
          <SearchIcon
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary"
            size={16}
          />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(1)
            }}
            placeholder="Search by FIR ID, number, complainant, category..."
            className="w-full rounded-md border border-border bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-md border border-border bg-white">
        {isLoading ? (
          <div className="p-6">
            <LoadingSpinner label="Loading FIR records..." />
          </div>
        ) : pageItems.length === 0 ? (
          <p className="p-6 text-sm text-text-secondary">No FIR found.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-bg text-xs uppercase text-text-secondary">
              <tr>
                <th className="px-4 py-3">FIR ID</th>
                <th className="px-4 py-3">FIR Number</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Police Station</th>
                <th className="px-4 py-3">Crime Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {pageItems.map((fir) => (
                <tr key={fir.id} className="hover:bg-bg">
                  <td className="px-4 py-3 font-medium text-navy">{fir.id}</td>
                  <td className="px-4 py-3">{fir.firNumber}</td>
                  <td className="px-4 py-3">{fir.registrationDate}</td>
                  <td className="px-4 py-3">{fir.policeStation?.name}</td>
                  <td className="px-4 py-3">{fir.offence?.crimeCategory}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={fir.status} />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/firs/${fir.id}`)}
                      className="flex items-center gap-1 text-primary hover:underline"
                    >
                      <Eye size={14} /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2 text-sm">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`h-8 w-8 rounded-md border ${
                p === page
                  ? 'border-primary bg-primary text-white'
                  : 'border-border bg-white text-text-secondary hover:bg-bg'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}
    </AuthenticatedLayout>
  )
}