import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute.jsx'
import Login from '../pages/Login.jsx'
import ForgotPassword from '../pages/ForgotPassword.jsx'
import Dashboard from '../pages/Dashboard.jsx'
import RegisterFir from '../pages/RegisterFIR.jsx'
import FirList from '../pages/FirList.jsx'
import FirDetails from '../pages/FirDetails.jsx'
import Search from '../pages/Search.jsx'
import EntityDetails from '../pages/EntityDetails.jsx'
import NotFound from '../pages/NotFound.jsx'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/firs/register"
        element={
          <ProtectedRoute>
            <RegisterFir />
          </ProtectedRoute>
        }
      />
      <Route
        path="/firs/:id"
        element={
          <ProtectedRoute>
            <FirDetails />
          </ProtectedRoute>
        }
      />
      <Route
        path="/firs"
        element={
          <ProtectedRoute>
            <FirList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <Search />
          </ProtectedRoute>
        }
      />
      <Route
        path="/entities/:id"
        element={
          <ProtectedRoute>
            <EntityDetails />
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}