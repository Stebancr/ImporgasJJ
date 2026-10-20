import { useEffect, useRef, useState } from 'react'
export interface AttachmentData {id:number;url:string;name:string;mime_type:string;size:number;state?:string;error?:string;retry_allowed?:boolean}
export default function ChatAttachmentView({attachment:a,loadBlob,retry}:{attachment:AttachmentData;loadBlob:(url:string)=>Promise<Blob>;retry?:()=>Promise<unknown>}){
 const [url,setUrl]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[visible,setVisible]=useState(false)
 const root=useRef<HTMLDivElement>(null),dialog=useRef<HTMLDialogElement>(null),objectUrl=useRef(''),loader=useRef(loadBlob),generation=useRef(0),loading=useRef(false)
 loader.current=loadBlob
 const image=a.mime_type.startsWith('image/'),audio=a.mime_type.startsWith('audio/'),video=a.mime_type.startsWith('video/')
 useEffect(()=>{const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setVisible(true);observer.disconnect()}},{rootMargin:'100px'});if(root.current)observer.observe(root.current);return()=>observer.disconnect()},[])
 useEffect(()=>{generation.current++;setUrl('');setError('');loading.current=false;setBusy(false);return()=>{generation.current++;if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current=''}},[a.id,a.url])
 const load=async()=>{
  if(loading.current)return '';if(url)return url
  const current=generation.current;loading.current=true
  setBusy(true);setError('')
  try{const blob=await loader.current(a.url);if(current!==generation.current)return '';const result=URL.createObjectURL(blob);if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);objectUrl.current=result;setUrl(result);return result}
  catch{if(current===generation.current)setError('No fue posible cargar el archivo. Comprueba tu conexión y vuelve a intentarlo.');return ''}
  finally{if(current===generation.current){loading.current=false;setBusy(false)}}
 }
 useEffect(()=>{if(visible&&image&&a.url)void load()},[visible,a.url])
 const download=async()=>{const target=await load();if(!target)return;const link=document.createElement('a');link.href=target;link.download=a.name||'adjunto';link.click()}
 const retryLoad=async()=>{setError('');if(a.url){await load();return}setBusy(true);try{await retry?.()}catch{setError('No se pudo reintentar la descarga. Inténtalo nuevamente.')}finally{setBusy(false)}}
 return <div ref={root} style={{maxWidth:'100%',minWidth:0,marginTop:8,overflowWrap:'anywhere'}}>
  <div style={{fontSize:12}}>{a.name||'Archivo adjunto'} {a.size>0&&`· ${Math.ceil(a.size/1024)} KB`} {a.mime_type&&`· ${a.mime_type}`}</div>
  {busy&&<div role="status">Cargando archivo…</div>}
  {!a.url&&<div role="status">{a.error||'Archivo pendiente de descarga.'}</div>}
  {url&&image&&<><button type="button" onClick={()=>dialog.current?.showModal()} aria-label={`Ampliar ${a.name}`} style={{display:'block',maxWidth:'100%'}}><img src={url} alt={a.name||'Imagen adjunta'} style={{maxWidth:'100%',maxHeight:300,objectFit:'contain',borderRadius:8}}/></button><dialog ref={dialog} style={{padding:16,border:0,borderRadius:12,maxWidth:'95vw',maxHeight:'90vh',margin:'auto'}}><button autoFocus type="button" aria-label="Cerrar imagen" onClick={()=>dialog.current?.close()}>Cerrar ✕</button><img src={url} alt={a.name} style={{maxWidth:'85vw',maxHeight:'75vh',objectFit:'contain'}}/></dialog></>}
  {url&&audio&&<audio controls preload="metadata" src={url} aria-label={a.name} style={{width:'100%',maxWidth:340}}/>}
  {url&&video&&<video controls preload="metadata" src={url} aria-label={a.name} style={{maxWidth:'100%',maxHeight:300}}/>}
  {a.url&&<div style={{display:'flex',gap:12,flexWrap:'wrap',fontSize:12,marginTop:6}}>{!url&&(audio||video||a.mime_type==='application/pdf')&&<button disabled={busy} onClick={()=>void load()}>Cargar vista previa</button>}{url&&a.mime_type==='application/pdf'&&<a href={url} target="_blank" rel="noopener noreferrer">Ver PDF</a>}<button disabled={busy} onClick={()=>void download()}>Descargar archivo</button></div>}
  {(error||a.retry_allowed)&&<button disabled={busy} onClick={()=>void retryLoad()}>Reintentar archivo</button>}
  {error&&<div role="alert" style={{fontSize:12,color:'#b42318'}}>{error}</div>}
 </div>
}
