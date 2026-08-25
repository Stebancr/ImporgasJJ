import React, { useEffect, useState } from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, Alert, Image,
} from 'react-native'
import { useNavigation, useRoute } from '@react-navigation/native'
import type { NativeStackNavigationProp } from '@react-navigation/native-stack'
import type { RouteProp } from '@react-navigation/native'
import { Ionicons } from '@expo/vector-icons'
import { visitsApi } from '../api/visits'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'
import type { VisitaDetalle, VisitaEstado, VisitsStackParamList } from '../types'

type Nav   = NativeStackNavigationProp<VisitsStackParamList, 'VisitDetail'>
type Route = RouteProp<VisitsStackParamList, 'VisitDetail'>

const ESTADO_CONFIG: Record<VisitaEstado, { label: string; color: string; bg: string }> = {
  pendiente:  { label: 'Pendiente',  color: '#92400e', bg: '#fef3c7' },
  en_proceso: { label: 'En Proceso', color: '#1e40af', bg: '#dbeafe' },
  finalizada: { label: 'Finalizada', color: '#065f46', bg: '#d1fae5' },
  cancelada:  { label: 'Cancelada',  color: '#991b1b', bg: '#fee2e2' },
}

function InfoRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  if (!value) return null
  return (
    <View style={styles.infoRow}>
      <Ionicons name={icon as any} size={16} color={Colors.primary} style={styles.infoIcon} />
      <View>
        <Text style={styles.infoLabel}>{label}</Text>
        <Text style={styles.infoValue}>{value}</Text>
      </View>
    </View>
  )
}

