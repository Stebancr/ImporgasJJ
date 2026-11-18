import type { ApiLocation } from '../services/locations'

export function locationMapUrls(location: ApiLocation, key?: string) {
  const { latitude, longitude, google_place_id } = location
  const lat = Number(latitude)
  const lng = Number(longitude)
  const hasPin = latitude != null && longitude != null && String(latitude).trim() !== '' &&
    String(longitude).trim() !== '' && Number.isFinite(lat) && Number.isFinite(lng) &&
    Math.abs(lat) <= 90 && Math.abs(lng) <= 180
  const address = [location.address, location.city, 'Colombia'].filter(Boolean).join(', ')
  const destination = hasPin ? String(lat) + ',' + String(lng) : address
  const directions = new URLSearchParams({ api: '1', destination })
  if (google_place_id) directions.set('destination_place_id', google_place_id)
  const embedParams = new URLSearchParams({ q: destination, output: 'embed' })
  if (hasPin) embedParams.set('z', '17')
  const embed = key && google_place_id
    ? 'https://www.google.com/maps/embed/v1/place?' + new URLSearchParams({ key, q: 'place_id:' + google_place_id, zoom: '17' })
    : 'https://www.google.com/maps?' + embedParams
  return { embed, directions: 'https://www.google.com/maps/dir/?' + directions }
}
