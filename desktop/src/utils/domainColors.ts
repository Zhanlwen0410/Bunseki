const DOMAIN_COLORS: Record<string, string> = {
  A: '#1565c0',
  B: '#e91e63',
  C: '#7b1fa2',
  E: '#ff6f00',
  F: '#2e7d32',
  G: '#c62828',
  H: '#6d4c41',
  I: '#00838f',
  K: '#f9a825',
  L: '#4caf50',
  M: '#1e88e5',
  N: '#5c6bc0',
  O: '#8d6e63',
  P: '#00897b',
  Q: '#ec407a',
  S: '#e64a19',
  T: '#7cb342',
  W: '#0288d1',
  X: '#455a64',
  Y: '#ab47bc',
  Z: '#78909c',
}

const FALLBACK_COLOR = '#9e9e9e'

export function getDomainColor(code: string): string {
  const prefix = (code || 'Z')[0].toUpperCase()
  return DOMAIN_COLORS[prefix] ?? FALLBACK_COLOR
}

export function getDomainColors(): Record<string, string> {
  return { ...DOMAIN_COLORS }
}
