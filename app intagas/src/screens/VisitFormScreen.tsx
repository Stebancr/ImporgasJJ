import React, { useRef, useState } from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Alert, ActivityIndicator, Image,
  TextInput, Platform,
} from 'react-native'
import { useNavigation, useRoute } from '@react-navigation/native'
import type { NativeStackNavigationProp } from '@react-navigation/native-stack'
import type { RouteProp } from '@react-navigation/native'
import { Ionicons } from '@expo/vector-icons'
import * as ImagePicker from 'expo-image-picker'
import * as ImageManipulator from 'expo-image-manipulator'
import SignatureScreen from 'react-native-signature-canvas'
import { visitsApi } from '../api/visits'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'
import type { ReporteFormData, VisitsStackParamList } from '../types'

type Nav   = NativeStackNavigationProp<VisitsStackParamList, 'VisitForm'>
type Route = RouteProp<VisitsStackParamList, 'VisitForm'>

const EQUIPO_OPTIONS   = ['estufa', 'horno', 'calentador', 'parrilla', 'caldera', 'calefactor', 'otro']
const UBICACION_OPTIONS = ['cocina', 'patio', 'balcon', 'exterior', 'sotano', 'otro']
const PAGO_OPTIONS      = ['efectivo', 'transferencia', 'tarjeta', 'credito', 'otro']

function Label({ children }: { children: string }) {
  return <Text style={styles.fieldLabel}>{children}</Text>
}

function FieldInput({ value, onChange, placeholder, multiline }: {
  value: string; onChange: (v: string) => void; placeholder?: string; multiline?: boolean
}) {
  return (
    <TextInput
      style={[styles.textInput, multiline && styles.textArea]}
      value={value}
      onChangeText={onChange}
      placeholder={placeholder}
      placeholderTextColor={Colors.textDisabled}
      multiline={multiline}
      numberOfLines={multiline ? 4 : 1}
      textAlignVertical={multiline ? 'top' : 'center'}
    />
  )
}

