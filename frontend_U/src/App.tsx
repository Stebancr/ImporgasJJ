import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './app/pages/HomePage'
import ProductsPage from './app/pages/ProductsPage'
import ProductDetailPage from './app/pages/ProductDetailPage'
import CartPage from './app/pages/CartPage'
import CheckoutPage from './app/pages/CheckoutPage'
import OrderConfirmationPage from './app/pages/OrderConfirmationPage'
import CheckoutResultPage from './app/pages/CheckoutResultPage'
import OrderTrackingPage from './app/pages/OrderTrackingPage'
import OrderDetailPage from './app/pages/OrderDetailPage'
import ProfilePage from './app/pages/ProfilePage'
import ContactPage from './app/pages/ContactPage'
import LoginPage from './app/pages/LoginPage'
import NosotrosPage from './app/pages/NosotrosPage'
import { AuthProvider } from './context/AuthContext'
import { CartProvider } from './context/CartContext'
import { FavoritesProvider } from './context/FavoritesContext'
import { AuthProvider as AdminAuthProvider } from './admin/context/AuthContext'
import './admin/pages/styles/globals.css'
import AdminProtectedRoute from './admin/components/AdminProtectedRoute'
import DashboardLayout from './admin/components/DashboardLayout'
import AdminLoginPage from './admin/pages/LoginPage'
import AdminDashboardPage from './admin/pages/DashboardPage'
import AdminProductsPage from './admin/pages/ProductsPage'
import AdminCategoriesPage from './admin/pages/CategoriesPage'
import AdminBrandsPage from './admin/pages/BrandsPage'
import AdminLocationsPage from './admin/pages/LocationsPage'
import AdminOrdersPage from './admin/pages/OrdersPage'
import AdminUsersPage from './admin/pages/UsersPage'
import AdminProfilePage from './admin/pages/ProfilePage'
import AdminGestionPage from './admin/pages/GestionPage'
import AdminChatPage from './admin/pages/ChatPage'
import AdminVisitsPage from './admin/pages/VisitsPage'

function StoreRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/productos" element={<ProductsPage />} />
        <Route path="/producto/:id" element={<ProductDetailPage />} />
        <Route path="/carrito" element={<CartPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/checkout/resultado" element={<CheckoutResultPage />} />
        <Route path="/orden-confirmada" element={<OrderConfirmationPage />} />
        <Route path="/seguimiento" element={<OrderTrackingPage />} />
        <Route path="/pedido/:trackingCode" element={<OrderDetailPage />} />
        <Route path="/perfil" element={<ProfilePage />} />
        <Route path="/contacto" element={<ContactPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/nosotros" element={<NosotrosPage />} />
      </Routes>
    </Layout>
  )
}

function AdminRoutes() {
  return (
    <AdminAuthProvider>
      <Routes>
      <Route path="login" element={<AdminLoginPage />} />
      <Route
        element={
          <AdminProtectedRoute allowedRoles={['admin']}>
            <DashboardLayout />
          </AdminProtectedRoute>
        }
      >
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="productos" element={<AdminProductsPage />} />
        <Route path="categorias" element={<AdminCategoriesPage />} />
        <Route path="marcas" element={<AdminBrandsPage />} />
        <Route path="ubicaciones" element={<AdminLocationsPage />} />
        <Route path="ordenes" element={<AdminOrdersPage />} />
        <Route path="usuarios" element={<AdminUsersPage />} />
        <Route path="perfil" element={<AdminProfilePage />} />
        <Route path="chat" element={<AdminChatPage />} />
        <Route path="visitas" element={<AdminVisitsPage />} />
        <Route path="gestion" element={<Navigate to="cotizaciones" replace />} />
        <Route path="gestion/cotizaciones" element={<AdminGestionPage />} />
        <Route path="gestion/facturas" element={<AdminGestionPage />} />
      </Route>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="*" element={<Navigate to="dashboard" replace />} />
      </Routes>
    </AdminAuthProvider>
  )
}

function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <FavoritesProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/admin/*" element={<div className="admin-theme"><AdminRoutes /></div>} />
              {/* Compatibilidad temporal con enlaces administrativos existentes. */}
              <Route path="/dashboard/products" element={<Navigate to="/admin/productos" replace />} />
              <Route path="/dashboard/categories" element={<Navigate to="/admin/categorias" replace />} />
              <Route path="/dashboard/brands" element={<Navigate to="/admin/marcas" replace />} />
              <Route path="/dashboard/locations" element={<Navigate to="/admin/ubicaciones" replace />} />
              <Route path="/dashboard/orders" element={<Navigate to="/admin/ordenes" replace />} />
              <Route path="/dashboard/users" element={<Navigate to="/admin/usuarios" replace />} />
              <Route path="/dashboard/profile" element={<Navigate to="/admin/perfil" replace />} />
              <Route path="/dashboard/chat" element={<Navigate to="/admin/chat" replace />} />
              <Route path="/dashboard/visits" element={<Navigate to="/admin/visitas" replace />} />
              <Route path="/dashboard/gestion/cotizaciones" element={<Navigate to="/admin/gestion/cotizaciones" replace />} />
              <Route path="/dashboard/gestion/facturas" element={<Navigate to="/admin/gestion/facturas" replace />} />
              <Route path="/dashboard/*" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="/*" element={<StoreRoutes />} />
            </Routes>
          </BrowserRouter>
        </FavoritesProvider>
      </CartProvider>
    </AuthProvider>
  )
}

export default App
