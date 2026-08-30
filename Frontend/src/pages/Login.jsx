import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Shield, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { loginSchema } from '../services/authService.js'
import Input from '../components/common/Input.jsx'
import Button from '../components/common/Button.jsx'

export default function Login() {
  const { login, loginAsGuest } = useAuth()
  const navigate = useNavigate()

  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState('')
  const [isGuestLoading, setIsGuestLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
  })

  async function onSubmit(data) {
    setServerError('')

    try {
      await login(data.email, data.password)
      navigate('/dashboard')
    } catch (err) {
      setServerError(err.message || 'Login failed. Please try again.')
    }
  }

  async function handleGuestLogin() {
    setIsGuestLoading(true)

    try {
      await loginAsGuest()
      navigate('/dashboard')
    } finally {
      setIsGuestLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4 py-6">
      <div className="w-full max-w-md rounded-lg border border-border bg-white p-6 shadow-sm">

        {/* Header */}
        <div className="mb-4 flex flex-col items-center text-center">
          <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-full bg-navy">
            <Shield className="h-5 w-5 text-white" />
          </div>

          <h1 className="text-xl font-bold tracking-wide text-navy">
            GOTHAM
          </h1>

          <p className="mt-1 text-sm text-text-secondary">
            CNA
          </p>
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-3"
        >
          <Input
            label="Officer ID or Email"
            type="text"
            autoComplete="username"
            error={errors.email?.message}
            {...register('email')}
          />

          <div className="relative">
            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              error={errors.password?.message}
              {...register('password')}
            />

            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-[34px] text-text-secondary hover:text-text-primary"
              aria-label={
                showPassword ? 'Hide password' : 'Show password'
              }
            >
              {showPassword ? (
                <EyeOff size={18} />
              ) : (
                <Eye size={18} />
              )}
            </button>
          </div>

          {serverError && (
            <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
              {serverError}
            </p>
          )}

          <div className="flex justify-end">
            <Link
              to="/forgot-password"
              className="text-sm text-primary hover:underline"
            >
              Forgot Password?
            </Link>
          </div>

          <Button
            type="submit"
            isLoading={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>

        {/* Divider */}
        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-text-secondary">OR</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* Guest Login */}
        <Button
          variant="secondary"
          className="w-full"
          isLoading={isGuestLoading}
          onClick={handleGuestLogin}
        >
          {isGuestLoading ? 'Signing in...' : 'Continue as Guest'}
        </Button>

        <p className="mt-1 text-center text-xs text-warning">
          Demo Access
        </p>

        {/* Demo Credentials */}
        <div className="mt-4 rounded-md bg-bg px-3 py-2 text-center text-xs text-text-secondary">
          Demo credentials — demo@gotham.com / demo123
        </div>

      </div>
    </div>
  )
}