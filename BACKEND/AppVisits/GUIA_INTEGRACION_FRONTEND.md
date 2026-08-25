# Guía de Integración Frontend - AppVisits

## 📱 Integración para React (Frontend)

### **1. Servicio API para Visitas Técnicas**

Crear archivo: `frontend_U/src/services/visits.ts`

```typescript
import api from './api';

// Tipos
export interface ClienteVisita {
  id?: number;
  nombre: string;
  identificacion?: string;
  telefono?: string;
  correo?: string;
  direccion: string;
}

export interface VisitaTecnica {
  id: number;
  numero_tarea: string;
  cliente: ClienteVisita;
  tecnico?: { id: number; nombre_completo: string; usuario: string };
  tipo_tarea: string;
  fecha: string;
  hora: string;
  descripcion?: string;
  estado: 'pendiente' | 'en_proceso' | 'finalizada' | 'cancelada';
  estado_display: string;
  reporte?: ReporteVisita;
  evidencias: EvidenciaFotografica[];
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface ReporteVisita {
  id: number;
  persona_atiende: string;
  equipo: string;
  equipo_display: string;
  ubicacion_equipo: string;
  ubicacion_display: string;
  motivo_servicio: string;
  solucion_realizada: string;
  observaciones?: string;
  recomendaciones?: string;
  valor_servicio?: number;
  metodo_pago?: string;
  firma_cliente?: string;
  inicio_desplazamiento?: string;
  duracion_desplazamiento?: string;
}

export interface EvidenciaFotografica {
  id: number;
  imagen: string;
  descripcion?: string;
  orden: number;
  subida_en: string;
}

// API Service
export const visitsService = {
  // Listar visitas
  async getVisitas(params?: {
    estado?: string;
    tecnico_id?: number;
    fecha?: string;
    mes?: string;
    search?: string;
  }) {
    const response = await api.get('/visits/', { params });
    return response.data;
  },

  // Obtener detalle de visita
  async getVisitaById(id: number) {
    const response = await api.get(`/visits/${id}/`);
    return response.data;
  },

  // Crear visita (admin)
  async createVisita(data: {
    cliente_nombre: string;
    cliente_identificacion?: string;
    cliente_telefono?: string;
    cliente_correo?: string;
    cliente_direccion: string;
    tipo_tarea: string;
    fecha: string;
    hora: string;
    descripcion?: string;
    observaciones_iniciales?: string;
    tecnico_id?: number;
  }) {
    const response = await api.post('/visits/', data);
    return response.data;
  },

  // Actualizar visita (admin)
  async updateVisita(
    id: number,
    data: {
      tipo_tarea?: string;
      fecha?: string;
      hora?: string;
      descripcion?: string;
      observaciones_iniciales?: string;
      estado?: string;
      tecnico?: number;
    }
  ) {
    const response = await api.patch(`/visits/${id}/`, data);
    return response.data;
  },

  // Eliminar visita (admin)
  async deleteVisita(id: number) {
    await api.delete(`/visits/${id}/`);
  },

  // Iniciar visita (técnico)
  async iniciarVisita(id: number) {
    const response = await api.post(`/visits/${id}/iniciar/`);
    return response.data;
  },

  // Finalizar visita y enviar reporte (técnico)
  async finalizarVisita(
    id: number,
    data: {
      persona_atiende: string;
      equipo: string;
      ubicacion_equipo: string;
      motivo_servicio: string;
      solucion_realizada: string;
      observaciones?: string;
      recomendaciones?: string;
      valor_servicio?: number;
      metodo_pago?: string;
      firma_base64?: string;
      duracion_desplazamiento?: string;
    }
  ) {
    const formData = new FormData();
    Object.entries(data).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, String(value));
      }
    });

    const response = await api.post(`/visits/${id}/finalizar/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Subir fotos (técnico)
  async subirFotos(id: number, files: File[]) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('fotos', file);
    });

    const response = await api.post(`/visits/${id}/fotos/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Eliminar foto
  async eliminarFoto(id: number, fotoId: number) {
    await api.delete(`/visits/${id}/fotos/${fotoId}/`);
  },

  // Obtener calendario
  async getCalendario(mes?: string) {
    const response = await api.get('/visits/calendario/', {
      params: mes ? { mes } : undefined,
    });
    return response.data;
  },

  // Descargar PDF (admin)
  async descargarPDF(id: number) {
    const response = await api.get(`/visits/${id}/pdf/`, {
      responseType: 'blob',
    });
    // Crear descarga
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `reporte_visita.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  },

  // Obtener lista de técnicos (admin)
  async getTecnicos() {
    const response = await api.get('/visits/tecnicos/');
    return response.data;
  },
};

