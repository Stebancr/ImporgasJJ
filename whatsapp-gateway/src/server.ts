import http from 'node:http'
import express from 'express'
import { Server } from 'socket.io'
import { env } from './config/env.js'
import { routes } from './http/routes.js'
import { secureSocketIo } from './realtime/socketio.js'
import { connectionManager } from './whatsapp/connection.js'

const app = express()
app.disable('x-powered-by')
app.use(express.json({ limit: '30mb' }))
app.use(routes)
const server = http.createServer(app)
const io = new Server(server, { path: '/whatsapp-gateway/socket.io', cors: { origin: false } })
secureSocketIo(io)
io.on('connection', socket => {
  console.log(JSON.stringify({ event: 'gateway.realtime_connected', transport: socket.conn.transport.name }))
  socket.emit('gateway.state', connectionManager.state)
  const listener = (state: unknown) => socket.emit('gateway.state', state)
  connectionManager.on('state', listener)
  socket.on('disconnect', reason => {
    connectionManager.off('state', listener)
    console.log(JSON.stringify({ event: 'gateway.realtime_disconnected', reason }))
  })
})
server.listen(env.WHATSAPP_GATEWAY_PORT, '0.0.0.0', () => {
  console.log(JSON.stringify({ event: 'gateway.started', port: env.WHATSAPP_GATEWAY_PORT, environment: env.WHATSAPP_GATEWAY_ENV }))
  void connectionManager.connect().catch(error => console.error(JSON.stringify({ event: 'gateway.connect_failed', error: String(error?.message || error).slice(0, 300) })))
})
