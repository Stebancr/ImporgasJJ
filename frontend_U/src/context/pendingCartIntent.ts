const PENDING_CART_KEY = 'imporgas-pending-cart-v1'
const MAX_AGE_MS = 30 * 60 * 1000

export interface PendingCartIntent {
  productId: number
  quantity: number
  createdAt: number
}

export function savePendingCartIntent(productId: string, quantity: number): boolean {
  const id = Number(productId)
  if (!Number.isInteger(id) || id < 1 || !Number.isInteger(quantity) || quantity < 1 || quantity > 999) return false
  sessionStorage.setItem(PENDING_CART_KEY, JSON.stringify({ productId: id, quantity, createdAt: Date.now() }))
  return true
}

export function readPendingCartIntent(): PendingCartIntent | null {
  try {
    const value = sessionStorage.getItem(PENDING_CART_KEY)
    if (!value) return null
    const intent = JSON.parse(value) as PendingCartIntent
    if (Number.isInteger(intent.productId) && intent.productId > 0 &&
        Number.isInteger(intent.quantity) && intent.quantity > 0 && intent.quantity <= 999 &&
        Number.isFinite(intent.createdAt) && Date.now() - intent.createdAt < MAX_AGE_MS) return intent
  } catch {
    // Invalid or expired intents are discarded below.
  }
  clearPendingCartIntent()
  return null
}

export function clearPendingCartIntent(): void {
  sessionStorage.removeItem(PENDING_CART_KEY)
}
