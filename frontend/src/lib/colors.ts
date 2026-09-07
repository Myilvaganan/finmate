// Deterministic color assignment: the same name always maps to the same color, everywhere in
// the app (dashboard charts, transaction badges, category legends) -- unlike a positional
// palette index, this stays stable even as lists get filtered, sorted, or paginated.

const CATEGORY_PALETTE = [
  '#2563eb', '#16794e', '#b54708', '#7c3aed', '#0891b2', '#be185d',
  '#65a30d', '#c2410c', '#4f46e5', '#0d9488', '#9333ea', '#ca8a04',
]

const BANK_PALETTE = [
  '#0891b2', '#c2410c', '#4f46e5', '#16794e', '#be185d', '#65a30d', '#7c3aed', '#b54708',
]

function hashString(seed: string): number {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = seed.charCodeAt(i) + ((hash << 5) - hash)
  return Math.abs(hash)
}

export function getCategoryColor(name: string): string {
  return CATEGORY_PALETTE[hashString(name || 'Uncategorized') % CATEGORY_PALETTE.length]
}

export function getBankColor(name: string): string {
  return BANK_PALETTE[hashString(name || 'Other') % BANK_PALETTE.length]
}

/** For a light tinted badge background with the same hue as the solid color. */
export function withAlpha(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
