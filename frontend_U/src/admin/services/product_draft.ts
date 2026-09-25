export interface ProductDraft {
  formData: {
    name: string
    description: string
    price: string
    original_price: string
    category: string
    brand: string
    is_available: boolean
    is_featured: boolean
  }
  newSpecRows: { name: string; value: string }[]
  stockValues: Record<number, string>
}

const prefix = 'admin-product-draft-v1:'
const imageWrites = new Map<string, Promise<void>>()

export function productDraftKey(): string {
  let userId = 'unknown'
  try { userId = String(JSON.parse(localStorage.getItem('adminUser') || '{}').id ?? 'unknown') } catch { /* Ignore invalid user cache. */ }
  return `${prefix}${userId}`
}

export function readProductDraft(key: string): ProductDraft | null {
  try {
    const value = localStorage.getItem(key)
    if (!value) return null
    const draft = JSON.parse(value) as ProductDraft
    if (!draft.formData || !Array.isArray(draft.newSpecRows) || !draft.stockValues) return null
    return draft
  } catch { return null }
}

export function saveProductDraft(key: string, draft: ProductDraft): void {
  try { localStorage.setItem(key, JSON.stringify(draft)) } catch { /* Storage may be unavailable. */ }
}

function openDraftDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('imporgas-admin-drafts', 1)
    request.onupgradeneeded = () => request.result.createObjectStore('product-images')
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function readDraftImages(key: string): Promise<File[]> {
  try {
    const db = await openDraftDatabase()
    return await new Promise<File[]>((resolve, reject) => {
      const transaction = db.transaction('product-images', 'readonly')
      const request = transaction.objectStore('product-images').get(key)
      request.onsuccess = () => resolve(Array.isArray(request.result) ? request.result : [])
      request.onerror = () => reject(request.error)
      transaction.oncomplete = () => db.close()
    })
  } catch { return [] }
}

async function writeDraftImages(key: string, images: File[]): Promise<void> {
  try {
    const db = await openDraftDatabase()
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction('product-images', 'readwrite')
      transaction.objectStore('product-images').put(images, key)
      transaction.oncomplete = () => { db.close(); resolve() }
      transaction.onerror = () => { db.close(); reject(transaction.error) }
    })
  } catch { /* Keep the text draft even when browser image storage is unavailable. */ }
}

export function saveDraftImages(key: string, images: File[]): Promise<void> {
  const next = (imageWrites.get(key) ?? Promise.resolve()).then(() => writeDraftImages(key, images))
  imageWrites.set(key, next)
  void next.finally(() => { if (imageWrites.get(key) === next) imageWrites.delete(key) })
  return next
}

export async function clearProductDraft(key: string): Promise<void> {
  localStorage.removeItem(key)
  await imageWrites.get(key)
  try {
    const db = await openDraftDatabase()
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction('product-images', 'readwrite')
      transaction.objectStore('product-images').delete(key)
      transaction.oncomplete = () => { db.close(); resolve() }
      transaction.onerror = () => { db.close(); reject(transaction.error) }
    })
  } catch { /* Text draft is already cleared. */ }
}