function ChipGroup({ options, value, onChange }: {
  options: string[]; value: string; onChange: (v: string) => void
}) {
  return (
    <View style={styles.chipRow}>
      {options.map((o) => (
        <TouchableOpacity
          key={o}
          style={[styles.chip, value === o && styles.chipActive]}
          onPress={() => onChange(o)}
        >
          <Text style={[styles.chipText, value === o && styles.chipTextActive]}>
            {o.charAt(0).toUpperCase() + o.slice(1)}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  )
}

export default function VisitFormScreen() {
  const navigation = useNavigation<Nav>()
  const route      = useRoute<Route>()
  const { id }     = route.params

  const [form, setForm] = useState<ReporteFormData>({
    persona_atiende: '',
    equipo:          'estufa',
    equipo_otro:     '',
    ubicacion_equipo:'cocina',
    ubicacion_otro:  '',
    motivo_servicio: '',
    solucion_realizada: '',
    observaciones:   '',
    recomendaciones: '',
    valor_servicio:  '',
    metodo_pago:     'efectivo',
  })

  const [photos, setPhotos]           = useState<string[]>([])
  const [firmaBase64, setFirmaBase64] = useState<string | null>(null)
  const [showSignature, setShowSignature] = useState(false)
  const [step, setStep]               = useState(0)
  const [submitting, setSubmitting]   = useState(false)

  const set = (key: keyof ReporteFormData, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  // ── Photos ─────────────────────────────────────────────────────────────────

  const pickPhotos = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync()
      if (status !== 'granted') {
        Alert.alert('Permiso necesario', 'Se necesita acceso a la galería para seleccionar fotos.')
        return
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsMultipleSelection: true,
        quality: 0.8,
      })
      if (!result.canceled && result.assets && result.assets.length > 0) {
        const compressed = await Promise.all(
          result.assets.map((a) =>
            ImageManipulator.manipulateAsync(a.uri, [{ resize: { width: 1200 } }], { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG })
              .then((r) => r.uri)
              .catch(() => a.uri) // Fallback to original if compression fails
          )
        )
        setPhotos((prev) => [...prev, ...compressed].slice(0, 20))
      }
    } catch (error) {
      console.error('Photo picker error:', error)
      Alert.alert('Error', 'No se pudo acceder a la galería. Intenta nuevamente.')
    }
  }

  const takePhoto = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync()
      if (status !== 'granted') {
        Alert.alert('Permiso necesario', 'Se necesita acceso a la cámara para tomar fotos.')
        return
      }
      const result = await ImagePicker.launchCameraAsync({ quality: 0.8 })
      if (!result.canceled && result.assets && result.assets.length > 0) {
        const compressed = await ImageManipulator.manipulateAsync(
          result.assets[0].uri,
          [{ resize: { width: 1200 } }],
          { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG }
        ).catch(() => ({ uri: result.assets[0].uri })) // Fallback to original if compression fails
        
        setPhotos((prev) => [...prev, compressed.uri].slice(0, 20))
      }
    } catch (error) {
      console.error('Camera error:', error)
      Alert.alert('Error', 'No se pudo acceder a la cámara. Intenta nuevamente.')
    }
  }

  const removePhoto = (idx: number) =>
    setPhotos((prev) => prev.filter((_, i) => i !== idx))

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!form.persona_atiende.trim()) {
      Alert.alert('Campo requerido', 'Ingresa el nombre de la persona que atiende.')
      return
    }
    if (!form.motivo_servicio.trim()) {
      Alert.alert('Campo requerido', 'Describe el motivo del servicio.')
      return
    }
    if (!form.solucion_realizada.trim()) {
      Alert.alert('Campo requerido', 'Describe la solución realizada.')
      return
    }
    if (photos.length < 1) {
      Alert.alert('Foto requerida', 'Debes agregar al menos una fotografía.')
      return
    }
    if (!firmaBase64) {
      Alert.alert('Firma requerida', 'Debes capturar la firma del cliente.')
      return
    }

    setSubmitting(true)
    try {
      // Upload photos first
      if (photos.length > 0) {
        await visitsApi.uploadPhotos(id, photos)
      }
      // Submit report + signature
      await visitsApi.finalizar(id, form, firmaBase64)
      Alert.alert('¡Visita finalizada!', 'El reporte fue enviado exitosamente.', [
        { text: 'OK', onPress: () => navigation.navigate('VisitsList') },
      ])
    } catch (e: any) {
      console.error('Submit error:', e)
      const errorMsg = e?.response?.data?.error || 
                       e?.response?.data?.detail || 
                       (e?.response?.data ? JSON.stringify(e.response.data) : null) ||
                       'No se pudo enviar el reporte. Verifica tu conexión.'
      Alert.alert('Error', errorMsg)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Steps ──────────────────────────────────────────────────────────────────

  const steps = ['Datos', 'Servicio', 'Fotos', 'Firma']

  return (
    <View style={styles.container}>
      {/* Step indicator */}
      <View style={styles.stepBar}>
        {steps.map((s, i) => (
          <TouchableOpacity key={s} style={styles.stepItem} onPress={() => setStep(i)}>
            <View style={[styles.stepDot, i <= step && styles.stepDotActive]}>
              <Text style={[styles.stepDotText, i <= step && styles.stepDotTextActive]}>
                {i < step ? '✓' : String(i + 1)}
              </Text>
            </View>
            <Text style={[styles.stepLabel, i === step && styles.stepLabelActive]}>{s}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* ── Step 0: Client + equipo ── */}
        {step === 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Información del cliente</Text>
            <Label>Persona que atiende *</Label>
            <FieldInput value={form.persona_atiende} onChange={(v) => set('persona_atiende', v)} placeholder="Nombre completo" />

            <Label>Equipo a asistir *</Label>
            <ChipGroup options={EQUIPO_OPTIONS} value={form.equipo} onChange={(v) => set('equipo', v)} />
            {form.equipo === 'otro' && (
              <FieldInput value={form.equipo_otro ?? ''} onChange={(v) => set('equipo_otro', v)} placeholder="Especifica el equipo" />
            )}

            <Label>Ubicación del equipo *</Label>
            <ChipGroup options={UBICACION_OPTIONS} value={form.ubicacion_equipo} onChange={(v) => set('ubicacion_equipo', v)} />
            {form.ubicacion_equipo === 'otro' && (
              <FieldInput value={form.ubicacion_otro ?? ''} onChange={(v) => set('ubicacion_otro', v)} placeholder="Especifica la ubicación" />
            )}
          </View>
        )}

        {/* ── Step 1: Service details ── */}
        {step === 1 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Detalles del servicio</Text>
            <Label>Motivo del servicio *</Label>
            <FieldInput multiline value={form.motivo_servicio} onChange={(v) => set('motivo_servicio', v)} placeholder="Describe el problema..." />

            <Label>Solución realizada *</Label>
            <FieldInput multiline value={form.solucion_realizada} onChange={(v) => set('solucion_realizada', v)} placeholder="Describe lo que se hizo..." />

            <Label>Observaciones</Label>
            <FieldInput multiline value={form.observaciones ?? ''} onChange={(v) => set('observaciones', v)} placeholder="Observaciones adicionales..." />

            <Label>Recomendaciones</Label>
            <FieldInput multiline value={form.recomendaciones ?? ''} onChange={(v) => set('recomendaciones', v)} placeholder="Recomendaciones al cliente..." />

            <Label>Valor del servicio</Label>
            <FieldInput value={form.valor_servicio ?? ''} onChange={(v) => set('valor_servicio', v)} placeholder="Ej. 150000" />

            <Label>Método de pago</Label>
            <ChipGroup options={PAGO_OPTIONS} value={form.metodo_pago ?? 'efectivo'} onChange={(v) => set('metodo_pago', v)} />
          </View>
        )}

        {/* ── Step 2: Photos ── */}
        {step === 2 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Evidencias fotográficas</Text>
            <Text style={styles.photoCount}>{photos.length}/20 fotos</Text>

            <View style={styles.photoActions}>
              <TouchableOpacity style={styles.photoBtn} onPress={takePhoto} disabled={photos.length >= 20}>
                <Ionicons name="camera-outline" size={22} color={Colors.primary} />
                <Text style={styles.photoBtnText}>Cámara</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.photoBtn} onPress={pickPhotos} disabled={photos.length >= 20}>
                <Ionicons name="images-outline" size={22} color={Colors.primary} />
                <Text style={styles.photoBtnText}>Galería</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.photoGrid}>
              {photos.map((uri, idx) => (
                <View key={idx} style={styles.photoItem}>
                  <Image source={{ uri }} style={styles.photoThumb} />
                  <TouchableOpacity style={styles.removeBtn} onPress={() => removePhoto(idx)}>
                    <Ionicons name="close-circle" size={20} color={Colors.error} />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
            {photos.length === 0 && (
              <Text style={styles.photoHint}>Se requiere al menos 1 fotografía.</Text>
            )}
          </View>
        )}

        {/* ── Step 3: Signature ── */}
        {step === 3 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Firma del cliente</Text>
            {firmaBase64 ? (
              <View>
                <Image
                  source={{ uri: firmaBase64 }}
                  style={styles.firmaPreview}
                  resizeMode="contain"
                />
                <TouchableOpacity style={styles.clearFirmaBtn} onPress={() => setFirmaBase64(null)}>
                  <Text style={styles.clearFirmaText}>Borrar firma</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View>
                <Text style={styles.firmaHint}>Pide al cliente que firme en el área de abajo:</Text>
                <View style={styles.signatureContainer}>
                  <SignatureScreen
                    onOK={(sig: string) => { setFirmaBase64(sig); setShowSignature(false) }}
                    onEmpty={() => Alert.alert('Firma vacía', 'Por favor firma antes de confirmar.')}
                    descriptionText="Firma aquí"
                    clearText="Limpiar"
                    confirmText="Confirmar"
                    webStyle={`.m-signature-pad { box-shadow: none; border: none; } .m-signature-pad--footer { background: #f8fafc; }`}
                    backgroundColor="white"
                    penColor={Colors.primaryDark}
                  />
                </View>
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {/* Navigation buttons */}
      <View style={styles.navRow}>
        {step > 0 && (
          <TouchableOpacity style={styles.navBtnSecondary} onPress={() => setStep((s) => s - 1)}>
            <Ionicons name="arrow-back" size={18} color={Colors.primary} />
            <Text style={styles.navBtnSecondaryText}>Anterior</Text>
          </TouchableOpacity>
        )}
        {step < steps.length - 1 ? (
          <TouchableOpacity style={styles.navBtnPrimary} onPress={() => setStep((s) => s + 1)}>
            <Text style={styles.navBtnPrimaryText}>Siguiente</Text>
            <Ionicons name="arrow-forward" size={18} color={Colors.textInverse} />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.navBtnPrimary, styles.submitBtn, submitting && styles.disabled]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting
              ? <ActivityIndicator color={Colors.textInverse} />
              : <>
                  <Ionicons name="checkmark-circle-outline" size={20} color={Colors.textInverse} />
                  <Text style={styles.navBtnPrimaryText}>Finalizar Visita</Text>
                </>
            }
          </TouchableOpacity>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.background },
  stepBar:      { flexDirection: 'row', justifyContent: 'space-around', backgroundColor: Colors.surface, paddingVertical: Spacing.sm, borderBottomWidth: 1, borderBottomColor: Colors.border },
  stepItem:     { alignItems: 'center', gap: 4 },
  stepDot:      { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: Colors.border, backgroundColor: Colors.background, justifyContent: 'center', alignItems: 'center' },
  stepDotActive:{ borderColor: Colors.primary, backgroundColor: Colors.primary },
  stepDotText:  { ...Typography.xs, color: Colors.textSecondary, fontWeight: '700' },
  stepDotTextActive: { color: Colors.textInverse },
  stepLabel:    { ...Typography.xs, color: Colors.textSecondary },
  stepLabelActive: { color: Colors.primary, fontWeight: '700' },
  scroll:       { flex: 1 },
  section:      { margin: Spacing.md, backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, gap: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 3, elevation: 1 },
  sectionTitle: { ...Typography.h3, color: Colors.text, marginBottom: Spacing.sm },
  fieldLabel:   { ...Typography.label, color: Colors.textSecondary, textTransform: 'uppercase', marginTop: Spacing.sm, marginBottom: 4, letterSpacing: 0.5 },
  textInput:    { borderWidth: 1.5, borderColor: Colors.border, borderRadius: Radius.md, paddingHorizontal: 12, paddingVertical: 10, ...Typography.body, color: Colors.text, backgroundColor: Colors.background },
  textArea:     { minHeight: 90, paddingTop: 10 },
  chipRow:      { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
  chip:         { paddingHorizontal: 12, paddingVertical: 7, borderRadius: Radius.full, borderWidth: 1.5, borderColor: Colors.border, backgroundColor: Colors.background },
  chipActive:   { borderColor: Colors.primary, backgroundColor: Colors.primary },
  chipText:     { ...Typography.sm, color: Colors.textSecondary },
  chipTextActive: { color: Colors.textInverse, fontWeight: '700' },
  photoCount:   { ...Typography.sm, color: Colors.textSecondary, marginBottom: Spacing.sm },
  photoActions: { flexDirection: 'row', gap: 12, marginBottom: Spacing.md },
  photoBtn:     { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderWidth: 1.5, borderColor: Colors.primary, borderRadius: Radius.md, paddingVertical: 12, backgroundColor: Colors.background },
  photoBtnText: { ...Typography.body, color: Colors.primary, fontWeight: '600' },
  photoGrid:    { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  photoItem:    { position: 'relative' },
  photoThumb:   { width: 90, height: 90, borderRadius: Radius.sm },
  removeBtn:    { position: 'absolute', top: -6, right: -6 },
  photoHint:    { ...Typography.sm, color: Colors.error, textAlign: 'center', marginTop: Spacing.md },
  firmaPreview: { width: '100%', height: 160, borderWidth: 1, borderColor: Colors.border, borderRadius: Radius.md },
  clearFirmaBtn:{ marginTop: 8, alignItems: 'center', padding: 8 },
  clearFirmaText:{ ...Typography.sm, color: Colors.error },
  firmaHint:    { ...Typography.sm, color: Colors.textSecondary, marginBottom: Spacing.sm },
  signatureContainer: { height: 280, borderWidth: 1.5, borderColor: Colors.border, borderRadius: Radius.md, overflow: 'hidden' },
  navRow:       { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, padding: Spacing.md, backgroundColor: Colors.surface, borderTopWidth: 1, borderTopColor: Colors.border },
  navBtnSecondary: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 16, paddingVertical: 12, borderWidth: 1.5, borderColor: Colors.primary, borderRadius: Radius.md },
  navBtnSecondaryText: { ...Typography.body, color: Colors.primary, fontWeight: '600' },
  navBtnPrimary: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, backgroundColor: Colors.primary, borderRadius: Radius.md },
  navBtnPrimaryText: { ...Typography.body, color: Colors.textInverse, fontWeight: '700' },
  submitBtn:    { backgroundColor: Colors.success },
  disabled:     { opacity: 0.6 },
})
