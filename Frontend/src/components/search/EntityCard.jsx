import { useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import RelationshipBadge from '../common/RelationshipBadge.jsx'

// Clickable card for a related entity/criminal. Used on Entity Details pages.
// Clicking anywhere on the card (or the button) navigates to /entities/:id.
export default function EntityCard({ index, relationship }) {
  const navigate = useNavigate()
  const { entity, relationshipType, relationshipScore, explanation, associatedFirCount } =
    relationship

  if (!entity) return null

  function goToEntity() {
    navigate(`/entities/${entity.id}`)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      goToEntity()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={goToEntity}
      onKeyDown={handleKeyDown}
      className="cursor-pointer rounded-md border border-border bg-white p-4 transition-colors hover:border-navy"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-text-secondary">{index}.</p>
          <h4 className="font-semibold text-navy">{entity.name}</h4>
          <p className="mt-1 text-xs text-text-secondary">
            Entity Type: {entity.type}
          </p>
          <p className="text-xs text-text-secondary">
            Relationship: {relationshipType}
          </p>
          {explanation && (
            <p className="mt-1 text-xs text-text-secondary">{explanation}</p>
          )}
          <p className="mt-1 text-xs text-text-secondary">
            Associated FIRs: {associatedFirCount ?? entity.associatedFirs?.length ?? 0}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <RelationshipBadge score={relationshipScore} />
          <span className="flex items-center gap-1 text-xs font-medium text-primary">
            View Details <ChevronRight size={14} />
          </span>
        </div>
      </div>
    </div>
  )
}