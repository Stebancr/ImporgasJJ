import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { env } from '../config/env.js'

type OutboundResult = { external_message_id: string; status: string }

function statePath(): string {
  return path.join(env.WHATSAPP_AUTH_DIR, `outbound-${env.WHATSAPP_CONNECTION_ID}.json`)
}

export async function loadOutboundResults(): Promise<Map<string, OutboundResult>> {
  try {
    const parsed = JSON.parse(await readFile(statePath(), 'utf8')) as Record<string, OutboundResult>
    return new Map(Object.entries(parsed).slice(-5000))
  } catch {
    return new Map()
  }
}

export async function saveOutboundResults(values: Map<string, OutboundResult>): Promise<void> {
  const file = statePath()
  await mkdir(path.dirname(file), { recursive: true, mode: 0o700 })
  const temporary = `${file}.tmp`
  await writeFile(temporary, JSON.stringify(Object.fromEntries(values)), { mode: 0o600 })
  await rename(temporary, file)
}
