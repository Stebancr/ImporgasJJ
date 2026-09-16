import { ReactNode } from 'react'
import Header from './Header'
import Footer from './Footer'
import Chatbot from './Chatbot'

interface LayoutProps {
  children: ReactNode
}

function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:p-3 focus:bg-white focus:text-primary">Saltar al contenido</a>
      <Header />
      <main id="main-content" className="min-w-0 flex-1">
        {children}
      </main>
      <Footer />
      <Chatbot />
    </div>
  )
}

export default Layout
