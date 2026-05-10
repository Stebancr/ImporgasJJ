import './styles/ContactPage.css'
import { useState } from 'react'
import { Phone, Mail, MapPin, Clock, Send, MessageCircle, CheckCircle } from 'lucide-react'
import GoogleMap from '../../components/GoogleMap'

interface ContactForm {
  name: string
  email: string
  phone: string
  subject: string
  message: string
}

function ContactPage() {
  const [form, setForm] = useState<ContactForm>({
    name: '',
    email: '',
    phone: '',
    subject: '',
    message: '',
  })
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500))

    setIsLoading(false)
    setIsSubmitted(true)
  }

  const contactInfo = [
    {
      icon: Phone,
      title: 'Teléfono',
      details: ['+57 300 123 4567', '+57 1 234 5678'],
      color: 'bg-blue-100 text-blue-600',
    },
    {
      icon: Mail,
      title: 'Correo Electrónico',
      details: ['info@gasstore.com', 'ventas@gasstore.com'],
      color: 'bg-green-100 text-green-600',
    },
    {
      icon: MapPin,
      title: 'Dirección',
      details: ['Calle 123 #45-67', 'Bogotá, Colombia'],
      color: 'bg-orange-100 text-orange-600',
    },
    {
      icon: Clock,
      title: 'Horario',
      details: ['Lun - Vie: 8:00 AM - 6:00 PM', 'Sáb: 9:00 AM - 2:00 PM'],
      color: 'bg-purple-100 text-purple-600',
    },
  ]

  const subjects = [
    'Consulta general',
    'Información de productos',
    'Estado de mi pedido',
    'Servicio de instalación',
    'Garantía y devoluciones',
    'Cotización empresarial',
    'Otro',
  ]

  return (
    <div className="contact-page bg-gray-50 min-h-screen">
      {/* Header */}
      <section className="bg-blue-600 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl font-bold mb-4">Contáctanos</h1>
          <p className="text-xl text-blue-100 max-w-2xl mx-auto">
            Estamos aquí para ayudarte. Contáctanos por cualquier consulta y te responderemos lo antes posible.
          </p>
        </div>
      </section>

      {/* Contact Info Cards */}
      <section className="py-12 -mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {contactInfo.map((info) => (
              <div key={info.title} className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className={`w-12 h-12 ${info.color} rounded-lg flex items-center justify-center mb-4`}>
                  <info.icon className="w-6 h-6" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{info.title}</h3>
                {info.details.map((detail, index) => (
                  <p key={index} className="text-gray-600 text-sm">
                    {detail}
                  </p>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Form & Info */}
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12">
            {/* Form */}
            <div className="bg-white rounded-2xl p-8 shadow-sm">
              {isSubmitted ? (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle className="w-10 h-10 text-green-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">¡Mensaje Enviado!</h2>
                  <p className="text-gray-600 mb-6">
                    Gracias por contactarnos. Te responderemos en menos de 24 horas.
                  </p>
                  <button
                    onClick={() => {
                      setIsSubmitted(false)
                      setForm({ name: '', email: '', phone: '', subject: '', message: '' })
                    }}
                    className="text-blue-600 font-medium hover:text-blue-700"
                  >
                    Enviar otro mensaje
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <MessageCircle className="w-5 h-5 text-blue-600" />
                    </div>
                    <h2 className="text-xl font-semibold text-gray-900">Envíanos un Mensaje</h2>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-5">
                    <div className="grid md:grid-cols-2 gap-5">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Nombre Completo
                        </label>
                        <input
                          type="text"
                          name="name"
                          value={form.name}
                          onChange={handleChange}
                          required
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="Tu nombre"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Correo Electrónico
                        </label>
                        <input
                          type="email"
                          name="email"
                          value={form.email}
                          onChange={handleChange}
                          required
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="tu@email.com"
                        />
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-5">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Teléfono
                        </label>
                        <input
                          type="tel"
                          name="phone"
                          value={form.phone}
                          onChange={handleChange}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="+57 300 123 4567"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Asunto
                        </label>
                        <select
                          name="subject"
                          value={form.subject}
                          onChange={handleChange}
                          required
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          <option value="">Seleccionar asunto</option>
                          {subjects.map((subject) => (
                            <option key={subject} value={subject}>
                              {subject}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Mensaje
                      </label>
                      <textarea
                        name="message"
                        value={form.message}
                        onChange={handleChange}
                        required
                        rows={5}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                        placeholder="Escribe tu mensaje aquí..."
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-blue-400"
                    >
                      {isLoading ? (
                        'Enviando...'
                      ) : (
                        <>
                          <Send className="w-5 h-5" />
                          Enviar Mensaje
                        </>
                      )}
                    </button>
                  </form>
                </>
              )}
            </div>

            {/* FAQ */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Preguntas Frecuentes</h2>
              <div className="space-y-4">
                {[
                  {
                    question: '¿Cuáles son los tiempos de entrega?',
                    answer: 'Los tiempos de entrega varían según la ubicación. En Bogotá, la entrega es de 1-2 días hábiles. Para otras ciudades, puede ser de 3-5 días hábiles.',
                  },
                  {
                    question: '¿Ofrecen servicio de instalación?',
                    answer: 'Sí, ofrecemos servicio de instalación profesional para todos nuestros productos. El costo depende del tipo de producto y la ubicación.',
                  },
                  {
                    question: '¿Cuál es la garantía de los productos?',
                    answer: 'Todos nuestros productos tienen garantía de fábrica. Los calentadores tienen hasta 5 años de garantía, y los aires acondicionados hasta 3 años.',
                  },
                  {
                    question: '¿Puedo devolver un producto?',
                    answer: 'Sí, tienes 30 días para devolver un producto sin uso y en su empaque original. Aplican algunas excepciones para productos instalados.',
                  },
                  {
                    question: '¿Aceptan pagos a cuotas?',
                    answer: 'Sí, aceptamos pagos con tarjeta de crédito hasta en 36 cuotas a través de Wompi, y también ofrecemos financiamiento directo.',
                  },
                ].map((faq, index) => (
                  <details key={index} className="bg-white rounded-xl p-4 shadow-sm group">
                    <summary className="font-medium text-gray-900 cursor-pointer list-none flex items-center justify-between">
                      {faq.question}
                      <span className="text-blue-600 group-open:rotate-180 transition-transform">
                        ▼
                      </span>
                    </summary>
                    <p className="mt-3 text-gray-600 leading-relaxed">{faq.answer}</p>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Map Section */}
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">Nuestra Ubicación</h2>
          <GoogleMap />
        </div>
      </section>
    </div>
  )
}

export default ContactPage
