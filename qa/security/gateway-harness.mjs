// Realtime transport only: deliberately never imports Baileys or opens a customer session.
import http from 'node:http'
import { Server } from '/work/node_modules/socket.io/dist/index.js'
import { secureSocketIo } from '/work/dist/realtime/socketio.js'
const server = http.createServer()
const io = new Server(server, { path: '/whatsapp-gateway/socket.io' })
secureSocketIo(io)
server.listen(3001, '0.0.0.0', () => console.log('ISOLATED_REALTIME_READY'))
