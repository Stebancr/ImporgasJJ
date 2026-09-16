import { useEffect, useRef } from 'react'

/** Focus and scroll belong to the visible mobile drawer only. */
export function useMobileDrawer(open: boolean, close: () => void) {
  const ref = useRef<HTMLElement>(null)
  const closeRef = useRef(close)
  closeRef.current = close
  useEffect(() => {
    if (!open || window.matchMedia('(min-width: 1024px)').matches) return
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusable = () => Array.from(ref.current?.querySelectorAll<HTMLElement>('a[href], button, input, select, textarea, [tabindex="0"]') || []).filter(el => !el.hasAttribute('disabled') && el.getClientRects().length > 0)
    focusable()[0]?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current()
      if (event.key === 'Tab') {
        const items = focusable()
        const first = items[0], last = items[items.length - 1]
        if (!ref.current?.contains(document.activeElement)) { event.preventDefault(); first?.focus() }
        else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    const media = window.matchMedia('(min-width: 1024px)')
    const onResize = () => { if (media.matches) closeRef.current() }
    document.addEventListener('keydown', onKey)
    media.addEventListener('change', onResize)
    return () => {
      document.body.style.overflow = overflow
      document.removeEventListener('keydown', onKey)
      media.removeEventListener('change', onResize)
      previous?.focus()
    }
  }, [open])
  return ref
}
