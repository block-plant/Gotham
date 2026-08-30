import { mockFirs } from '../data/firData.js'
import { getItem, setItem, KEYS } from '../utils/storageUtils.js'

function mockDelay(ms = 500) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function getCreatedFirs() {
  return getItem(KEYS.FIRS) || []
}

function nextFirId(existingFirs) {
  const n = existingFirs.length + 1
  return `FIR-2026-${String(n).padStart(3, '0')}`
}

// TODO: Replace mock response with backend API call -> GET /firs
export async function getAllFirs() {
  await mockDelay()
  const created = getCreatedFirs()
  // Newly created FIRs first, then static mock records, newest overall first.
  return [...created, ...mockFirs].sort(
    (a, b) => new Date(b.createdAt) - new Date(a.createdAt),
  )
}

// TODO: Replace mock response with backend API call -> GET /firs/:id
export async function getFirById(id) {
  await mockDelay(300)
  const all = [...getCreatedFirs(), ...mockFirs]
  const fir = all.find((f) => f.id === id)
  if (!fir) throw new Error('FIR not found.')
  return fir
}

// TODO: Replace mock response with backend API call -> POST /firs
export async function createFir(data) {
  await mockDelay(900)
  const all = [...getCreatedFirs(), ...mockFirs]
  const id = nextFirId(all)

  const newFir = {
    ...data,
    id,
    status: 'Registered',
    createdAt: new Date().toISOString(),
  }

  const created = getCreatedFirs()
  setItem(KEYS.FIRS, [newFir, ...created])
  return newFir
}