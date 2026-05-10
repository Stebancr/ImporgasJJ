import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Bot, Sparkles } from 'lucide-react'

interface Message {
  id: number
  text: string
  isBot: boolean
  timestamp: Date
}

const quickReplies = [
  'Horarios de atencion',
  'Servicio de instalacion',
  'Rastrear mi pedido',
  'Hablar con asesor',
]

const botResponses: Record<string, string> = {
  'horarios': 'Nuestro horario de atencion es de Lunes a Viernes de 8:00 AM a 6:00 PM y Sabados de 9:00 AM a 2:00 PM. En que mas puedo ayudarte?',
  'instalación': 'Ofrecemos servicio de instalacion profesional para todos nuestros productos. El costo depende del tipo de producto y la ubicacion. Te gustaria agendar una instalacion?',
  'rastrear': 'Para rastrear tu pedido, ve a la seccion "Seguimiento" en el menu principal e ingresa tu numero de orden. Tambien recibiras notificaciones automaticas por correo y WhatsApp.',
  'asesor': 'Te comunicare con uno de nuestros asesores. Por favor, dejanos tu numero de telefono y te contactaremos en menos de 5 minutos.',
  'default': 'Gracias por contactarnos! Un asesor te respondera pronto. Mientras tanto, hay algo especifico en lo que pueda ayudarte?',
}

function Chatbot() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: 'Hola! Soy el asistente virtual de GasStore. En que puedo ayudarte hoy?',
      isBot: true,
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getBotResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase()
    
    if (lowerMessage.includes('horario')) return botResponses['horarios']
    if (lowerMessage.includes('instalación') || lowerMessage.includes('instalar') || lowerMessage.includes('instalacion')) return botResponses['instalación']
    if (lowerMessage.includes('rastrear') || lowerMessage.includes('pedido') || lowerMessage.includes('seguimiento')) return botResponses['rastrear']
    if (lowerMessage.includes('asesor') || lowerMessage.includes('humano') || lowerMessage.includes('persona')) return botResponses['asesor']
    
    return botResponses['default']
  }

  const handleSend = (text?: string) => {
    const messageText = text || inputValue.trim()
    if (!messageText) return

    const userMessage: Message = {
      id: messages.length + 1,
      text: messageText,
      isBot: false,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    // Simulate bot response delay
    setTimeout(() => {
      const botMessage: Message = {
        id: messages.length + 2,
        text: getBotResponse(messageText),
        isBot: true,
        timestamp: new Date(),
      }
      setIsTyping(false)
      setMessages((prev) => [...prev, botMessage])
    }, 1200)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSend()
    }
  }

  return (
    <>
      {/* Chat Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}`}
      >
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-[#0066FF] to-[#FF6B35] rounded-full blur opacity-75 group-hover:opacity-100 transition-opacity" />
          <div className="relative w-14 h-14 bg-gradient-to-r from-[#0066FF] to-[#0052CC] rounded-full flex items-center justify-center shadow-lg">
            <MessageCircle className="w-6 h-6 text-white" />
          </div>
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#10B981] rounded-full border-2 border-white animate-pulse" />
        </div>
      </button>

      {/* Chat Window */}
      <div 
        className={`fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] transition-all duration-300 ${
          isOpen 
            ? 'opacity-100 translate-y-0 scale-100' 
            : 'opacity-0 translate-y-4 scale-95 pointer-events-none'
        }`}
      >
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E5E7EB]">
          {/* Header */}
          <div className="bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
                  <Bot className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Asistente GasStore</h3>
                  <div className="flex items-center gap-1.5 text-sm text-white/80">
                    <span className="w-2 h-2 bg-[#10B981] rounded-full animate-pulse" />
                    En linea
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)} 
                className="w-10 h-10 hover:bg-white/10 rounded-xl transition-colors flex items-center justify-center"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="h-80 overflow-y-auto p-4 bg-[#F9FAFB]">
            <div className="space-y-4">
              {messages.map((message) => (
                <div 
                  key={message.id} 
                  className={`flex ${message.isBot ? 'justify-start' : 'justify-end'} animate-fade-in`}
                >
                  {message.isBot && (
                    <div className="w-8 h-8 bg-gradient-to-br from-[#0066FF] to-[#0052CC] rounded-lg flex items-center justify-center mr-2 flex-shrink-0">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div 
                    className={`max-w-[75%] px-4 py-3 rounded-2xl ${
                      message.isBot 
                        ? 'bg-white text-[#1A1D21] shadow-sm border border-[#E5E7EB] rounded-tl-none' 
                        : 'bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white rounded-tr-none'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.text}</p>
                    <p className={`text-xs mt-1.5 ${message.isBot ? 'text-[#9CA3AF]' : 'text-white/70'}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
              
              {/* Typing indicator */}
              {isTyping && (
                <div className="flex items-center gap-2 animate-fade-in">
                  <div className="w-8 h-8 bg-gradient-to-br from-[#0066FF] to-[#0052CC] rounded-lg flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-[#E5E7EB]">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-[#9CA3AF] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Quick Replies */}
          <div className="px-4 py-3 bg-white border-t border-[#E5E7EB]">
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
              {quickReplies.map((reply, index) => (
                <button
                  key={index}
                  onClick={() => handleSend(reply)}
                  className="flex-shrink-0 px-3 py-1.5 text-xs bg-[#F3F4F6] text-[#4B5563] rounded-full hover:bg-[#E5E7EB] hover:text-[#1A1D21] transition-colors whitespace-nowrap"
                >
                  {reply}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-4 bg-white border-t border-[#E5E7EB]">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe un mensaje..."
                className="flex-1 px-4 py-3 bg-[#F3F4F6] border-2 border-transparent rounded-xl focus:outline-none focus:border-[#0066FF] focus:bg-white transition-all text-sm"
              />
              <button
                onClick={() => handleSend()}
                disabled={!inputValue.trim()}
                className="w-12 h-12 bg-gradient-to-r from-[#0066FF] to-[#0052CC] text-white rounded-xl flex items-center justify-center hover:shadow-lg hover:shadow-[#0066FF]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default Chatbot
