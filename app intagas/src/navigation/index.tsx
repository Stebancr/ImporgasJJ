import React, { useEffect } from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { ActivityIndicator, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'

import { useAuthStore } from '../store/auth'
import { setLogoutCallback } from '../api/client'
import { Colors } from '../constants/theme'

import LoginScreen      from '../screens/LoginScreen'
import DashboardScreen  from '../screens/DashboardScreen'
import VisitsListScreen from '../screens/VisitsListScreen'
import CalendarScreen   from '../screens/CalendarScreen'
import ProfileScreen    from '../screens/ProfileScreen'
import VisitDetailScreen from '../screens/VisitDetailScreen'
import VisitFormScreen  from '../screens/VisitFormScreen'

import type {
  RootStackParamList,
  AuthStackParamList,
  MainTabParamList,
  VisitsStackParamList,
} from '../types'

const RootStack = createNativeStackNavigator<RootStackParamList>()
const AuthStack = createNativeStackNavigator<AuthStackParamList>()
const MainTab   = createBottomTabNavigator<MainTabParamList>()
const VisitsStack = createNativeStackNavigator<VisitsStackParamList>()

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
    </AuthStack.Navigator>
  )
}

function VisitsNavigator() {
  return (
    <VisitsStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: Colors.primary },
        headerTintColor: Colors.textInverse,
        headerTitleStyle: { fontWeight: '700' },
      }}
    >
      <VisitsStack.Screen name="VisitsList"   component={VisitsListScreen}  options={{ title: 'Mis Visitas' }} />
      <VisitsStack.Screen name="VisitDetail"  component={VisitDetailScreen} options={{ title: 'Detalle de Visita' }} />
      <VisitsStack.Screen name="VisitForm"    component={VisitFormScreen}   options={{ title: 'Formulario Técnico' }} />
    </VisitsStack.Navigator>
  )
}

function MainNavigator() {
  return (
    <MainTab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: Colors.primary },
        headerTintColor: Colors.textInverse,
        headerTitleStyle: { fontWeight: '700' },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textSecondary,
        tabBarStyle: { borderTopColor: Colors.border },
        tabBarIcon: ({ focused, color, size }) => {
          const icons: Record<string, [string, string]> = {
            Dashboard: ['home', 'home-outline'],
            Visits:    ['clipboard', 'clipboard-outline'],
            Calendar:  ['calendar', 'calendar-outline'],
            Profile:   ['person', 'person-outline'],
          }
          const [active, inactive] = icons[route.name] ?? ['ellipse', 'ellipse-outline']
          return <Ionicons name={(focused ? active : inactive) as any} size={size} color={color} />
        },
      })}
    >
      <MainTab.Screen name="Dashboard" component={DashboardScreen} options={{ title: 'Inicio' }} />
      <MainTab.Screen name="Visits"    component={VisitsNavigator} options={{ title: 'Visitas', headerShown: false }} />
      <MainTab.Screen name="Calendar"  component={CalendarScreen}  options={{ title: 'Calendario' }} />
      <MainTab.Screen name="Profile"   component={ProfileScreen}   options={{ title: 'Mi Perfil' }} />
    </MainTab.Navigator>
  )
}

export default function AppNavigator() {
  const { isLoading, isAuthenticated, initializeAuth, logout } = useAuthStore()

  useEffect(() => {
    initializeAuth()
    setLogoutCallback(logout)
  }, [])

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: Colors.primary }}>
        <ActivityIndicator size="large" color={Colors.textInverse} />
      </View>
    )
  }

  return (
    <NavigationContainer>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <RootStack.Screen name="Main" component={MainNavigator} />
        ) : (
          <RootStack.Screen name="Auth" component={AuthNavigator} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  )
}
