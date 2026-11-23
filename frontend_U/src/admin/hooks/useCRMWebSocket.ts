/** Mantiene la bandeja sincronizada sin exponer el JWT en la URL. */
import { useEffect, useRef, useState } from 'react'
import { revokeBrowserSession } from '../../services/sessionSecurity'
import { refreshAdminToken } from '../services/admin_token'

export interface CRMRealtimeEvent {
  type: string
  session_id: number
  message_id?: number
}

export function useCRMWebSocket(onEvent: (event: CRMRealtimeEvent) => void, onConnected?: () => void) {
  const callback = useRef(onEvent)
  const connectedCallback = useRef(onConnected)
  const [connected, setConnected] = useState(false)
  callback.current = onEvent
  connectedCallback.current = onConnected

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false
    let attempts = 0

    const connect = () => {
      if (stopped) return
      const token = localStorage.getItem('token')
      if (!token) return
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/crm-chat/`, ['crm-chat', `jwt.${token}`])
      socket.onopen = () => {
        attempts = 0
        setConnected(true)
        connectedCallback.current?.()
      }
      socket.onmessage = (message) => {
        if (stopped) return
        try { callback.current(JSON.parse(message.data) as CRMRealtimeEvent) } catch { /* payload ajeno */ }
      }
      socket.onclose = async (event) => {
        setConnected(false)
        if (stopped) return
        if (event.code === 4401 || event.code === 4403) {
          const current = localStorage.getItem('token')
          if (current && current !== token) { connect(); return }
          const fresh = await refreshAdminToken()
          if (fresh && !stopped) { connect(); return }
          stopped = true
          revokeBrowserSession({ key: 'token', value: token })
          return
        }
        if (!stopped) {
          attempts += 1
          if (attempts > 5) { stopped = true; return }
          reconnectTimer = setTimeout(connect, Math.min(30_000, 1000 * 2 ** attempts))
        }
      }
      socket.onerror = () => socket?.close()
    }

    connect()
    const stop = () => { stopped = true; if (reconnectTimer) clearTimeout(reconnectTimer); socket?.close() }
    window.addEventListener('session:revoked', stop)
    return () => {
      window.removeEventListener('session:revoked', stop)
      stopped = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  return connected
}
