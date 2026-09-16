import { Link } from 'react-router-dom'
import { ArrowLeft, ShieldCheck } from 'lucide-react'

const sections = [
  ['Identificación del responsable', 'ImporGas JJ S.A.S, identificada con NIT 900739269-1, es responsable del tratamiento de los datos personales recopilados mediante este sitio y sus canales de atención.'],
  ['Finalidades del tratamiento', 'La información se utiliza para atender consultas, gestionar compras, pedidos, entregas, garantías y solicitudes de servicio; brindar soporte; administrar la relación con clientes; cumplir obligaciones legales y mejorar la experiencia en nuestros canales.'],
  ['Datos que pueden ser recopilados', 'Según la interacción, podemos recopilar datos de identificación y contacto, información necesaria para pedidos y entregas, historial de compras, mensajes enviados por los canales de atención y datos técnicos básicos generados al utilizar el sitio.'],
  ['Tratamiento y uso de la información', 'Los datos se consultan, almacenan, actualizan y utilizan únicamente para las finalidades informadas. Cuando sea necesario para prestar un servicio, podrán intervenir proveedores que deben proteger la información y usarla solo para la labor encomendada.'],
  ['Derechos de los titulares', 'El titular puede conocer, actualizar y rectificar sus datos; solicitar información sobre su uso; pedir prueba de la autorización cuando corresponda; revocar la autorización o solicitar la supresión en los casos permitidos; acceder gratuitamente a sus datos y presentar quejas ante la autoridad competente después de agotar el trámite directo.'],
  ['Atención de consultas y reclamos', 'Las consultas, solicitudes y reclamos relacionados con datos personales pueden enviarse a gerenciaimporgasjj213@gmail.com o comunicarse al 316 526 6734. La solicitud debe permitir identificar al titular, describir claramente la petición y aportar los documentos que resulten necesarios para tramitarla.'],
  ['Seguridad de la información', 'ImporGas JJ S.A.S aplica medidas administrativas y técnicas razonables para proteger la información contra pérdida, acceso, uso, modificación o divulgación no autorizados. Ningún mecanismo ofrece seguridad absoluta, por lo que estas medidas se revisan y ajustan cuando es necesario.'],
  ['Vigencia y modificaciones', 'Esta política rige desde su publicación. Las modificaciones sustanciales serán informadas mediante este sitio o por un canal adecuado antes de aplicar nuevos usos que requieran conocimiento o autorización del titular.'],
]

export default function DataPolicyPage() {
  return <div className="bg-slate-50 min-h-screen overflow-x-hidden">
    <section className="bg-[#001575] text-white px-4 py-14 sm:py-20">
      <div className="max-w-4xl mx-auto">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-white/80 hover:text-white mb-7"><ArrowLeft className="w-4 h-4" />Volver al inicio</Link>
        <div className="flex items-start gap-4"><ShieldCheck className="w-10 h-10 text-[#F58634] shrink-0" /><div><h1 className="text-3xl sm:text-4xl font-bold leading-tight">Política de Tratamiento de Datos Personales</h1><p className="mt-3 text-blue-100">Información sobre el uso y la protección de tus datos personales.</p></div></div>
      </div>
    </section>
    <section className="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-8 lg:p-10 space-y-9">
        <p className="text-slate-600 leading-7">Esta política describe los criterios generales utilizados por ImporGas JJ S.A.S para tratar los datos personales recibidos a través de sus canales comerciales y de servicio.</p>
        {sections.map(([title, body]) => <section key={title}><h2 className="text-xl font-bold text-[#001575] mb-3">{title}</h2><p className="text-slate-600 leading-7 break-words">{body}</p></section>)}
      </div>
    </section>
  </div>
}
