import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { PageLoading } from './PageBoundary'

export default function StoreProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, user } = useAuth()
  const location = useLocation()
  if (isLoading) return <PageLoading />
  if (!isAuthenticated || !user) return <Navigate replace to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`} />
  return <>{children}</>
}
