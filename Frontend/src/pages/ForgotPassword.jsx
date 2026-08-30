import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Shield, ArrowLeft } from 'lucide-react'
import * as authService from '../services/authService.js'
import Input from '../components/common/Input.jsx'
import Button from '../components/common/Button.jsx'

const schema = z.object({
  email: z.string().email('Enter a valid official email address'),
})

export default function ForgotPassword() {
  const [successMessage, setSuccessMessage] = useState('')
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) })

  async function onSubmit(data) {
    setServerError('')
    setSuccessMessage('')
    try {
      const result = await authService.requestPasswordReset(data.email)
      setSuccessMessage(result.message)
    } catch (err) {
      setServerError('Something went wrong. Please try again.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-white p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-navy">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-navy">Reset Password</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Enter your official email to receive reset instructions
          </p>
        </div>

        {successMessage ? (
          <p className="rounded-md bg-success/10 px-3 py-3 text-sm text-success">
            {successMessage}
          </p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <Input
              label="Official Email Address"
              type="email"
              error={errors.email?.message}
              {...register('email')}
            />

            {serverError && (
              <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
                {serverError}
              </p>
            )}

            <Button type="submit" isLoading={isSubmitting} className="w-full">
              {isSubmitting ? 'Sending...' : 'Send Reset Link'}
            </Button>
          </form>
        )}

        <Link
          to="/login"
          className="mt-6 flex items-center justify-center gap-1 text-sm text-primary hover:underline"
        >
          <ArrowLeft size={14} /> Back to Login
        </Link>
      </div>
    </div>
  )
}