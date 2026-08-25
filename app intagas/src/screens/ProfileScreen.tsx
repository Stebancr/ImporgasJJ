import React from 'react'
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../store/auth'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'

export default function ProfileScreen() {
  const user   = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const handleLogout = () => {
    Alert.alert('Cerrar sesión', '¿Deseas cerrar sesión?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Cerrar sesión', style: 'destructive', onPress: logout },
    ])
  }

  if (!user) return null
  const initials = user.nombre_completo
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()

  const rows: Array<{ icon: string; label: string; value: string | null }> = [
    { icon: 'person-outline',   label: 'Nombre',        value: user.nombre_completo },
    { icon: 'at-outline',       label: 'Usuario',       value: user.usuario },
    { icon: 'mail-outline',     label: 'Correo',        value: user.correo },
    { icon: 'call-outline',     label: 'Teléfono',      value: user.telefono },
    { icon: 'shield-outline',   label: 'Tipo de acceso', value: user.tipo_usuario === 0 ? 'Técnico' : user.tipo_usuario === 1 ? 'Administrador' : 'Super Admin' },
    { icon: 'location-outline', label: 'Sede',          value: user.location_name },
  ]

  return (
    <ScrollView style={styles.container}>
      {/* Avatar */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <Text style={styles.name}>{user.nombre_completo}</Text>
        <Text style={styles.role}>
          {user.tipo_usuario === 0 ? 'Técnico' : 'Administrador'}
        </Text>
      </View>

      {/* Info */}
      <View style={styles.infoCard}>
        {rows.filter((r) => r.value).map((r) => (
          <View key={r.label} style={styles.infoRow}>
            <Ionicons name={r.icon as any} size={20} color={Colors.primary} />
            <View style={styles.infoContent}>
              <Text style={styles.infoLabel}>{r.label}</Text>
              <Text style={styles.infoValue}>{r.value}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Logout */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Ionicons name="log-out-outline" size={20} color={Colors.error} />
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.background },
  header:       { backgroundColor: Colors.primary, alignItems: 'center', paddingVertical: Spacing.xl, paddingHorizontal: Spacing.lg },
  avatar:       { width: 80, height: 80, borderRadius: 40, backgroundColor: Colors.accent, justifyContent: 'center', alignItems: 'center', marginBottom: Spacing.md },
  avatarText:   { ...Typography.h1, color: Colors.textInverse },
  name:         { ...Typography.h2, color: Colors.textInverse, textAlign: 'center' },
  role:         { ...Typography.sm, color: 'rgba(255,255,255,0.7)', marginTop: 4 },
  infoCard:     { margin: Spacing.md, backgroundColor: Colors.surface, borderRadius: Radius.md, overflow: 'hidden', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
  infoRow:      { flexDirection: 'row', alignItems: 'center', gap: 12, padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.divider },
  infoContent:  { flex: 1 },
  infoLabel:    { ...Typography.xs, color: Colors.textSecondary, textTransform: 'uppercase', letterSpacing: 0.5 },
  infoValue:    { ...Typography.body, color: Colors.text, marginTop: 2 },
  logoutBtn:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, margin: Spacing.lg, padding: Spacing.md, borderWidth: 1.5, borderColor: Colors.error, borderRadius: Radius.md },
  logoutText:   { ...Typography.body, color: Colors.error, fontWeight: '600' },
})
