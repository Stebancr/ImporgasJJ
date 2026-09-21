import { ReactNode } from 'react'
import Header from './Header'
import Footer from './Footer'
import Chatbot from './Chatbot'
import { useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

function Layout({ children }: LayoutProps) {
  const { pathname } = useLocation()
  const formPage = ['/checkout', '/login', '/perfil/editar'].includes(pathname) || pathname.startsWith('/restablecer-contrasena/')
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:p-3 focus:bg-white focus:text-primary">Saltar al contenido</a>
      <Header />
      <main id="main-content" className="min-w-0 flex-1">
        {children}
      </main>
      <Footer />
      <div className={formPage ? 'hidden sm:block' : undefined}><Chatbot /></div>
    </div>
  )
}

export default Layout
