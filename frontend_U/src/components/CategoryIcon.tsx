import { Construction, Cylinder, Flame, FolderTree, Gauge, Link2, SlidersHorizontal, Timer, Wind, Wrench, Zap } from 'lucide-react'

export const categoryIcons = {
  flame: { Icon: Flame, label: 'Llama' },
  wind: { Icon: Wind, label: 'Viento' },
  gauge: { Icon: Gauge, label: 'Manómetro' },
  wrench: { Icon: Wrench, label: 'Herramienta' },
  zap: { Icon: Zap, label: 'Electricidad' },
  meter: { Icon: Timer, label: 'Medidor' },
  sliders: { Icon: SlidersHorizontal, label: 'Regulador' },
  link: { Icon: Link2, label: 'Conexión' },
  construction: { Icon: Construction, label: 'Pieza industrial' },
  cylinder: { Icon: Cylinder, label: 'Tanque' },
}

export function CategoryIcon({ name, className }: { name?: string; className?: string }) {
  const Icon = Object.prototype.hasOwnProperty.call(categoryIcons, name ?? '')
    ? categoryIcons[name as keyof typeof categoryIcons].Icon
    : FolderTree
  return <Icon className={className} aria-hidden="true" />
}
