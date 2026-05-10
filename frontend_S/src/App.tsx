import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import DashboardLayout from '@/components/layout/DashboardLayout'

// Pages
import LoginPage from '@/app/pages/LoginPage'
import RegisterPage from '@/app/pages/RegisterPage'
import DashboardPage from '@/app/pages/DashboardPage'
import ProductsPage from '@/app/pages/ProductsPage'
import CategoriesPage from '@/app/pages/CategoriesPage'
import BrandsPage from '@/app/pages/BrandsPage'
import LocationsPage from '@/app/pages/LocationsPage'
import OrdersPage from '@/app/pages/OrdersPage'
import UsersPage from '@/app/pages/UsersPage'
import ProfilePage from '@/app/pages/ProfilePage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
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
          <Route path="profile" element={<ProfilePage />} />
        </Route>

        {/* Redirect root to dashboard or login */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        
        {/* 404 - Redirect to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
