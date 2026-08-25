import React, { useEffect, useState } from 'react'
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, RefreshControl, ActivityIndicator,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../store/auth'
import { visitsApi } from '../api/visits'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'
import type { VisitaItem } from '../types'

export default function DashboardScreen() {
  const user = useAuthStore((s) => s.user)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [stats, setStats] = useState({
    pendiente: 0,
    en_proceso: 0,
    finalizada: 0,
    hoy: 0,
  })

  const loadStats = async () => {
    try {
      const visitas = await visitsApi.getAll()
      const today = new Date().toISOString().slice(0, 10)
      setStats({
        pendiente:  visitas.filter((v) => v.estado === 'pendiente').length,
        en_proceso: visitas.filter((v) => v.estado === 'en_proceso').length,
        finalizada: visitas.filter((v) => v.estado === 'finalizada').length,
        hoy:        visitas.filter((v) => v.fecha === today).length,
      })
    } catch {
      // ignore
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { loadStats() }, [])

  const onRefresh = () => { setRefreshing(true); loadStats() }

  const nombre = user?.nombre_completo?.split(' ')[0] ?? user?.usuario ?? 'Técnico'

  const statCards = [
    { label: 'Pendientes',  value: stats.pendiente,  color: Colors.warning,  icon: 'time-outline' },
    { label: 'En Proceso',  value: stats.en_proceso, color: Colors.info,     icon: 'construct-outline' },
    { label: 'Finalizadas', value: stats.finalizada, color: Colors.success,  icon: 'checkmark-circle-outline' },
    { label: 'Hoy',         value: stats.hoy,        color: Colors.primary,  icon: 'today-outline' },
  ] as const

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
    >
      {/* Welcome */}
      <View style={styles.welcome}>
        <View>
          <Text style={styles.greeting}>¡Hola, {nombre}!</Text>
          <Text style={styles.greetingSubtitle}>
            {new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
          </Text>
        </View>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>{nombre[0]?.toUpperCase()}</Text>
        </View>
      </View>

      {/* Stats */}
      <Text style={styles.sectionTitle}>Resumen de visitas</Text>
      {loading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginVertical: 24 }} />
      ) : (
        <View style={styles.statsGrid}>
          {statCards.map((card) => (
            <View key={card.label} style={[styles.statCard, { borderLeftColor: card.color }]}>
              <Ionicons name={card.icon as any} size={26} color={card.color} />
              <Text style={styles.statValue}>{card.value}</Text>
              <Text style={styles.statLabel}>{card.label}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Quick tips */}
      <View style={styles.tipCard}>
        <Ionicons name="information-circle-outline" size={20} color={Colors.info} />
        <Text style={styles.tipText}>
          Ve a <Text style={{ fontWeight: '700' }}>Visitas</Text> para ver las asignadas y completar los formularios técnicos.
        </Text>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.background },
  welcome:      { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: Colors.primary, padding: Spacing.lg, paddingTop: Spacing.xl },
  greeting:     { ...Typography.h2, color: Colors.textInverse },
  greetingSubtitle: { ...Typography.sm, color: 'rgba(255,255,255,0.7)', marginTop: 2, textTransform: 'capitalize' },
  avatarCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: Colors.accent, justifyContent: 'center', alignItems: 'center' },
  avatarText:   { ...Typography.h3, color: Colors.textInverse },
  sectionTitle: { ...Typography.h3, color: Colors.text, margin: Spacing.md, marginBottom: Spacing.sm },
  statsGrid:    { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: Spacing.sm },
  statCard:     { width: '45%', margin: '2.5%', backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, borderLeftWidth: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 6, elevation: 2 },
  statValue:    { ...Typography.h1, color: Colors.text, marginTop: 8 },
  statLabel:    { ...Typography.sm, color: Colors.textSecondary, marginTop: 2 },
  tipCard:      { flexDirection: 'row', alignItems: 'flex-start', gap: 8, backgroundColor: '#e0f2fe', borderRadius: Radius.md, margin: Spacing.md, padding: Spacing.md },
  tipText:      { ...Typography.sm, color: Colors.text, flex: 1 },
})
