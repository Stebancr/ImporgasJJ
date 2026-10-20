export const channelTextLimits: Record<string, number> = { ecommerce: 10000, whatsapp_web: 4000, whatsapp: 4000, facebook: 2000, instagram: 1000 }
export const messageTokens = () => /https?:\/\/[^\s<>]+|```[\s\S]+?```|`[^`\n]+`|\*\*[^*\n]+?\*\*|(?<!\w)\*[^*\n]+?\*(?!\w)|(?<!\w)_[^_\n]+?_(?!\w)|(?<!\w)~[^~\n]+?~(?!\w)/g
export function cleanMessage(text: string): string {
  return text.replace(/\r\n/g,'\n').replace(/\\n/g,'\n').replace(/https?\\:\/\//g,s=>s.replace('\\',''))
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi,'')
    .replace(/<br\s*\/?>|<\/(?:p|div|li)>/gi,'\n').replace(/<\/?(?:strong|b)\b[^>]*>/gi,'**')
    .replace(/<\/?(?:em|i)\b[^>]*>/gi,'_').replace(/<[^>]*>/g,'')
    .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'")
    .replace(/<[^>]*>/g,'').replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g,'$1 ($2)').trim()
}
export function channelText(text: string, channel: string): string {
  const convert = (token: string): string => {
    if (/^https?:\/\//.test(token)) return token
    const n=token.startsWith('```')?3:token.startsWith('**')?2:1
    const inner=token.slice(n,-n)
    if (['facebook','instagram'].includes(channel)) return inner.replace(messageTokens(),convert)
    if(token.startsWith('**') && ['whatsapp_web','whatsapp'].includes(channel)) return '*'+inner+'*'
    if(token.startsWith('*') && !token.startsWith('**') && channel==='ecommerce') return '**'+inner+'**'
    return token
  }
  return cleanMessage(text).replace(messageTokens(),convert)
}
