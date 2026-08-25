import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator,
} from 'react-native'
import { Calendar, DateData } from 'react-native-calendars'
import { useNavigation } from '@react-navigation/native'
import type { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { Ionicons } from '@expo/vector-icons'
import { visitsApi } from '../api/visits'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'
import type { CalendarioData, CalendarioItem, VisitaEstado, VisitsStackParamList } from '../types'

type Nav = NativeStackNavigationProp<VisitsStackParamList, 'VisitsList'>

const ESTADO_CONFIG: Record<VisitaEstado, string> = {
  pendiente:  Colors.warning,
  en_proceso: Colors.info,
  finalizada: Colors.success,
  cancelada:  Colors.error,
}

export default function CalendarScreen() {
  const navigation = useNavigation<Nav>()
  const [data, setData]           = useState<CalendarioData>({})
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [currentMes, setCurrentMes] = useState(() => new Date().toISOString().slice(0, 7))
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const loadCalendar = useCallback(async (mes: string) => {
    try {
      const d = await visitsApi.getCalendario(mes)
      setData(d)
    } catch {
      setData({})
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { loadCalendar(currentMes) }, [currentMes, loadCalendar])

  const markedDates = Object.entries(data).reduce<Record<string, object>>((acc, [date, visits]) => {
    const dots = visits.slice(0, 3).map((v) => ({ color: ESTADO_CONFIG[v.estado as VisitaEstado] ?? Colors.primary }))
    acc[date] = {
      dots,
      selected: date === selectedDay,
      selectedColor: Colors.primaryLight,
    }
    return acc
  }, {})

  if (selectedDay && !markedDates[selectedDay]) {
    markedDates[selectedDay] = { selected: true, selectedColor: Colors.primaryLight }
  }

  const selectedVisits: CalendarioItem[] = selectedDay ? (data[selectedDay] ?? []) : []

  const onMonthChange = (month: { dateString: string }) => {
    const mes = month.dateString.slice(0, 7)
    if (mes !== currentMes) {
      setCurrentMes(mes)
      setLoading(true)
    }
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadCalendar(currentMes) }} tintColor={Colors.primary} />}
    >
      <Calendar
        markingType="multi-dot"
        markedDates={markedDates}
        onDayPress={(day: DateData) => setSelectedDay(day.dateString)}
        onMonthChange={onMonthChange}
        theme={{
          backgroundColor: Colors.surface,
          calendarBackground: Colors.surface,
          selectedDayBackgroundColor: Colors.primary,
          selectedDayTextColor: Colors.textInverse,
          todayTextColor: Colors.primary,
          dayTextColor: Colors.text,
          textDisabledColor: Colors.textDisabled,
          dotColor: Colors.primary,
          monthTextColor: Colors.text,
          arrowColor: Colors.primary,
          textMonthFontWeight: '700',
          textDayFontSize: 14,
          textMonthFontSize: 16,
        }}
        style={styles.calendar}
        enableSwipeMonths
      />

      {loading && (
        <ActivityIndicator color={Colors.primary} style={{ marginTop: 20 }} />
      )}

      {/* Selected day */}
      {selectedDay && (
        <View style={styles.daySection}>
          <Text style={styles.dayTitle}>
            {new Date(selectedDay + 'T00:00:00').toLocaleDateString('es-CO', {
              weekday: 'long', day: 'numeric', month: 'long',
            })}
          </Text>
          {selectedVisits.length === 0 ? (
            <View style={styles.emptyDay}>
              <Ionicons name="calendar-outline" size={32} color={Colors.textDisabled} />
              <Text style={styles.emptyDayText}>No hay visitas este día</Text>
            </View>
          ) : (
            selectedVisits.map((v) => (
              <TouchableOpacity
                key={v.id}
                style={styles.visitCard}
                onPress={() => navigation.navigate('VisitDetail', { id: v.id })}
                activeOpacity={0.8}
              >
                <View style={[styles.visitDot, { backgroundColor: ESTADO_CONFIG[v.estado as VisitaEstado] ?? Colors.primary }]} />
                <View style={styles.visitInfo}>
                  <Text style={styles.visitClient}>{v.cliente_nombre}</Text>
                  <Text style={styles.visitMeta}>
                    {v.hora.slice(0, 5)} · {v.tipo_tarea}
                  </Text>
                  {v.tecnico_nombre && (
                    <Text style={styles.visitMeta}>
                      <Ionicons name="person-outline" size={11} /> {v.tecnico_nombre}
                    </Text>
                  )}
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.textSecondary} />
              </TouchableOpacity>
            ))
          )}
        </View>
      )}

      {/* Legend */}
      <View style={styles.legend}>
        {Object.entries(ESTADO_CONFIG).map(([estado, color]) => (
          <View key={estado} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: color }]} />
            <Text style={styles.legendText}>{estado.replace('_', ' ')}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.background },
  calendar:     { margin: Spacing.md, borderRadius: Radius.md, elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4 },
  daySection:   { margin: Spacing.md },
  dayTitle:     { ...Typography.h3, color: Colors.text, marginBottom: Spacing.sm, textTransform: 'capitalize' },
  emptyDay:     { alignItems: 'center', paddingVertical: 24, gap: 8 },
  emptyDayText: { ...Typography.sm, color: Colors.textDisabled },
  visitCard:    { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, marginBottom: 8, gap: 10, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
  visitDot:     { width: 10, height: 10, borderRadius: 5 },
  visitInfo:    { flex: 1 },
  visitClient:  { ...Typography.body, color: Colors.text, fontWeight: '600' },
  visitMeta:    { ...Typography.sm, color: Colors.textSecondary, marginTop: 2 },
  legend:       { flexDirection: 'row', flexWrap: 'wrap', gap: 12, margin: Spacing.md, padding: Spacing.md, backgroundColor: Colors.surface, borderRadius: Radius.md },
  legendItem:   { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot:    { width: 10, height: 10, borderRadius: 5 },
  legendText:   { ...Typography.xs, color: Colors.textSecondary, textTransform: 'capitalize' },
})