export default visitsService;
```

---

### **2. Componente: Crear/Editar Visita (Admin)**

Crear archivo: `frontend_U/src/components/VisitaForm.tsx`

```typescript
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import visitsService from '../services/visits';

interface VisitaFormProps {
  visitaId?: number;
  onSuccess?: () => void;
}

export default function VisitaForm({ visitaId, onSuccess }: VisitaFormProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [tecnicos, setTecnicos] = useState([]);
  const [formData, setFormData] = useState({
    cliente_nombre: '',
    cliente_identificacion: '',
    cliente_telefono: '',
    cliente_correo: '',
    cliente_direccion: '',
    tipo_tarea: 'mantenimiento',
    fecha: '',
    hora: '',
    descripcion: '',
    observaciones_iniciales: '',
    tecnico_id: '',
  });

  useEffect(() => {
    cargarTecnicos();
    if (visitaId) {
      cargarVisita();
    }
  }, [visitaId]);

  const cargarTecnicos = async () => {
    try {
      const data = await visitsService.getTecnicos();
      setTecnicos(data);
    } catch (error) {
      console.error('Error cargando técnicos:', error);
    }
  };

  const cargarVisita = async () => {
    try {
      const visita = await visitsService.getVisitaById(visitaId!);
      setFormData({
        cliente_nombre: visita.cliente.nombre,
        cliente_identificacion: visita.cliente.identificacion || '',
        cliente_telefono: visita.cliente.telefono || '',
        cliente_correo: visita.cliente.correo || '',
        cliente_direccion: visita.cliente.direccion,
        tipo_tarea: visita.tipo_tarea,
        fecha: visita.fecha,
        hora: visita.hora,
        descripcion: visita.descripcion || '',
        observaciones_iniciales: visita.observaciones_iniciales || '',
        tecnico_id: visita.tecnico?.id.toString() || '',
      });
    } catch (error) {
      console.error('Error cargando visita:', error);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (visitaId) {
        await visitsService.updateVisita(visitaId, {
          ...formData,
          tecnico_id: formData.tecnico_id ? parseInt(formData.tecnico_id) : undefined,
        });
      } else {
        await visitsService.createVisita({
          ...formData,
          tecnico_id: formData.tecnico_id ? parseInt(formData.tecnico_id) : undefined,
        });
      }
      onSuccess?.();
      navigate('/visits');
    } catch (error) {
      console.error('Error guardando visita:', error);
      alert('Error al guardar la visita');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-6">
          {visitaId ? 'Editar Visita' : 'Nueva Visita Técnica'}
        </h2>

        {/* Información del Cliente */}
        <fieldset className="border border-gray-300 rounded p-4 mb-6">
          <legend className="text-lg font-semibold px-2">
            Información del Cliente
          </legend>
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              name="cliente_nombre"
              placeholder="Nombre"
              required
              value={formData.cliente_nombre}
              onChange={handleChange}
              className="col-span-2 px-3 py-2 border rounded-md"
            />
            <input
              type="text"
              name="cliente_identificacion"
              placeholder="Identificación"
              value={formData.cliente_identificacion}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            />
            <input
              type="tel"
              name="cliente_telefono"
              placeholder="Teléfono"
              value={formData.cliente_telefono}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            />
            <input
              type="email"
              name="cliente_correo"
              placeholder="Email"
              value={formData.cliente_correo}
              onChange={handleChange}
              className="col-span-2 px-3 py-2 border rounded-md"
            />
            <textarea
              name="cliente_direccion"
              placeholder="Dirección"
              required
              value={formData.cliente_direccion}
              onChange={handleChange}
              className="col-span-2 px-3 py-2 border rounded-md"
              rows={3}
            />
          </div>
        </fieldset>

        {/* Información de la Visita */}
        <fieldset className="border border-gray-300 rounded p-4 mb-6">
          <legend className="text-lg font-semibold px-2">
            Información de la Visita
          </legend>
          <div className="grid grid-cols-2 gap-4">
            <select
              name="tipo_tarea"
              value={formData.tipo_tarea}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            >
              <option value="mantenimiento">Mantenimiento Preventivo</option>
              <option value="instalacion">Instalación</option>
              <option value="reparacion">Reparación</option>
              <option value="revision">Revisión Técnica</option>
              <option value="visita_tecnica">Visita Técnica Perímetro Urbano</option>
              <option value="garantia">Garantía</option>
            </select>
            <select
              name="tecnico_id"
              value={formData.tecnico_id}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            >
              <option value="">Seleccionar técnico</option>
              {tecnicos.map((tecnico) => (
                <option key={tecnico.id} value={tecnico.id}>
                  {tecnico.nombre_completo}
                </option>
              ))}
            </select>
            <input
              type="date"
              name="fecha"
              required
              value={formData.fecha}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            />
            <input
              type="time"
              name="hora"
              required
              value={formData.hora}
              onChange={handleChange}
              className="px-3 py-2 border rounded-md"
            />
            <textarea
              name="descripcion"
              placeholder="Descripción de la tarea"
              value={formData.descripcion}
              onChange={handleChange}
              className="col-span-2 px-3 py-2 border rounded-md"
              rows={3}
            />
            <textarea
              name="observaciones_iniciales"
              placeholder="Observaciones iniciales"
              value={formData.observaciones_iniciales}
              onChange={handleChange}
              className="col-span-2 px-3 py-2 border rounded-md"
              rows={2}
            />
          </div>
        </fieldset>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Guardando...' : 'Guardar Visita'}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-6 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400"
          >
            Cancelar
          </button>
        </div>
      </div>
    </form>
  );
}
```

---

### **3. Componente: Lista de Visitas**

Crear archivo: `frontend_U/src/components/VisitasList.tsx`

```typescript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import visitsService from '../services/visits';

export default function VisitasList() {
  const [visitas, setVisitas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ estado: 'all', search: '' });

  useEffect(() => {
    cargarVisitas();
  }, [filters]);

  const cargarVisitas = async () => {
    setLoading(true);
    try {
      const params = {
        estado: filters.estado !== 'all' ? filters.estado : undefined,
        search: filters.search || undefined,
      };
      const data = await visitsService.getVisitas(
        Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined))
      );
      setVisitas(data);
    } catch (error) {
      console.error('Error cargando visitas:', error);
    } finally {
      setLoading(false);
    }
  };

  const estadoColor = (estado: string) => {
    const colors: { [key: string]: string } = {
      pendiente: 'bg-yellow-100 text-yellow-800',
      en_proceso: 'bg-blue-100 text-blue-800',
      finalizada: 'bg-green-100 text-green-800',
      cancelada: 'bg-red-100 text-red-800',
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Visitas Técnicas</h1>
        <Link
          to="/visits/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          + Nueva Visita
        </Link>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex gap-4">
        <select
          value={filters.estado}
          onChange={(e) => setFilters({ ...filters, estado: e.target.value })}
          className="px-3 py-2 border rounded-md"
        >
          <option value="all">Todos los estados</option>
          <option value="pendiente">Pendiente</option>
          <option value="en_proceso">En Proceso</option>
          <option value="finalizada">Finalizada</option>
          <option value="cancelada">Cancelada</option>
        </select>
        <input
          type="text"
          placeholder="Buscar por cliente, dirección o número de tarea..."
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          className="flex-1 px-3 py-2 border rounded-md"
        />
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-8">Cargando...</div>
      ) : visitas.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No hay visitas</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-6 py-3 text-left">Tarea</th>
                <th className="px-6 py-3 text-left">Cliente</th>
                <th className="px-6 py-3 text-left">Fecha</th>
                <th className="px-6 py-3 text-left">Técnico</th>
                <th className="px-6 py-3 text-left">Estado</th>
                <th className="px-6 py-3 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {visitas.map((visita) => (
                <tr key={visita.id} className="border-t hover:bg-gray-50">
                  <td className="px-6 py-3 font-semibold">#{visita.numero_tarea}</td>
                  <td className="px-6 py-3">{visita.cliente_nombre}</td>
                  <td className="px-6 py-3">
                    {new Date(visita.fecha).toLocaleDateString('es-CO')} {visita.hora}
                  </td>
                  <td className="px-6 py-3">{visita.tecnico_nombre}</td>
                  <td className="px-6 py-3">
                    <span className={`px-3 py-1 rounded-full text-sm ${estadoColor(visita.estado)}`}>
                      {visita.estado_display}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <Link
                      to={`/visits/${visita.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      Ver
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

---

### **4. Componente: Detalle de Visita para Técnico**

Crear archivo: `frontend_U/src/components/VisitaDetail.tsx`

```typescript
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import visitsService from '../services/visits';

export default function VisitaDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [visita, setVisita] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState('view'); // view, iniciar, report

  useEffect(() => {
    cargarVisita();
  }, [id]);

  const cargarVisita = async () => {
    try {
      const data = await visitsService.getVisitaById(parseInt(id!));
      setVisita(data);
    } catch (error) {
      console.error('Error cargando visita:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleIniciar = async () => {
    try {
      const updated = await visitsService.iniciarVisita(parseInt(id!));
      setVisita(updated);
      setAction('view');
      alert('Visita iniciada');
    } catch (error) {
      console.error('Error iniciando visita:', error);
      alert('Error al iniciar visita');
    }
  };

  if (loading) return <div className="text-center py-8">Cargando...</div>;
  if (!visita) return <div className="text-center py-8">Visita no encontrada</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <button
        onClick={() => navigate(-1)}
        className="mb-6 px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400"
      >
        ← Atrás
      </button>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold">Tarea #{visita.numero_tarea}</h1>
            <p className="text-gray-600">
              Estado:{' '}
              <span className="font-semibold">{visita.estado_display}</span>
            </p>
          </div>
          {visita.estado === 'pendiente' && (
            <button
              onClick={handleIniciar}
              className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 font-semibold"
            >
              Iniciar Visita
            </button>
          )}
          {visita.estado === 'en_proceso' && (
            <button
              onClick={() => setAction('report')}
              className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-semibold"
            >
              Enviar Reporte
            </button>
          )}
        </div>

        {/* Información del Cliente */}
        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4">Cliente</h2>
          <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded">
            <div>
              <p className="text-sm text-gray-600">Nombre</p>
              <p className="font-semibold">{visita.cliente.nombre}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Teléfono</p>
              <p className="font-semibold">{visita.cliente.telefono}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Identificación</p>
              <p className="font-semibold">{visita.cliente.identificacion}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Email</p>
              <p className="font-semibold">{visita.cliente.correo}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm text-gray-600">Dirección</p>
              <p className="font-semibold">{visita.cliente.direccion}</p>
            </div>
          </div>
        </section>

        {/* Información de la Visita */}
        <section className="mb-8">
          <h2 className="text-xl font-bold mb-4">Detalles de la Visita</h2>
          <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded">
            <div>
              <p className="text-sm text-gray-600">Tipo de Tarea</p>
              <p className="font-semibold">{visita.tipo_tarea_display}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Fecha y Hora</p>
              <p className="font-semibold">
                {new Date(visita.fecha).toLocaleDateString('es-CO')} {visita.hora}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-sm text-gray-600">Descripción</p>
              <p className="font-semibold">{visita.descripcion || '-'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm text-gray-600">Observaciones Iniciales</p>
              <p className="font-semibold">{visita.observaciones_iniciales || '-'}</p>
            </div>
          </div>
        </section>

        {/* Fotos de Evidencia */}
        {visita.evidencias.length > 0 && (
          <section className="mb-8">
            <h2 className="text-xl font-bold mb-4">Fotos de Evidencia</h2>
            <div className="grid grid-cols-3 gap-4">
              {visita.evidencias.map((evidencia) => (
                <div key={evidencia.id} className="bg-gray-100 rounded overflow-hidden">
                  <img
                    src={evidencia.imagen}
                    alt={evidencia.descripcion}
                    className="w-full h-48 object-cover"
                  />
                  {evidencia.descripcion && (
                    <p className="p-2 text-sm">{evidencia.descripcion}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Reporte */}
        {visita.reporte && (
          <section>
            <h2 className="text-xl font-bold mb-4">Reporte Técnico</h2>
            <div className="grid grid-cols-2 gap-4 bg-green-50 p-4 rounded">
              <div>
                <p className="text-sm text-gray-600">Persona que Atiende</p>
                <p className="font-semibold">{visita.reporte.persona_atiende}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Equipo</p>
                <p className="font-semibold">{visita.reporte.equipo_display}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Ubicación</p>
                <p className="font-semibold">{visita.reporte.ubicacion_display}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Valor Servicio</p>
                <p className="font-semibold">
                  ${visita.reporte.valor_servicio?.toLocaleString('es-CO')}
                </p>
              </div>
              <div className="col-span-2">
                <p className="text-sm text-gray-600">Motivo del Servicio</p>
                <p className="font-semibold">{visita.reporte.motivo_servicio}</p>
              </div>
              <div className="col-span-2">
                <p className="text-sm text-gray-600">Solución Realizada</p>
                <p className="font-semibold">{visita.reporte.solucion_realizada}</p>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
```

---

## 🔑 Consideraciones de Integración

### **1. Autenticación**

El servicio espera que `api` esté configurado con autenticación Bearer:

```typescript
// En services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api', // o tu URL
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

### **2. Manejo de Firmas Digitales**

Para capturar la firma en una app móvil con React, usar una librería como `react-signature-canvas`:

```bash
npm install react-signature-canvas
```

```typescript
import SignatureCanvas from 'react-signature-canvas';

export default function SignaturePad() {
  const signatureRef = useRef<SignatureCanvas>(null);

  const handleSubmit = async () => {
    if (!signatureRef.current?.isEmpty()) {
      const base64 = signatureRef.current.getTrimmedCanvas().toDataURL('image/png');
      await visitsService.finalizarVisita(visitaId, {
        // ... otros datos
        firma_base64: base64,
      });
    }
  };

  return (
    <>
      <SignatureCanvas
        ref={signatureRef}
        penColor="black"
        canvasProps={{ width: 500, height: 200, className: 'border' }}
      />
      <button onClick={handleSubmit}>Finalizar Visita</button>
    </>
  );
}
```

### **3. Captura de Fotos**

Para capturar fotos en navegadores modernos:

```typescript
export default function CameraCapture({ visitaId }: { visitaId: number }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [photos, setPhotos] = useState<File[]>([]);

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
    });
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx?.drawImage(videoRef.current, 0, 0);
      canvasRef.current.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `photo_${Date.now()}.jpg`, {
            type: 'image/jpeg',
          });
          setPhotos([...photos, file]);
        }
      });
    }
  };

  const uploadPhotos = async () => {
    if (photos.length > 0) {
      await visitsService.subirFotos(visitaId, photos);
      setPhotos([]);
    }
  };

  return (
    <>
      <video ref={videoRef} autoPlay width={400} height={300} />
      <canvas ref={canvasRef} width={400} height={300} style={{ display: 'none' }} />
      <button onClick={capturePhoto}>Capturar Foto</button>
      <button onClick={uploadPhotos}>Subir {photos.length} fotos</button>
    </>
  );
}
```

---

**Última actualización:** 2026-08-05
