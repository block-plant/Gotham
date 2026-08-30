// Centralized localStorage access so no other file touches localStorage directly.
// This makes it easy to swap for real backend calls / sessionStorage / cookies later.

const KEYS = {
  AUTH_USER: 'gotham_auth_user',
  FIRS: 'gotham_firs',
}

export function getItem(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setItem(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function removeItem(key) {
  localStorage.removeItem(key)
}

export { KEYS }