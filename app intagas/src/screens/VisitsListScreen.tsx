import React, { useEffect, useState, useCallback } from 'react'
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  TextInput, RefreshControl, ActivityIndicator,
} from 'react-native'
import { useNavigation } from '@react-navigation/native'
import type { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { Ionicons } from '@expo/vector-icons'
import { visitsApi } from '../api/visits'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'
import type { VisitaItem, VisitaEstado, VisitsStackParamList } from '../types'

type Nav = NativeStackNavigationProp<VisitsStackParamList, 'VisitsList'>

const ESTADO_CONFIG: Record<VisitaEstado, { label: string; color: string; bg: string }> = {
  pendiente:  { label: 'Pendiente',  color: '#92400e', bg: '#fef3c7' },
  en_proceso: { label: 'En Proceso', color: '#1e40af', bg: '#dbeafe' },
  finalizada: { label: 'Finalizada', color: '#065f46', bg: '#d1fae5' },
  cancelada:  { label: 'Cancelada',  color: '#991b1b', bg: '#fee2e2' },
}

const ESTADO_FILTERS = [
  { key: 'all',        label: 'Todas' },
  { key: 'pendiente',  label: 'Pendientes' },
  { key: 'en_proceso', label: 'En Proceso' },
  { key: 'finalizada', label: 'Finalizadas' },
]

export default function VisitsListScreen() {
  const navigation = useNavigation<Nav>()
  const [visits, setVisits]         = useState<VisitaItem[]>([])
  const [filtered, setFiltered]     = useState<VisitaItem[]>([])
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch]         = useState('')
  const [estadoFilter, setEstadoFilter] = useState('all')

  const loadVisits = useCallback(async () => {
    try {
      const data = await visitsApi.getAll()
      setVisits(data)
    } catch {
      setVisits([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { loadVisits() }, [loadVisits])

  useEffect(() => {
    let result = visits
    if (estadoFilter !== 'all') result = result.filter((v) => v.estado === estadoFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (v) => v.cliente_nombre.toLowerCase().includes(q) ||
               v.cliente_direccion.toLowerCase().includes(q) ||
               v.numero_tarea.includes(q),
      )
    }
    setFiltered(result)
  }, [visits, search, estadoFilter])

  const onRefresh = () => { setRefreshing(true); loadVisits() }

  const renderItem = ({ item }: { item: VisitaItem }) => {
    const cfg = ESTADO_CONFIG[item.estado]
    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('VisitDetail', { id: item.id })}
        activeOpacity={0.8}
      >
        <View style={styles.cardHeader}>
          <Text style={styles.taskNum}>#{item.numero_tarea}</Text>
          <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
            <Text style={[styles.badgeText, { color: cfg.color }]}>{cfg.label}</Text>
          </View>
        </View>
        <Text style={styles.clientName}>{item.cliente_nombre}</Text>
        <View style={styles.cardRow}>
          <Ionicons name="location-outline" size={14} color={Colors.textSecondary} />
          <Text style={styles.cardRowText} numberOfLines={1}>{item.cliente_direccion}</Text>
        </View>
        <View style={styles.cardRow}>
          <Ionicons name="calendar-outline" size={14} color={Colors.textSecondary} />
          <Text style={styles.cardRowText}>{item.fecha}</Text>
          <Ionicons name="time-outline" size={14} color={Colors.textSecondary} style={{ marginLeft: 8 }} />
          <Text style={styles.cardRowText}>{item.hora?.slice(0, 5)}</Text>
        </View>
        <View style={styles.cardRow}>
          <Ionicons name="construct-outline" size={14} color={Colors.textSecondary} />
          <Text style={styles.cardRowText}>{item.tipo_tarea_display}</Text>
        </View>
        {item.tiene_reporte && (
          <View style={styles.reportBadge}>
            <Ionicons name="checkmark-circle" size={14} color={Colors.success} />
            <Text style={[styles.cardRowText, { color: Colors.success }]}> Reporte completado</Text>
          </View>
        )}
      </TouchableOpacity>
    )
  }

  return (
    <View style={styles.container}>
      {/* Search */}
      <View style={styles.searchRow}>
        <Ionicons name="search-outline" size={18} color={Colors.textSecondary} style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar por cliente, dirección o tarea..."
          placeholderTextColor={Colors.textDisabled}
          value={search}
          onChangeText={setSearch}
        />
      </View>

      {/* Estado filter chips */}
      <View style={styles.chipRow}>
        {ESTADO_FILTERS.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.chip, estadoFilter === f.key && styles.chipActive]}
            onPress={() => setEstadoFilter(f.key)}
          >
            <Text style={[styles.chipText, estadoFilter === f.key && styles.chipTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(v) => String(v.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="clipboard-outline" size={48} color={Colors.textDisabled} />
              <Text style={styles.emptyText}>No hay visitas para mostrar</Text>
            </View>
          }
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: Colors.background },
  searchRow:   { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.surface, margin: Spacing.md, marginBottom: Spacing.sm, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.border, paddingHorizontal: Spacing.sm },
  searchIcon:  { marginRight: 6 },
  searchInput: { flex: 1, paddingVertical: 10, ...Typography.body, color: Colors.text },
  chipRow:     { flexDirection: 'row', paddingHorizontal: Spacing.md, gap: 8, marginBottom: Spacing.sm },
  chip:        { paddingHorizontal: 12, paddingVertical: 6, borderRadius: Radius.full, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border },
  chipActive:  { backgroundColor: Colors.primary, borderColor: Colors.primary },
  chipText:    { ...Typography.sm, color: Colors.textSecondary },
  chipTextActive: { color: Colors.textInverse, fontWeight: '600' },
  list:        { padding: Spacing.md, gap: 10 },
  card:        { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.07, shadowRadius: 6, elevation: 2 },
  cardHeader:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  taskNum:     { ...Typography.xs, color: Colors.textSecondary, fontFamily: 'monospace' },
  badge:       { paddingHorizontal: 8, paddingVertical: 3, borderRadius: Radius.full },
  badgeText:   { ...Typography.xs, fontWeight: '600' },
  clientName:  { ...Typography.h3, color: Colors.text, marginBottom: 8 },
  cardRow:     { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  cardRowText: { ...Typography.sm, color: Colors.textSecondary, flex: 1 },
  reportBadge: { flexDirection: 'row', alignItems: 'center', marginTop: 6, paddingTop: 6, borderTopWidth: 1, borderTopColor: Colors.divider },
  empty:       { alignItems: 'center', paddingTop: 60, gap: 12 },
  emptyText:   { ...Typography.body, color: Colors.textDisabled },
})
