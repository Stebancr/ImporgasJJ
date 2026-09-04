// calendar.tsx â€” redirects to VisitsPage which has the calendar tab built in
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function CalendarPage() {
  const navigate = useNavigate()
  useEffect(() => {
    navigate('/admin/visitas', { replace: true })
  }, [navigate])
  return null
}
