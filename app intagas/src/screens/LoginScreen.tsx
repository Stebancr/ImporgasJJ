import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator,
  ScrollView, Alert, StatusBar,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../store/auth'
import { Colors, Spacing, Radius, Typography } from '../constants/theme'

export default function LoginScreen() {
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)

  const handleLogin = async () => {
    if (!usuario.trim() || !password.trim()) {
      Alert.alert('Error', 'Ingresa tu usuario y contraseña.')
      return
    }
    setLoading(true)
    try {
      await login(usuario.trim(), password)
    } catch (e: any) {
      Alert.alert(
        'Error de acceso',
        e?.response?.data?.detail ?? 'Usuario o contraseña incorrectos.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <StatusBar barStyle="light-content" backgroundColor={Colors.primaryDark} />
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

        {/* Logo / brand */}
        <View style={styles.header}>
          <View style={styles.logoCircle}>
            <Ionicons name="flame" size={48} color={Colors.accent} />
          </View>
          <Text style={styles.brand}>IMPORGAS JJ</Text>
          <Text style={styles.subtitle}>Servicio Técnico</Text>
        </View>

        {/* Card */}
        <View style={styles.card}>
          <Text style={styles.title}>Iniciar sesión</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Usuario</Text>
            <View style={styles.inputRow}>
              <Ionicons name="person-outline" size={18} color={Colors.textSecondary} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Nombre de usuario"
                placeholderTextColor={Colors.textDisabled}
                autoCapitalize="none"
                autoCorrect={false}
                value={usuario}
                onChangeText={setUsuario}
                returnKeyType="next"
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Contraseña</Text>
            <View style={styles.inputRow}>
              <Ionicons name="lock-closed-outline" size={18} color={Colors.textSecondary} style={styles.inputIcon} />
              <TextInput
                style={[styles.input, { flex: 1 }]}
                placeholder="Contraseña"
                placeholderTextColor={Colors.textDisabled}
                secureTextEntry={!showPassword}
                value={password}
                onChangeText={setPassword}
                returnKeyType="done"
                onSubmitEditing={handleLogin}
              />
              <TouchableOpacity onPress={() => setShowPassword((v) => !v)} style={styles.eyeBtn}>
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20} color={Colors.textSecondary}
                />
              </TouchableOpacity>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.loginBtn, loading && styles.loginBtnDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading
              ? <ActivityIndicator color={Colors.textInverse} />
              : <Text style={styles.loginBtnText}>Ingresar</Text>}
          </TouchableOpacity>
        </View>

        <Text style={styles.version}>v1.0.0</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: Colors.primary },
  scroll:      { flexGrow: 1, justifyContent: 'center', padding: Spacing.lg },
  header:      { alignItems: 'center', marginBottom: Spacing.xl },
  logoCircle:  { width: 88, height: 88, borderRadius: 44, backgroundColor: Colors.primaryDark, justifyContent: 'center', alignItems: 'center', marginBottom: Spacing.md },
  brand:       { ...Typography.h1, color: Colors.textInverse },
  subtitle:    { ...Typography.body, color: 'rgba(255,255,255,0.7)', marginTop: 4 },
  card:        { backgroundColor: Colors.surface, borderRadius: Radius.lg, padding: Spacing.lg, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 12, elevation: 6 },
  title:       { ...Typography.h2, color: Colors.text, marginBottom: Spacing.lg },
  inputGroup:  { marginBottom: Spacing.md },
  label:       { ...Typography.label, color: Colors.textSecondary, marginBottom: 6, textTransform: 'uppercase' },
  inputRow:    { flexDirection: 'row', alignItems: 'center', borderWidth: 1.5, borderColor: Colors.border, borderRadius: Radius.md, backgroundColor: Colors.background, paddingHorizontal: Spacing.sm },
  inputIcon:   { marginRight: 6 },
  input:       { flex: 1, paddingVertical: 12, ...Typography.body, color: Colors.text },
  eyeBtn:      { padding: 6 },
  loginBtn:    { marginTop: Spacing.md, backgroundColor: Colors.primary, borderRadius: Radius.md, paddingVertical: 14, alignItems: 'center' },
  loginBtnDisabled: { opacity: 0.6 },
  loginBtnText: { ...Typography.body, fontWeight: '700', color: Colors.textInverse },
  version:     { textAlign: 'center', marginTop: Spacing.lg, color: 'rgba(255,255,255,0.4)', ...Typography.xs },
})
