const {chromium}=require('/tmp/crm-ui/node_modules/playwright')
const assert=require('node:assert/strict')
;(async()=>{
 assert.equal(process.env.RECOVERY_ISOLATED_QA,'1','Requires isolated QA flag')
 const browser=await chromium.launch()
 try{
  const page=await browser.newPage()
  const response=await page.request.post('http://backend:8000/auth/token/',{data:{usuario:'qa-recovery-socket',password:'Synthetic-qa-socket-only-942!'}})
  assert.equal(response.status(),200)
  const token=(await response.json()).access
  const result=await page.evaluate(token=>new Promise((resolve,reject)=>{
   const socket=new WebSocket('ws://nginx/ws/crm-chat/',['crm-chat',`jwt.${token}`])
   const timer=setTimeout(()=>{socket.close();reject(new Error('WebSocket timeout'))},10000)
   socket.onerror=()=>{clearTimeout(timer);reject(new Error('WebSocket connection failed'))}
   socket.onopen=()=>socket.send(JSON.stringify({type:'ping'}))
   socket.onmessage=e=>{clearTimeout(timer);socket.close();resolve(JSON.parse(e.data))}
  }),token)
  assert.deepEqual(result,{type:'pong'})
  console.log('PASS real Nginx/ASGI WebSocket handshake, JWT subprotocol, Redis group and ping/pong; isolated synthetic account; no customer messages')
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)})