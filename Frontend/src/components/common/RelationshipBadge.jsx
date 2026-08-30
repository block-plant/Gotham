import { getRelationshipStrength, strengthColors } from '../../utils/relationshipUtils.js'

export default function RelationshipBadge({ score }) {
  const strength = getRelationshipStrength(score)
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${strengthColors[strength]}`}
    >
      {strength} ({score})
    </span>
  )
}