export default function VisitDetailScreen() {
  const navigation = useNavigation<Nav>()
  const route      = useRoute<Route>()
  const { id }     = route.params
  const [visit, setVisit]   = useState<VisitaDetalle | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)

  const loadVisit = async () => {
    setLoading(true)
    try {
      const v = await visitsApi.getById(id)
      if (!v) {
        throw new Error('Visita no encontrada')
      }
      setVisit(v)
    } catch (error) {
      console.error('Error loading visit:', error)
      Alert.alert('Error', 'No se pudo cargar la visita. Verifica tu conexión.')
      navigation.goBack()
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadVisit() }, [id])

  const handleIniciar = async () => {
    if (!visit) return
    Alert.alert(
      'Iniciar visita',
      `¿Deseas iniciar la visita de ${visit.cliente_nombre}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Iniciar',
          onPress: async () => {
            setStarting(true)
            try {
              const updated = await visitsApi.iniciar(visit.id)
              setVisit(updated)
            } catch (e: any) {
              Alert.alert('Error', e?.response?.data?.error ?? 'No se pudo iniciar la visita.')
            } finally {
              setStarting(false)
            }
          },
        },
      ],
    )
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    )
  }
  if (!visit) return null

  const cfg = ESTADO_CONFIG[visit.estado]
  const canStart  = visit.estado === 'pendiente'
  const canSubmit = visit.estado === 'en_proceso'

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Text style={styles.taskNum}>Tarea #{visit.numero_tarea}</Text>
          <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
            <Text style={[styles.badgeText, { color: cfg.color }]}>{cfg.label}</Text>
          </View>
        </View>
        <Text style={styles.clientName}>{visit.cliente_nombre}</Text>
        <Text style={styles.tipoTarea}>{visit.tipo_tarea_display}</Text>
      </View>

      {/* Client info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Datos del cliente</Text>
        <InfoRow icon="person-outline"    label="Nombre"       value={visit.cliente.nombre} />
        <InfoRow icon="card-outline"      label="Identificación" value={visit.cliente.identificacion} />
        <InfoRow icon="call-outline"      label="Teléfono"     value={visit.cliente.telefono} />
        <InfoRow icon="mail-outline"      label="Correo"       value={visit.cliente.correo} />
        <InfoRow icon="location-outline"  label="Dirección"    value={visit.cliente.direccion} />
      </View>

      {/* Visit info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Información de la orden</Text>
        <InfoRow icon="calendar-outline"  label="Fecha"   value={visit.fecha} />
        <InfoRow icon="time-outline"      label="Hora"    value={visit.hora?.slice(0, 5)} />
        <InfoRow icon="person-circle-outline" label="Técnico" value={visit.tecnico?.nombre_completo ?? 'No asignado'} />
        {visit.descripcion ? <InfoRow icon="document-text-outline" label="Descripción" value={visit.descripcion} /> : null}
        {visit.observaciones_iniciales ? <InfoRow icon="chatbox-outline" label="Observaciones iniciales" value={visit.observaciones_iniciales} /> : null}
      </View>

      {/* Report summary if done */}
      {visit.reporte && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Reporte completado</Text>
          <InfoRow icon="person-outline" label="Atendió"   value={visit.reporte.persona_atiende} />
          <InfoRow icon="construct-outline" label="Equipo" value={visit.reporte.equipo_display} />
          <InfoRow icon="home-outline"   label="Ubicación" value={visit.reporte.ubicacion_display} />
          <InfoRow icon="create-outline" label="Motivo"    value={visit.reporte.motivo_servicio} />
          <InfoRow icon="checkmark-done-outline" label="Solución" value={visit.reporte.solucion_realizada} />
          {visit.reporte.valor_servicio && (
            <InfoRow icon="cash-outline" label="Valor" value={`$${Number(visit.reporte.valor_servicio).toLocaleString('es-CO')}`} />
          )}
          {visit.reporte.firma_cliente && (
            <View style={{ marginTop: 10 }}>
              <Text style={styles.infoLabel}>Firma del cliente:</Text>
              <Image source={{ uri: visit.reporte.firma_cliente }} style={styles.firmaImg} resizeMode="contain" />
            </View>
          )}
        </View>
      )}

      {/* Photos */}
      {visit.evidencias.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Evidencias ({visit.evidencias.length})</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.photoScroll}>
            {visit.evidencias.map((e) => (
              <Image key={e.id} source={{ uri: e.imagen }} style={styles.thumbnail} />
            ))}
          </ScrollView>
        </View>
      )}

      {/* Actions */}
      <View style={styles.actions}>
        {canStart && (
          <TouchableOpacity
            style={[styles.actionBtn, styles.startBtn]}
            onPress={handleIniciar}
            disabled={starting}
          >
            {starting
              ? <ActivityIndicator color={Colors.textInverse} />
              : <>
                  <Ionicons name="play-circle-outline" size={22} color={Colors.textInverse} />
                  <Text style={styles.actionBtnText}>Iniciar Visita</Text>
                </>
            }
          </TouchableOpacity>
        )}
        {canSubmit && (
          <TouchableOpacity
            style={[styles.actionBtn, styles.formBtn]}
            onPress={() => navigation.navigate('VisitForm', { id: visit.id })}
          >
            <Ionicons name="clipboard-outline" size={22} color={Colors.textInverse} />
            <Text style={styles.actionBtnText}>Completar Formulario</Text>
          </TouchableOpacity>
        )}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.background },
  center:       { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header:       { backgroundColor: Colors.primary, padding: Spacing.lg },
  headerRow:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  taskNum:      { ...Typography.sm, color: 'rgba(255,255,255,0.7)', fontFamily: 'monospace' },
  badge:        { paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.full },
  badgeText:    { ...Typography.xs, fontWeight: '700' },
  clientName:   { ...Typography.h2, color: Colors.textInverse, marginBottom: 4 },
  tipoTarea:    { ...Typography.sm, color: 'rgba(255,255,255,0.8)' },
  section:      { backgroundColor: Colors.surface, margin: Spacing.md, marginBottom: 0, borderRadius: Radius.md, padding: Spacing.md, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
  sectionTitle: { ...Typography.label, color: Colors.textSecondary, textTransform: 'uppercase', marginBottom: Spacing.sm, letterSpacing: 0.5 },
  infoRow:      { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 10 },
  infoIcon:     { marginTop: 2 },
  infoLabel:    { ...Typography.xs, color: Colors.textSecondary },
  infoValue:    { ...Typography.body, color: Colors.text },
  firmaImg:     { width: 160, height: 80, borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.sm, marginTop: 4 },
  photoScroll:  { marginTop: 8 },
  thumbnail:    { width: 100, height: 100, borderRadius: Radius.sm, marginRight: 8 },
  actions:      { padding: Spacing.lg, gap: 12, marginBottom: Spacing.xl },
  actionBtn:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, paddingVertical: 16, borderRadius: Radius.lg },
  startBtn:     { backgroundColor: Colors.warning },
  formBtn:      { backgroundColor: Colors.primary },
  actionBtnText:{ ...Typography.body, fontWeight: '700', color: Colors.textInverse },
})
