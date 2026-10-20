import { useState, type RefObject } from 'react'
import { Button, Dialog, DialogTitle, DialogContent, DialogActions, Stack, TextField } from '@mui/material'
import { Bold, Italic, Link, List, CornerDownLeft } from 'lucide-react'
export default function MessageFormatToolbar({input,value,onChange}:{input:RefObject<HTMLTextAreaElement|null>;value:string;onChange:(value:string)=>void}){
 const [link,setLink]=useState(false),[url,setUrl]=useState(''),[label,setLabel]=useState('')
 const [selection,setSelection]=useState({start:0,end:0})
 const [active,setActive]=useState('')
 const wrap=(before:string,after:string,fallback='texto')=>{
  const el=input.current;if(!el)return
  const a=el.selectionStart,b=el.selectionEnd,text=value.slice(a,b)||fallback
  const toggled=value.slice(Math.max(0,a-before.length),a)===before&&value.slice(b,b+after.length)===after&&!!after
  const result=toggled?value.slice(0,a-before.length)+text+value.slice(b+after.length):value.slice(0,a)+before+text+after+value.slice(b)
  onChange(result);setActive(toggled?'':before)
  requestAnimationFrame(()=>{el.focus();el.setSelectionRange(toggled?a-before.length:a+before.length,(toggled?a-before.length:a+before.length)+text.length)})
 }
 return <><Stack direction="row" sx={{gap:.5,flexWrap:'wrap'}} role="toolbar" aria-label="Formato del mensaje">
  <Button size="small" startIcon={<Bold size={15}/>} aria-pressed={active==='**'} onMouseDown={e=>e.preventDefault()} onClick={()=>wrap('**','**')}>Negrilla</Button>
  <Button size="small" startIcon={<Italic size={15}/>} aria-pressed={active==='_'} onMouseDown={e=>e.preventDefault()} onClick={()=>wrap('_','_')}>Cursiva</Button>
  <Button size="small" startIcon={<List size={15}/>} onMouseDown={e=>e.preventDefault()} onClick={()=>{const el=input.current;if(!el)return;const a=value.lastIndexOf('\n',el.selectionStart-1)+1,b=el.selectionEnd;onChange(value.slice(0,a)+value.slice(a,b).split('\n').map(line=>'- '+line).join('\n')+value.slice(b));el.focus()}}>Lista</Button>
  <Button size="small" startIcon={<CornerDownLeft size={15}/>} onMouseDown={e=>e.preventDefault()} onClick={()=>wrap('\n','','')}>Salto de línea</Button>
  <Button size="small" startIcon={<Link size={15}/>} onMouseDown={e=>e.preventDefault()} onClick={()=>{const el=input.current;if(!el)return;setSelection({start:el.selectionStart,end:el.selectionEnd});setLabel(value.slice(el.selectionStart,el.selectionEnd));setUrl('');setLink(true)}}>Enlace</Button>
 </Stack><Dialog open={link} onClose={()=>setLink(false)} fullWidth maxWidth="xs"><DialogTitle>Insertar enlace</DialogTitle><DialogContent><Stack spacing={2} sx={{pt:1}}><TextField label="Texto del enlace" value={label} onChange={e=>setLabel(e.target.value)}/><TextField autoFocus label="URL completa" value={url} onChange={e=>setUrl(e.target.value)} helperText="Usa una dirección https:// o http://"/></Stack></DialogContent><DialogActions><Button onClick={()=>setLink(false)}>Cancelar</Button><Button disabled={!/^https?:\/\/[^\s<>]+$/i.test(url)} onClick={()=>{const text=label?`${label} (${url})`:url;onChange(value.slice(0,selection.start)+text+value.slice(selection.end));setLink(false);requestAnimationFrame(()=>input.current?.focus())}}>Insertar enlace</Button></DialogActions></Dialog></>
}
