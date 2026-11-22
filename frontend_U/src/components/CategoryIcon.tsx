import { createLucideIcon, Construction, Cylinder, Flame, FolderTree, Gauge, Heater, Link2, PenTool, SlidersHorizontal, Timer, Wind, Wrench, Zap } from 'lucide-react'

// Original 24×24 drawings rendered by Lucide: currentColor, round caps, 2px stroke.
const FlowValve = createLucideIcon('FlowValve', [
  ['path', { d: 'M3 9v8l9-4 9 4V9l-9 4Zm9 4V4M8 4h8', key: 'valve' }],
])
const StraightPipe = createLucideIcon('StraightPipe', [
  ['path', { d: 'M2 9h20v6H2ZM5 8v8m14-8v8', key: 'pipe' }],
])
const InstantWaterHeater = createLucideIcon('InstantWaterHeater', [
  ['rect', { x: '5', y: '2', width: '14', height: '17', rx: '2', key: 'body' }],
  ['path', { d: 'M9 19v3m6-3v3M12 5c0 3-3 3-3 6a3 3 0 0 0 6 0c0-1-1-2-1-2s0 2-2 2c-1-1 1-3 0-6Z', key: 'heat' }],
])
const GasMeterRegulator = createLucideIcon('GasMeterRegulator', [
  ['rect', { x: '2', y: '8', width: '11', height: '12', rx: '2', key: 'meter' }],
  ['path', { d: 'M5 8V4h3m3 4V4h6v4M5 12h5m-5 4h2m6-2h3m3 3v3m-2 0h4', key: 'pipes' }],
  ['circle', { cx: '19', cy: '12', r: '4', key: 'control' }],
  ['path', { d: 'm19 12 1-1', key: 'needle' }],
])
const SteamGenerator = createLucideIcon('SteamGenerator', [
  ['path', { d: 'M5 13c-4-3 4-5 0-9m7 9c-4-3 4-5 0-9m7 9c-4-3 4-5 0-9M3 17h18v4H3Z', key: 'steam' }],
])
const PipeFittings = createLucideIcon('PipeFittings', [
  ['path', { d: 'M3 3h6v6h6v6H9v6H3v-6H1V9h2ZM17 3h5v5h-5zM18 17h4v4h-4z', key: 'fittings' }],
])
const HeatedTank = createLucideIcon('HeatedTank', [
  ['rect', { x: '5', y: '4', width: '14', height: '16', rx: '4', key: 'tank' }],
  ['path', { d: 'M9 4V2m6 2V2M8 20v2m8-2v2m-4-15c0 2-3 3-3 6a3 3 0 0 0 6 0c0-2-2-3-3-6Z', key: 'heat' }],
])
const ElectricWaterHeater = createLucideIcon('ElectricWaterHeater', [
  ['rect', { x: '3', y: '4', width: '13', height: '15', rx: '3', key: 'body' }],
  ['path', { d: 'm10 7-4 5h5l-3 4M7 19v3m6-3v3m3-12h2m1-4v4m3-4v4m-4 0h5v3a2.5 2.5 0 0 1-5 0Z', key: 'electric' }],
])
const GasMeter = createLucideIcon('GasMeter', [
  ['rect', { x: '4', y: '7', width: '16', height: '15', rx: '3', key: 'body' }],
  ['path', { d: 'M7 7V2h3m7 5V2h-3M7 11h10v5H7zM10 11v5m4-5v5m-5 3h6', key: 'counter' }],
])
const PressureRegulator = createLucideIcon('PressureRegulator', [
  ['path', { d: 'M2 14h5m10 0h5M2 11v6m20-6v6M7 14a5 5 0 0 1 10 0v3H7Zm5-5V4M8 4h8m-6 16h4', key: 'regulator' }],
])
const ThreadedCoupling = createLucideIcon('ThreadedCoupling', [
  ['path', { d: 'M8 5h8l4 7-4 7H8l-4-7ZM1 9h4m-4 6h4m14-6h4m-4 6h4', key: 'nut' }],
  ['circle', { cx: '12', cy: '12', r: '3', key: 'bore' }],
])
const PipeElbow = createLucideIcon('PipeElbow', [
  ['path', { d: 'M3 2h8v3H3Zm1 3v9a6 6 0 0 0 6 6h9m-9-15v8a1 1 0 0 0 1 1h8m0-3h3v11h-3Z', key: 'elbow' }],
])
const StorageTank = createLucideIcon('StorageTank', [
  ['ellipse', { cx: '12', cy: '5', rx: '7', ry: '3', key: 'top' }],
  ['path', { d: 'M5 5v13c0 4 14 4 14 0V5M8 21v1m8-1v1M9 11h3m-3 4h3m7 1h3', key: 'storage' }],
])

