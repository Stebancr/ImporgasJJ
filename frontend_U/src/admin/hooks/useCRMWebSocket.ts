/** Mantiene la bandeja sincronizada sin exponer el JWT en la URL. */
import { useEffect, useRef, useState } from 'react'

export interface CRMRealtimeEvent {
  type: string
  session_id: number
  message_id?: number
}

export function useCRMWebSocket(onEvent: (event: CRMRealtimeEvent) => void) {
  const callback = useRef(onEvent)
  const [connected, setConnected] = useState(false)
  callback.current = onEvent

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false
    let attempts = 0

    const connect = () => {
      if (stopped) return
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/crm-chat/`, ['crm-chat', `jwt.${token}`])
      socket.onopen = () => {
        attempts = 0
        setConnected(true)
      }
      socket.onmessage = (message) => {
        try { callback.current(JSON.parse(message.data) as CRMRealtimeEvent) } catch { /* payload ajeno */ }
      }
      socket.onclose = () => {
        setConnected(false)
        if (!stopped) {
          attempts += 1
          reconnectTimer = setTimeout(connect, Math.min(30_000, 1000 * 2 ** attempts))
        }
      }
      socket.onerror = () => socket?.close()
    }

    connect()
    return () => {
      stopped = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  return connected
}
