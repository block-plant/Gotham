import { mockEntities, mockRelationships } from '../data/entityData.js'
import { mockFirs } from '../data/firData.js'
import { getItem, KEYS } from '../utils/storageUtils.js'
import { sortByRelationshipScore } from '../utils/relationshipUtils.js'

function mockDelay(ms = 500) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const typeFilterMap = {
  'Criminal / Person': 'Criminal',
  Alias: 'Criminal', // aliases are matched against criminal records, not a separate type
  'Phone Number': 'Phone Number',
  Vehicle: 'Vehicle',
  Location: 'Location',
  Organization: 'Organization',
}

function entityMatches(entity, q) {
  const haystack = [
    entity.name,
    ...(entity.aliases || []),
    ...(entity.phoneNumbers || []),
    entity.id,
  ]
    .filter(Boolean)
    .map((s) => s.toLowerCase())
  return haystack.some((s) => s.includes(q))
}

// TODO: Replace mock response with backend API call -> GET /search?q=...&filter=...
export async function search(query, filter = 'All') {
  await mockDelay(600)
  const q = query.trim().toLowerCase()
  if (!q) return { entities: [], firs: [] }

  let entities = mockEntities.filter((e) => entityMatches(e, q))
  if (filter !== 'All' && filter !== 'FIR') {
    const targetType = typeFilterMap[filter]
    entities = entities.filter((e) => e.type === targetType)
  }

  let firs = []
  if (filter === 'All' || filter === 'FIR') {
    const created = getItem(KEYS.FIRS) || []
    const allFirs = [...created, ...mockFirs]
    firs = allFirs.filter((f) =>
      [f.id, f.firNumber, f.complainant?.fullName, f.offence?.crimeCategory]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(q)),
    )
  }

  return { entities, firs }
}

// TODO: Replace mock response with backend API call -> GET /entities/:id
export async function getEntityById(id) {
  await mockDelay(400)
  const entity = mockEntities.find((e) => e.id === id)
  if (!entity) throw new Error('Entity not found.')
  return entity
}

// TODO: Replace mock response with backend/ML API call -> GET /entities/:id/relationships
export async function getEntityRelationships(id) {
  await mockDelay(500)
  const relationships = mockRelationships[id] || []
  const enriched = relationships.map((rel) => {
    const entity = mockEntities.find((e) => e.id === rel.toEntityId)
    return { ...rel, entity }
  })
  return sortByRelationshipScore(enriched)
}