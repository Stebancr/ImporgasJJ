import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Restarts the document scroll only when the URL path or query changes. */
export default function ScrollToTop() {
  const { pathname, search } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, search])

  return null
}
