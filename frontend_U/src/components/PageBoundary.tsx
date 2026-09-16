import { Component, type ReactNode, Suspense } from 'react'

export function PageLoading() {
  return <div role="status" aria-live="polite" className="min-h-48 p-6 flex items-center justify-center text-muted-foreground">Cargando contenido…</div>
}

export class PageBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <section role="alert" className="mx-auto max-w-lg p-6 space-y-4">
      <h1 className="text-xl font-semibold">No pudimos cargar esta página</h1>
      <p>Comprueba tu conexión y vuelve a intentarlo.</p>
      <button className="min-h-11 rounded-lg bg-primary text-primary-foreground px-4 py-2" onClick={() => window.location.reload()}>Volver a intentar</button>
    </section>
    return <Suspense fallback={<PageLoading />}>{this.props.children}</Suspense>
  }
}
