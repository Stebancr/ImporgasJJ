for(const path of ['/tmp/crm-ui/node_modules/playwright','/tools/node_modules/playwright']){
 const {chromium}=require(path)
 const launch=chromium.launch.bind(chromium)
 chromium.launch=(options={})=>launch({...options,args:[...(options.args||[]),'--host-resolver-rules=MAP crm.localhost nginx, MAP users.localhost nginx, MAP localhost nginx']})
}
for(const stream of [process.stdout,process.stderr]){
 const write=stream.write.bind(stream)
 stream.write=(chunk,...args)=>write(String(chunk).replace(/Bearer\s+[^\s]+/g,'Bearer [redacted]').replace(/eyJ[A-Za-z0-9_.-]+/g,'[synthetic token redacted]'),...args)
}
