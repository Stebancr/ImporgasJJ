import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { PageLoading } from './PageBoundary'

export default function StoreTermsRoute({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, user } = useAuth()
  const location = useLocation()
  if (isLoading) return <PageLoading />
  const redirect = encodeURIComponent(location.pathname + location.search)
  if (!isAuthenticated || !user) return <Navigate replace to={`/login?redirect=${redirect}`} />
  if (!user.terms_accepted_at || user.terms_version !== user.current_terms_version) {
    return <Navigate replace to={`/terminos-y-condiciones?redirect=${redirect}`} />
  }
  return <>{children}</>
}
