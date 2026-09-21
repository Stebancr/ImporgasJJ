import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Mantiene una única URL canónica para cada ruta pública del SPA. */
export default function CanonicalUrl() {
  const location = useLocation()

  useEffect(() => {
    const configuredBase = String(import.meta.env.VITE_PUBLIC_APP_URL || window.location.origin)
      .replace(/\/$/, '')
    const canonicalUrl = `${configuredBase}${location.pathname || '/'}`
    let link = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    if (!link) {
      link = document.createElement('link')
      link.rel = 'canonical'
      document.head.appendChild(link)
    }
    link.href = canonicalUrl
  }, [location.pathname])

  return null
}
