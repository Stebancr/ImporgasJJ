import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './app/pages/HomePage'
import ProductsPage from './app/pages/ProductsPage'
import ProductDetailPage from './app/pages/ProductDetailPage'
import CartPage from './app/pages/CartPage'
import CheckoutPage from './app/pages/CheckoutPage'
import OrderTrackingPage from './app/pages/OrderTrackingPage'
import OrderDetailPage from './app/pages/OrderDetailPage'
import ProfilePage from './app/pages/ProfilePage'
import ContactPage from './app/pages/ContactPage'
import LoginPage from './app/pages/LoginPage'
import { AuthProvider } from './context/AuthContext'
import { CartProvider } from './context/CartContext'

function App() {
  return (
    <AuthProvider>
      <CartProvider>
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/productos" element={<ProductsPage />} />
          <Route path="/producto/:id" element={<ProductDetailPage />} />
          <Route path="/carrito" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/seguimiento" element={<OrderTrackingPage />} />
          <Route path="/pedido/:trackingCode" element={<OrderDetailPage />} />
          <Route path="/perfil" element={<ProfilePage />} />
          <Route path="/contacto" element={<ContactPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </Layout>
    </Router>
      </CartProvider>
    </AuthProvider>
  )
}

export default App
