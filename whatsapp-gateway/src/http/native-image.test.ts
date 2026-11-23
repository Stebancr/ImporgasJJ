import { describe, expect, it } from 'vitest'
import sharp from 'sharp'
import QRCode from 'qrcode'

describe('native image compatibility after security dependency updates', () => {
  it('loads libvips and transforms a synthetic attachment without a provider', async () => {
    const png = await sharp({ create: { width: 8, height: 6, channels: 3, background: '#123456' } }).png().toBuffer()
    expect((await sharp(png).metadata()).format).toBe('png')
    const jpeg = await sharp(png).resize(4, 3).jpeg().toBuffer()
    const metadata = await sharp(jpeg).metadata()
    expect(metadata.format).toBe('jpeg')
    expect(metadata.width).toBe(4)
    expect(metadata.height).toBe(3)
  })

  it('renders a synthetic QR without connecting a WhatsApp account', async () => {
    const image = await QRCode.toDataURL('synthetic-qa-not-a-whatsapp-login')
    expect(image.startsWith('data:image/png;base64,')).toBe(true)
  })
})
