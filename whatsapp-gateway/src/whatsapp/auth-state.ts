import { chmod, mkdir, rm } from 'node:fs/promises'
import path from 'node:path'
import { useMultiFileAuthState } from '@whiskeysockets/baileys'
import { env } from '../config/env.js'

export function connectionAuthDir(connectionId: string): string {
  return path.join(env.WHATSAPP_AUTH_DIR, connectionId)
}

export async function loadAuthState(connectionId: string) {
  const directory = connectionAuthDir(connectionId)
  await mkdir(directory, { recursive: true, mode: 0o700 })
  await chmod(directory, 0o700)
  return useMultiFileAuthState(directory)
}

export async function clearAuthState(connectionId: string): Promise<void> {
  await rm(connectionAuthDir(connectionId), { recursive: true, force: true })
}
