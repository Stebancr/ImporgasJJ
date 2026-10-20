import { Fragment, type ReactNode } from 'react'
import { channelText, messageTokens } from './messageFormat'

function inline(text: string, rich: boolean, depth=0): ReactNode {
  const nodes:ReactNode[]=[];let cursor=0
  const regex=rich&&depth<4?messageTokens():/https?:\/\/[^\s<>]+/g
  for(const match of text.matchAll(regex)){
    const at=match.index!,token=match[0];nodes.push(text.slice(cursor,at))
    if(/^https?:\/\//.test(token)){
      const href=token.replace(/[).,;!?]+$/,'')
      nodes.push(<Fragment key={at}><a href={href} target="_blank" rel="noopener noreferrer" style={{color:'inherit',textDecoration:'underline',overflowWrap:'anywhere'}}>{href}</a>{token.slice(href.length)}</Fragment>)
    }else{
      const n=token.startsWith('```')?3:token.startsWith('**')?2:1
      const content=token.slice(n,-n)
      nodes.push(token[0]==='`'?<code key={at}>{content}</code>:token[0]==='*'?<strong key={at} style={{fontWeight:700}}>{inline(content,true,depth+1)}</strong>:token[0]==='_'?<em key={at}>{inline(content,true,depth+1)}</em>:<s key={at}>{inline(content,true,depth+1)}</s>)
    }
    cursor=at+token.length
  }
  nodes.push(text.slice(cursor));return nodes
}
export default function MessageText({text,channel='ecommerce'}:{text:string;channel?:string}){
  const normalized=channelText(text,channel)
  return <div style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',minWidth:0,fontSize:'inherit',lineHeight:1.5}}>{inline(normalized,!['facebook','instagram'].includes(channel))}</div>
}