export const categoryIcons = {
  'instant-water-heater': { Icon: InstantWaterHeater, label: 'Calentador de paso' },
  'gas-meter-regulator': { Icon: GasMeterRegulator, label: 'Medidor y regulador' },
  heater: { Icon: Heater, label: 'Calefactor' },
  wrench: { Icon: Wrench, label: 'Repuestos' },
  steam: { Icon: SteamGenerator, label: 'Generador de vapor' },
  'pipe-fittings': { Icon: PipeFittings, label: 'Conjunto de conexiones' },
  'heated-tank': { Icon: HeatedTank, label: 'Depósito con calentamiento' },
  'electric-water-heater': { Icon: ElectricWaterHeater, label: 'Calentador eléctrico' },
  zap: { Icon: Zap, label: 'Electricidad' },
  'gas-meter': { Icon: GasMeter, label: 'Contador de gas' },
  gauge: { Icon: Gauge, label: 'Manómetro' },
  'pressure-regulator': { Icon: PressureRegulator, label: 'Regulador de presión' },
  'threaded-coupling': { Icon: ThreadedCoupling, label: 'Acople roscado' },
  'pipe-elbow': { Icon: PipeElbow, label: 'Codo de tubería' },
  'storage-tank': { Icon: StorageTank, label: 'Tanque de almacenamiento' },
  // Preserve stored keys for other categories without rewriting the database.
  valve: { Icon: FlowValve, label: 'Válvula' },
  pipe: { Icon: StraightPipe, label: 'Tubería' },
  'folder-tree': { Icon: FolderTree, label: 'Categoría (respaldo)' },
  'pen-tool': { Icon: PenTool, label: 'Herramientas' },
  flame: { Icon: Flame, label: 'Llama' },
  wind: { Icon: Wind, label: 'Viento' },
  meter: { Icon: Timer, label: 'Medidor genérico' },
  sliders: { Icon: SlidersHorizontal, label: 'Controles' },
  link: { Icon: Link2, label: 'Enlace' },
  construction: { Icon: Construction, label: 'Construcción' },
  cylinder: { Icon: Cylinder, label: 'Cilindro' },
} as const

export const categoryIconBySlug = {
  calentadores: 'instant-water-heater',
  reguladores: 'gas-meter-regulator',
  calefactores: 'heater',
  repuestos: 'wrench',
  'generadores-de-vapor': 'steam',
  'accesorios-laton': 'pipe-fittings',
  'calentadores-de-acumulacion': 'heated-tank',
  'calentadores-electricos': 'electric-water-heater',
  electricidad: 'zap',
  'medidor-de-gas': 'gas-meter',
  manometro: 'gauge',
  'regulador-de-gas': 'pressure-regulator',
  laton: 'threaded-coupling',
  galvanizado: 'pipe-elbow',
  'tanque-de-acumulacion': 'storage-tank',
} as const satisfies Record<string, keyof typeof categoryIcons>

export function resolveCategoryIcon(slug?: string, name?: string, iconKey?: string | null) {
  if (iconKey && Object.prototype.hasOwnProperty.call(categoryIcons, iconKey)) return iconKey as keyof typeof categoryIcons
  if (Object.prototype.hasOwnProperty.call(categoryIconBySlug, slug ?? '')) {
    return categoryIconBySlug[slug as keyof typeof categoryIconBySlug]
  }
  return Object.prototype.hasOwnProperty.call(categoryIcons, name ?? '') ? name as keyof typeof categoryIcons : undefined
}

export function CategoryIcon({ slug, name, iconKey, className }: { slug?: string; name?: string; iconKey?: string | null; className?: string }) {
  const key = resolveCategoryIcon(slug, name, iconKey)
  const Icon = key ? categoryIcons[key].Icon : FolderTree
  return <Icon className={className} aria-hidden="true" focusable="false" />
}
