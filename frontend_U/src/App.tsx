import { lazy, Suspense } from 'react'
import { PageBoundary } from './components/PageBoundary'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import StoreProtectedRoute from './components/StoreProtectedRoute'
import StoreTermsRoute from './components/StoreTermsRoute'
import ScrollToTop from './components/ScrollToTop'
import CanonicalUrl from './components/CanonicalUrl'
import HomePage from './app/pages/HomePage'
const ProductsPage = lazy(() => import('./app/pages/ProductsPage'))
const ProductDetailPage = lazy(() => import('./app/pages/ProductDetailPage'))
const CartPage = lazy(() => import('./app/pages/CartPage'))
const CheckoutPage = lazy(() => import('./app/pages/CheckoutPage'))
const OrderConfirmationPage = lazy(() => import('./app/pages/OrderConfirmationPage'))
const CheckoutResultPage = lazy(() => import('./app/pages/CheckoutResultPage'))
const OrderTrackingPage = lazy(() => import('./app/pages/OrderTrackingPage'))
const OrderDetailPage = lazy(() => import('./app/pages/OrderDetailPage'))
const ProfilePage = lazy(() => import('./app/pages/ProfilePage'))
const ContactPage = lazy(() => import('./app/pages/ContactPage'))
const LoginPage = lazy(() => import('./app/pages/LoginPage'))
const ResetPasswordPage = lazy(() => import('./app/pages/ResetPasswordPage'))
const NosotrosPage = lazy(() => import('./app/pages/NosotrosPage'))
const DataPolicyPage = lazy(() => import('./app/pages/DataPolicyPage'))
const TermsPage = lazy(() => import('./app/pages/TermsPage'))
import { AuthProvider } from './context/AuthContext'
import { CartProvider } from './context/CartContext'
import { FavoritesProvider } from './context/FavoritesContext'
import { AuthProvider as AdminAuthProvider } from './admin/context/AuthContext'
import './admin/pages/styles/globals.css'
import AdminProtectedRoute from './admin/components/AdminProtectedRoute'
const EditProfilePage = lazy(() => import('./app/pages/EditProfilePage'))
const MyOrdersPage = lazy(() => import('./app/pages/MyOrdersPage'))
const FavoritesPage = lazy(() => import('./app/pages/FavoritesPage'))
const AddressesPage = lazy(() => import('./app/pages/AddressesPage'))
const NotificationsPage = lazy(() => import('./app/pages/NotificationsPage'))
const DashboardLayout = lazy(() => import('./admin/components/DashboardLayout'))
const AdminLoginPage = lazy(() => import('./admin/pages/LoginPage'))
const AdminDashboardPage = lazy(() => import('./admin/pages/DashboardPage'))
const AdminProductsPage = lazy(() => import('./admin/pages/ProductsPage'))
const AdminCategoriesPage = lazy(() => import('./admin/pages/CategoriesPage'))
const AdminBrandsPage = lazy(() => import('./admin/pages/BrandsPage'))
const AdminLocationsPage = lazy(() => import('./admin/pages/LocationsPage'))
const AdminOrdersPage = lazy(() => import('./admin/pages/OrdersPage'))
const AdminUsersPage = lazy(() => import('./admin/pages/UsersPage'))
const AdminProfilePage = lazy(() => import('./admin/pages/ProfilePage'))
const AdminGestionPage = lazy(() => import('./admin/pages/GestionPage'))
const AdminVisitsPage = lazy(() => import('./admin/pages/VisitsPage'))

// Material UI y React Query solo se descargan al entrar al módulo CRM; el
// ecommerce conserva un bundle inicial más pequeño y sus rutas no cambian.
const AdminChatPage = lazy(() => import('./admin/pages/ChatPage'))
const MetaIntegrationsPage = lazy(() => import('./admin/pages/MetaIntegrationsPage'))

function CRMPageFallback() {
  return <div className="p-6 text-sm text-muted-foreground">Cargando CRM…</div>
}

function StoreRoutes() {
  return (
    <AuthProvider><CartProvider><FavoritesProvider><Layout>
      <PageBoundary>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/productos" element={<ProductsPage />} />
        <Route path="/producto/:id" element={<ProductDetailPage />} />
        <Route path="/carrito" element={<StoreProtectedRoute><CartPage /></StoreProtectedRoute>} />
        <Route path="/checkout" element={<StoreTermsRoute><CheckoutPage /></StoreTermsRoute>} />
        <Route path="/checkout/resultado" element={<StoreProtectedRoute><CheckoutResultPage /></StoreProtectedRoute>} />
        <Route path="/orden-confirmada" element={<StoreProtectedRoute><OrderConfirmationPage /></StoreProtectedRoute>} />
        <Route path="/seguimiento" element={<StoreProtectedRoute><OrderTrackingPage /></StoreProtectedRoute>} />
        <Route path="/pedido/:trackingCode" element={<StoreProtectedRoute><OrderDetailPage /></StoreProtectedRoute>} />
        <Route path="/perfil" element={<StoreProtectedRoute><ProfilePage /></StoreProtectedRoute>} />
        <Route path="/perfil/editar" element={<StoreProtectedRoute><EditProfilePage /></StoreProtectedRoute>} />
        <Route path="/mis-pedidos" element={<StoreProtectedRoute><MyOrdersPage /></StoreProtectedRoute>} />
        <Route path="/favoritos" element={<StoreProtectedRoute><FavoritesPage /></StoreProtectedRoute>} />
        <Route path="/direcciones" element={<StoreProtectedRoute><AddressesPage /></StoreProtectedRoute>} />
        <Route path="/notificaciones" element={<StoreProtectedRoute><NotificationsPage /></StoreProtectedRoute>} />
        <Route path="/contacto" element={<ContactPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/restablecer-contrasena/:uid/:token" element={<ResetPasswordPage />} />
        <Route path="/nosotros" element={<NosotrosPage />} />
        <Route path="/politica-tratamiento-datos" element={<DataPolicyPage />} />
        <Route path="/terminos-y-condiciones" element={<TermsPage />} />
        <Route path="*" element={<section className="max-w-xl mx-auto p-6"><h1 className="text-2xl font-bold">Página no encontrada</h1><a className="underline text-primary" href="/">Volver al inicio</a></section>} />
      </Routes>
      </PageBoundary>
    </Layout></FavoritesProvider></CartProvider></AuthProvider>
  )
}

function AdminRoutes() {
  return (
    <AdminAuthProvider>
      <PageBoundary><Routes>
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
        <Route path="chat" element={<Suspense fallback={<CRMPageFallback />}><AdminChatPage /></Suspense>} />
        <Route path="chat/integraciones" element={<Suspense fallback={<CRMPageFallback />}><MetaIntegrationsPage /></Suspense>} />
        <Route path="visitas" element={<AdminVisitsPage />} />
        <Route path="gestion" element={<Navigate to="cotizaciones" replace />} />
        <Route path="gestion/cotizaciones" element={<AdminGestionPage />} />
        <Route path="gestion/facturas" element={<AdminGestionPage />} />
      </Route>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="*" element={<Navigate to="dashboard" replace />} />
      </Routes></PageBoundary>
    </AdminAuthProvider>
  )
}

function App() {
  return (
          <BrowserRouter>
            <CanonicalUrl />
            <ScrollToTop />
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
  )
}

export default App
