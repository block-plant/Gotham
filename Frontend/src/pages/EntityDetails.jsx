import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, ChevronRight, ShieldAlert } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import EntityCard from '../components/search/EntityCard.jsx'
import * as searchService from '../services/searchService.js'

const riskColors = {
  High: 'bg-danger/10 text-danger',
  Medium: 'bg-warning/10 text-warning',
  Low: 'bg-success/10 text-success',
}

export default function EntityDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [entity, setEntity] = useState(null)
  const [relationships, setRelationships] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setIsLoading(true)
    setError('')
    Promise.all([
      searchService.getEntityById(id),
      searchService.getEntityRelationships(id),
    ])
      .then(([entityData, rels]) => {
        setEntity(entityData)
        setRelationships(rels)
      })
      .catch(() => setError('Entity not found.'))
      .finally(() => setIsLoading(false))
  }, [id])

  return (
    <AuthenticatedLayout title="Entity Details">
      <div className="mb-3 flex items-center gap-1 text-xs text-text-secondary">
        <Link to="/search" className="hover:underline">Search Intelligence</Link>
        <ChevronRight size={12} />
        <span className="text-text-primary">{entity?.name || '...'}</span>
      </div>

      <button
        onClick={() => navigate(-1)}
        className="mb-4 flex items-center gap-1 text-sm text-primary hover:underline"
      >
        <ArrowLeft size={14} /> Back to Search Results
      </button>

      {isLoading && <LoadingSpinner label="Loading entity..." />}
      {error && <p className="text-sm text-danger">{error}</p>}

      {entity && (
        <div className="flex flex-col gap-6">
          {/* PRIMARY ENTITY */}
          <div className="rounded-md border border-border bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
              Primary Entity
            </p>
            <div className="mt-2 flex items-start justify-between gap-3">
              <div>
                <h1 className="text-xl font-bold text-navy">{entity.name}</h1>
                <p className="mt-1 text-sm text-text-secondary">
                  Type: {entity.type}
                </p>
              </div>
              {entity.riskLevel && (
                <span
                  className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${riskColors[entity.riskLevel]}`}
                >
                  <ShieldAlert size={14} /> Risk Level: {entity.riskLevel}
                </span>
              )}
            </div>

            <EntityFields entity={entity} />
          </div>

          {/* RELATED ENTITIES */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-text-secondary">
              Closely Related Entities
            </h2>
            {relationships.length === 0 ? (
              <p className="text-sm text-text-secondary">
                No related entities found for this record.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {relationships.map((rel, i) => (
                  <EntityCard key={rel.toEntityId} index={i + 1} relationship={rel} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  )
}

// Renders type-specific fields per the spec (Person/Vehicle/Phone/Location/Organization).
function EntityFields({ entity }) {
  const rows = []

  if (entity.type === 'Criminal') {
    rows.push(
      ['Age', entity.age],
      ['Gender', entity.gender],
      ['Known Aliases', entity.aliases?.join(', ')],
      ['Address', entity.address],
      ['Phone Numbers', entity.phoneNumbers?.join(', ')],
      ['Associated FIRs', entity.associatedFirs?.length],
    )
  } else if (entity.type === 'Vehicle') {
    rows.push(
      ['Vehicle Type', entity.vehicleType],
      ['Owner', entity.owner],
      ['Associated Criminals', entity.associatedCriminals?.join(', ') || 'None on record'],
      ['Associated FIRs', entity.associatedFirs?.length],
    )
  } else if (entity.type === 'Phone Number') {
    rows.push(
      ['Associated Person', entity.associatedPerson],
      ['Associated FIRs', entity.associatedFirs?.length],
    )
  } else if (entity.type === 'Location') {
    rows.push(
      ['Address', entity.address],
      ['Associated Entities', entity.associatedEntities?.join(', ')],
      ['Associated FIRs', entity.associatedFirs?.length],
    )
  } else if (entity.type === 'Organization') {
    rows.push(
      ['Organization Type', entity.orgType],
      ['Associated Individuals', entity.associatedIndividuals?.join(', ')],
      ['Associated FIRs', entity.associatedFirs?.length],
    )
  }

  rows.push(['Last Known Activity', entity.lastKnownActivity])

  return (
    <div className="mt-4 grid grid-cols-1 gap-x-6 gap-y-1 border-t border-border pt-4 sm:grid-cols-2">
      {rows
        .filter(([, value]) => value !== undefined && value !== '')
        .map(([label, value]) => (
          <div key={label} className="flex justify-between border-b border-border/50 py-1 text-sm">
            <span className="text-text-secondary">{label}:</span>
            <span className="text-right text-text-primary">{value}</span>
          </div>
        ))}
    </div>
  )
}