import { useEffect, useState } from 'react'
import { visitsService, type ClienteVisita } from '../../services/admin_visits'

type Props = {
  selectedId?: number
  registering: boolean
  conflicts: number[]
  onSelect: (client: ClienteVisita) => void
  onRegister: () => void
}

const action = 'min-h-10 rounded-md border px-3 py-1 text-sm font-medium hover:bg-muted disabled:opacity-50 focus-visible:outline focus-visible:outline-2'

export default function VisitContactPicker({ selectedId, registering, conflicts, onSelect, onRegister }: Props) {
  const [term, setTerm] = useState('')
  const [results, setResults] = useState<ClienteVisita[]>([])
  const [status, setStatus] = useState('')
  const [query, setQuery] = useState<{ term: string }>()
  const [profile, setProfile] = useState<ClienteVisita>()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState<Awaited<ReturnType<typeof visitsService.getContactHistory>>>()
  const [historyPage, setHistoryPage] = useState(0)
  const [profileStatus, setProfileStatus] = useState('')

  useEffect(() => {
    if (!conflicts.length && !query) return
    let current = true
    setStatus('Buscando…')
    setResults([])
    const request = conflicts.length
      ? Promise.all(conflicts.map(visitsService.getContact))
      : visitsService.searchContacts(query!.term)
    request.then(matches => {
      if (!current) return
      setResults(matches)
      setStatus(matches.length ? (conflicts.length ? 'Selecciona la ficha correcta antes de continuar.' : '') : 'No encontramos clientes.')
    }).catch(() => {
      if (current) setStatus('No se pudieron consultar los clientes. Inténtalo nuevamente.')
    })
    return () => { current = false }
  }, [conflicts, query])

  useEffect(() => {
    setHistory(undefined)
    setProfileStatus('')
    if (!selectedId || !historyPage) return
    let current = true
    setProfileStatus('Cargando historial…')
    visitsService.getContactHistory(selectedId, historyPage).then(data => {
      if (current) { setHistory(data); setProfileStatus('') }
    }).catch(() => { if (current) setProfileStatus('No pudimos cargar el historial.') })
    return () => { current = false }
  }, [selectedId, historyPage])

  return (
    <div className="col-span-full space-y-3 rounded-xl border p-3">
      <label htmlFor="visit-contact-search" className="block text-sm font-medium">Buscar cliente por nombre, teléfono o correo</label>
      <div className="flex flex-wrap gap-2">
        <input id="visit-contact-search" className="min-w-0 flex-1 rounded-md border bg-background px-3" value={term} onChange={e => setTerm(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && term.trim().length >= 2) { e.preventDefault(); setQuery({ term: term.trim() }) } }} maxLength={100} />
        <button type="button" className={action} disabled={term.trim().length < 2} onClick={() => setQuery({ term: term.trim() })}>Buscar</button>
        <button type="button" className={action} aria-pressed={registering} onClick={() => {
          setProfile(undefined); setEditing(false); setHistoryPage(0); onRegister()
        }}>Registrar cliente nuevo</button>
      </div>
      <div role="status" className="text-sm">{status}</div>
      <ul className="space-y-1">
        {results.map(client => <li key={client.id}>
          <button type="button" className={action + ' w-full break-words text-left'} aria-pressed={client.id === selectedId}
            onClick={() => { setProfile(client); setEditing(false); setHistoryPage(1); onSelect(client) }}>
            {client.nombre} · {client.telefono} · {client.correo}
          </button>
        </li>)}
      </ul>
      {registering && <p className="text-sm">Los datos se guardarán al crear la visita.</p>}
      {profile && selectedId === profile.id && <div className="space-y-2">
        <p className="text-sm font-medium">Ficha de {profile.nombre}</p>
        <button type="button" className={action} disabled={saving} onClick={() => setEditing(!editing)}>{editing ? 'Cerrar edición' : 'Editar datos de contacto'}</button>
        {editing && <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-sm">Teléfono de la ficha<input className="block w-full rounded border bg-background p-2" type="tel" value={profile.telefono ?? ''} onChange={e => setProfile({ ...profile, telefono: e.target.value })} /></label>
          <label className="text-sm">Correo de la ficha<input className="block w-full rounded border bg-background p-2" type="email" value={profile.correo ?? ''} onChange={e => setProfile({ ...profile, correo: e.target.value })} /></label>
          <label className="text-sm sm:col-span-2">Dirección de la ficha<input className="block w-full rounded border bg-background p-2" value={profile.direccion} onChange={e => setProfile({ ...profile, direccion: e.target.value })} /></label>
          <button type="button" className={action} disabled={saving} onClick={async () => {
            setSaving(true)
            try {
              const updated = await visitsService.updateContact(selectedId!, { telefono: profile.telefono, correo: profile.correo, direccion: profile.direccion })
              setProfile(updated); setEditing(false); setProfileStatus('Ficha actualizada.')
              onSelect(updated)
            } catch {
              setProfileStatus('No pudimos guardar la ficha. Revisa el formato y las posibles coincidencias.')
            } finally { setSaving(false) }
          }}>Guardar ficha</button>
        </div>}
        <p role="status" className="text-sm">{profileStatus}</p>
        {history && <div className="text-sm">
          <p className="font-medium">Historial de visitas</p>
          {history.results.length ? <ul>{history.results.map(visit => <li key={visit.id}>#{visit.numero_tarea} · {visit.fecha} · {visit.estado.replace(/_/g, ' ')}</li>)}</ul> : <p>Todavía no tiene visitas.</p>}
          {historyPage > 1 && <button type="button" className={action} onClick={() => setHistoryPage(historyPage - 1)}>Anterior</button>}
          {history.next && <button type="button" className={action} onClick={() => setHistoryPage(historyPage + 1)}>Siguiente</button>}
        </div>}
      </div>}
    </div>
  )
}
