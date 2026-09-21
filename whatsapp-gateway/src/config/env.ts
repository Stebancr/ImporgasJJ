import { z } from 'zod'

export const env = z.object({
  WHATSAPP_GATEWAY_ENV: z.enum(['development', 'production', 'test']).default('development'),
  WHATSAPP_GATEWAY_PORT: z.coerce.number().int().positive().default(3001),
  CRM_API_URL: z.string().url(),
  CRM_INTERNAL_SERVICE_TOKEN: z.string().min(32),
  WHATSAPP_AUTH_DIR: z.string().default('/app/auth'),
  WHATSAPP_MEDIA_DIR: z.string().default('/app/media'),
  WHATSAPP_CONNECTION_ID: z.string().regex(/^[a-zA-Z0-9_-]{3,64}$/).default('primary'),
  WHATSAPP_GATEWAY_PUBLIC_URL: z.string().optional(),
  WHATSAPP_QR_TTL_SECONDS: z.coerce.number().int().min(30).max(300).default(60),
  WHATSAPP_MAX_MEDIA_BYTES: z.coerce.number().int().positive().default(25 * 1024 * 1024),
  WHATSAPP_GATEWAY_REQUEST_MAX_AGE: z.coerce.number().int().min(30).max(900).default(300),
}).parse(process.env)
