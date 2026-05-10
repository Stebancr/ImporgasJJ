import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './app/pages/HomePage'
import ProductsPage from './app/pages/ProductsPage'
import ProductDetailPage from './app/pages/ProductDetailPage'
import CartPage from './app/pages/CartPage'
import CheckoutPage from './app/pages/CheckoutPage'
import OrderTrackingPage from './app/pages/OrderTrackingPage'
import ContactPage from './app/pages/ContactPage'
import LoginPage from './app/pages/LoginPage'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/productos" element={<ProductsPage />} />
          <Route path="/producto/:id" element={<ProductDetailPage />} />
          <Route path="/carrito" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/seguimiento" element={<OrderTrackingPage />} />
          <Route path="/contacto" element={<ContactPage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
