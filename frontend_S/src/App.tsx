import { lazy } from 'react'
import { PageBoundary } from '@/components/PageBoundary'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import DashboardLayout from '@/components/layout/DashboardLayout'

// Pages
const LoginPage = lazy(() => import('@/app/pages/LoginPage'))
const DashboardPage = lazy(() => import('@/app/pages/DashboardPage'))
const ProductsPage = lazy(() => import('@/app/pages/ProductsPage'))
const CategoriesPage = lazy(() => import('@/app/pages/CategoriesPage'))
const BrandsPage = lazy(() => import('@/app/pages/BrandsPage'))
const LocationsPage = lazy(() => import('@/app/pages/LocationsPage'))
const OrdersPage = lazy(() => import('@/app/pages/OrdersPage'))
const UsersPage = lazy(() => import('@/app/pages/UsersPage'))
const ProfilePage = lazy(() => import('@/app/pages/ProfilePage'))
const GestionPage = lazy(() => import('@/app/pages/GestionPage'))
const ChatPage = lazy(() => import('@/app/pages/ChatPage'))
const VisitsPage = lazy(() => import('@/app/pages/VisitsPage'))

export default function App() {
  return (
    <AuthProvider>
      <PageBoundary><Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<Navigate to="/login" replace />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute allowedRoles={['admin']}>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="brands" element={<BrandsPage />} />
          <Route path="locations" element={<LocationsPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route
            path="users"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="gestion">
            <Route index element={<Navigate to="cotizaciones" replace />} />
            <Route
              path="cotizaciones"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <GestionPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="facturas"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <GestionPage />
                </ProtectedRoute>
              }
            />
          </Route>
          <Route path="profile" element={<ProfilePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="visits" element={<VisitsPage />} />
        </Route>

        {/* Redirect root to dashboard or login */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* 404 - Redirect to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes></PageBoundary>
    </AuthProvider>
  )
}
