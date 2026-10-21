import { useSyncExternalStore } from 'react'
import type { SessionFilters } from '../services/admin_chat'

const snapshots = new Map<string, SessionFilters>()
const listeners = new Set<() => void>()
const channels = ['all', 'whatsapp_web', 'whatsapp', 'instagram', 'facebook', 'ecommerce']
const defaults: SessionFilters = { channel: 'all', status: 'all', search: '', priority: 'all', unanswered: false }

function snapshot(userId: string): SessionFilters {
  if (!snapshots.has(userId)) {
    let saved: SessionFilters = {}
    try { saved = JSON.parse(sessionStorage.getItem(`crm-inbox:${userId}`) || '{}') } catch { /* storage unavailable */ }
    snapshots.set(userId, {
      ...defaults,
      channel: channels.includes(saved?.channel || '') ? saved.channel : 'all',
      status: ['all', 'bot', 'waiting', 'active', 'closed'].includes(saved?.status || '') ? saved.status : 'all',
      priority: ['all', 'low', 'normal', 'high', 'urgent'].includes(saved?.priority || '') ? saved.priority : 'all',
      queue: Number.isInteger(saved?.queue) && saved.queue! > 0 ? saved.queue : undefined,
      unanswered: saved?.unanswered === true,
    })
  }
  return snapshots.get(userId)!
}

/** Selections persist per account/tab; searches stay only in memory. */
export function useInboxFilters(userId: string | number | undefined) {
  const key = String(userId ?? 'anonymous')
  const filters = useSyncExternalStore(callback => {
    listeners.add(callback)
    return () => { listeners.delete(callback) }
  }, () => snapshot(key))
  const setFilters = (patch: Partial<SessionFilters>) => {
    const next = { ...snapshot(key), ...patch }
    snapshots.set(key, next)
    const { search: _search, ...selections } = next
    try { sessionStorage.setItem(`crm-inbox:${key}`, JSON.stringify(selections)) } catch { /* in-memory fallback */ }
    listeners.forEach(notify => notify())
  }
  return [filters, setFilters] as const
}
