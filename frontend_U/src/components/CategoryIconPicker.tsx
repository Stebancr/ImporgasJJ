import { useId, useRef, useState } from 'react'
import { CategoryIcon, categoryIcons } from './CategoryIcon'

const normalized = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

export function CategoryIconPicker({ value, onChange, error }: { value: string; onChange: (key: string) => void; error?: string }) {
  const id = useId()
  const grid = useRef<HTMLDivElement>(null)
  const [search, setSearch] = useState('')
  const entries = Object.entries(categoryIcons).filter(([key, item]) => normalized(key + ' ' + item.label).includes(normalized(search)))
  const selected = Object.prototype.hasOwnProperty.call(categoryIcons, value) ? categoryIcons[value as keyof typeof categoryIcons] : undefined
  const focusKey = entries.some(([key]) => key === value) ? value : entries[0]?.[0]
  return <fieldset className="min-w-0 space-y-3">
    <legend className="text-sm font-medium">Icono de categoría</legend>
    <label className="sr-only" htmlFor={id}>Buscar iconos</label>
    <input id={id} type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Buscar por nombre o clave…" className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-2 focus-visible:outline-ring" />
    <div className="flex items-center gap-3 rounded-md border border-input p-3" aria-live="polite">
      <CategoryIcon iconKey={value} className="h-7 w-7 shrink-0 text-primary" />
      <span className="min-w-0 text-sm"><span className="block font-medium">{selected?.label ?? 'Icono de respaldo'}</span><code className="break-all text-xs text-muted-foreground">{selected ? value : 'folder-tree'}</code></span>
    </div>
    <div ref={grid} role="radiogroup" aria-label="Iconos disponibles" aria-describedby={error ? id + '-error' : undefined} className="grid max-h-52 grid-cols-3 gap-2 overflow-y-auto rounded-md border border-input p-2 sm:grid-cols-4">
      {entries.map(([key, item]) => <button key={key} type="button" role="radio" aria-checked={key === value} aria-label={item.label + ' — ' + key} tabIndex={key === focusKey ? 0 : -1} title={item.label + ' (' + key + ')'}
        className={`flex min-w-0 flex-col items-center gap-1 rounded-md border p-2 text-center transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${key === value ? 'border-primary bg-primary/10 text-primary' : 'border-transparent hover:border-input hover:bg-muted'}`}
        onClick={() => onChange(key)} onKeyDown={event => {
          if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
          event.preventDefault()
          const index = entries.findIndex(([entry]) => entry === key)
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? entries.length - 1 : (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + entries.length) % entries.length
          onChange(entries[next][0])
          grid.current?.querySelectorAll<HTMLButtonElement>('button')[next]?.focus()
        }}>
        <CategoryIcon iconKey={key} className="h-6 w-6 shrink-0" /><span className="w-full truncate text-xs">{item.label}</span><code className="w-full truncate text-[10px]">{key}</code>
        {key === value && <span className="sr-only">Seleccionado</span>}
      </button>)}
    </div>
    {entries.length === 0 && <p role="status" className="text-sm text-muted-foreground">No hay iconos que coincidan. Prueba otro nombre.</p>}
    {error && <p id={id + '-error'} role="alert" className="text-sm text-destructive">{error}</p>}
  </fieldset>
}
