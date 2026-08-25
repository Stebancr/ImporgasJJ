// ─── App theme ─────────────────────────────────────────────────────────────────

export const Colors = {
  primary:      '#1e3a5f',
  primaryLight: '#2d5a9e',
  primaryDark:  '#102244',
  accent:       '#f97316',
  success:      '#16a34a',
  warning:      '#d97706',
  error:        '#dc2626',
  info:         '#0284c7',

  background:   '#f8fafc',
  surface:      '#ffffff',
  border:       '#e2e8f0',
  divider:      '#f1f5f9',

  text:         '#0f172a',
  textSecondary:'#475569',
  textDisabled: '#94a3b8',
  textInverse:  '#ffffff',

  // Estado colors
  pendiente:    '#f59e0b',
  en_proceso:   '#3b82f6',
  finalizada:   '#10b981',
  cancelada:    '#ef4444',
}

export const Spacing = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
  xxl: 48,
}

export const Radius = {
  sm:  6,
  md:  10,
  lg:  14,
  xl:  20,
  full: 9999,
}

export const Typography = {
  h1:   { fontSize: 28, fontWeight: '700' as const, lineHeight: 36 },
  h2:   { fontSize: 22, fontWeight: '700' as const, lineHeight: 30 },
  h3:   { fontSize: 18, fontWeight: '600' as const, lineHeight: 26 },
  body: { fontSize: 15, fontWeight: '400' as const, lineHeight: 22 },
  sm:   { fontSize: 13, fontWeight: '400' as const, lineHeight: 18 },
  xs:   { fontSize: 11, fontWeight: '400' as const, lineHeight: 16 },
  label:{ fontSize: 12, fontWeight: '600' as const, lineHeight: 16 },
}
