import { useCallback, useEffect, useState } from 'react'
import { Edit2, Loader2, Star, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { reviewsService, type Review } from '../services/reviews'

interface Props { productId: number; average: number; count: number; onChanged: () => void }

export default function ProductReviews({ productId, average, count, onChanged }: Props) {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try { setReviews((await reviewsService.list(productId)).data) }
    catch (err) { setError(err instanceof Error ? err.message : 'No fue posible cargar las reseñas') }
    finally { setLoading(false) }
  }, [productId])

  useEffect(() => { void load() }, [load])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (editingId) await reviewsService.update(productId, editingId, { rating, comment })
      else await reviewsService.create(productId, { rating, comment })
      setComment(''); setRating(5); setEditingId(null)
      await load(); onChanged()
    } catch (err) { setError(err instanceof Error ? err.message : 'No fue posible guardar la reseña') }
    finally { setSaving(false) }
  }

  const remove = async (review: Review) => {
    if (!window.confirm('¿Deseas eliminar tu reseña?')) return
    await reviewsService.remove(productId, review.id)
    await load(); onChanged()
  }

  return <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
    <aside className="rounded-xl bg-gray-50 p-6 text-center">
      <p className="text-5xl font-bold text-gray-900">{average.toFixed(1)}</p>
      <div className="my-3 flex justify-center">{[1, 2, 3, 4, 5].map(v => <Star key={v} className={`h-5 w-5 ${v <= Math.round(average) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />)}</div>
      <p className="text-gray-600">{count} {count === 1 ? 'reseña' : 'reseñas'}</p>
    </aside>
    <section>
      {isAuthenticated ? <form onSubmit={submit} className="mb-8 rounded-xl border border-gray-200 p-5">
        <h3 className="mb-3 font-semibold text-gray-900">{editingId ? 'Editar mi reseña' : 'Escribir una reseña'}</h3>
        <div className="mb-4 flex gap-1">{[1, 2, 3, 4, 5].map(v => <button key={v} type="button" onClick={() => setRating(v)} aria-label={`${v} estrellas`}><Star className={`h-7 w-7 ${v <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} /></button>)}</div>
        <textarea value={comment} onChange={e => setComment(e.target.value)} minLength={3} maxLength={2000} required rows={4} className="w-full rounded-lg border border-gray-300 p-3 focus:border-blue-600 focus:outline-none" placeholder="Cuéntanos tu experiencia con el producto" />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="mt-3 flex gap-3"><button disabled={saving} className="rounded-lg bg-blue-600 px-5 py-2 text-white disabled:opacity-60">{saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Publicar reseña'}</button>{editingId && <button type="button" onClick={() => { setEditingId(null); setComment(''); setRating(5) }} className="text-gray-600">Cancelar</button>}</div>
      </form> : <div className="mb-8 rounded-xl border border-blue-100 bg-blue-50 p-4 text-blue-900">Puedes consultar las reseñas. Para publicar una, <button onClick={() => navigate(`/login?redirect=/producto/${productId}`)} className="font-semibold underline">inicia sesión</button>.</div>}
      {loading ? <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600" /> : reviews.length === 0 ? <p className="py-8 text-center text-gray-500">Este producto aún no tiene reseñas.</p> : <div className="space-y-4">{reviews.map(review => <article key={review.id} className="rounded-xl border border-gray-200 p-5">
        <div className="flex items-start justify-between gap-4"><div><p className="font-semibold text-gray-900">{review.user_name}</p><div className="my-2 flex">{[1, 2, 3, 4, 5].map(v => <Star key={v} className={`h-4 w-4 ${v <= review.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />)}</div></div>
          {review.is_owner && <div className="flex gap-2"><button onClick={() => { setEditingId(review.id); setRating(review.rating); setComment(review.comment) }} aria-label="Editar reseña" className="p-2 text-blue-600"><Edit2 className="h-4 w-4" /></button><button onClick={() => void remove(review)} aria-label="Eliminar reseña" className="p-2 text-red-600"><Trash2 className="h-4 w-4" /></button></div>}</div>
        <p className="text-gray-700">{review.comment}</p><time className="mt-3 block text-xs text-gray-500">{new Date(review.created_at).toLocaleDateString('es-CO')}</time>
      </article>)}</div>}
    </section>
  </div>
}
