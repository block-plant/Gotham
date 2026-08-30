import { getItem, setItem, removeItem, KEYS } from '../utils/storageUtils.js'
import { z } from 'zod'

// Demo credentials for the hackathon prototype.
const DEMO_EMAIL = 'demo@gotham.com'
const DEMO_PASSWORD = 'demo123'

export const loginSchema = z.object({
  email: z.string().min(1, 'Officer ID or Email is required'),
  password: z.string().min(1, 'Password is required'),
})

function mockDelay(ms = 700) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// TODO: Replace mock response with backend API call -> POST /auth/login
export async function login(email, password) {
  await mockDelay()

  if (email !== DEMO_EMAIL || password !== DEMO_PASSWORD) {
    throw new Error('Invalid Officer ID/Email or password.')
  }

  const user = {
    id: 'officer-001',
    name: 'Officer A. Verma',
    email: DEMO_EMAIL,
    role: 'officer',
    isGuest: false,
  }

  setItem(KEYS.AUTH_USER, user)
  return user
}

// TODO: Replace mock response with backend API call -> POST /auth/login/guest (or similar)
export async function loginAsGuest() {
  await mockDelay(300)

  const guestUser = {
    id: 'guest-001',
    name: 'Guest User',
    email: null,
    role: 'guest',
    isGuest: true,
  }

  setItem(KEYS.AUTH_USER, guestUser)
  return guestUser
}

// TODO: Replace mock response with backend API call -> POST /auth/forgot-password
export async function requestPasswordReset(email) {
  await mockDelay()
  // Always succeeds in the mock — a real backend would look the email up server-side
  // and respond the same way regardless, to avoid leaking which emails exist.
  return {
    success: true,
    message:
      'If an account exists for this email, password reset instructions have been sent.',
  }
}

export function logout() {
  removeItem(KEYS.AUTH_USER)
}

export function getCurrentUser() {
  return getItem(KEYS.AUTH_USER)
}