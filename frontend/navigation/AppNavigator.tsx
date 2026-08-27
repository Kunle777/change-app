import React from 'react';
import { useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useNavigation } from '@react-navigation/native';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import HomeScreen from '../screens/HomeScreen';
import CheckInScreen from '../screens/CheckInScreen';
import AIScreen from '../screens/AIScreen';
import BrainDumpScreen from '../screens/BrainDumpScreen';
import SettingsScreen from '../screens/SettingsScreen';
import ForgotPasswordScreen from '../screens/ForgotPasswordScreen';
import ResetPasswordScreen from '../screens/ResetPasswordScreen';
import ChangePasswordScreen from '../screens/ChangePasswordScreen';
import TaskDetailScreen from '../screens/TaskDetailScreen';
import CalendarScreen from '../screens/CalenderScreen';
import { Ionicons } from '@expo/vector-icons';
import WinLogScreen from '../screens/WinLogScreen';

export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  ResetPassword: undefined;
  ChangePassword: undefined;
  TaskDetail: { taskId: string };
  MainTabs: undefined;
  CheckIn: { type: 'morning' | 'evening' };
  Calendar: undefined;
  WinLog: undefined;
};

export type MainTabParamList = {
  Home: undefined;
  AI: undefined;
  BrainDump: undefined;
  Savings: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function SavingsComingSoon() {
  return (
    <View style={styles.centered}>
      <Text style={styles.comingSoon}>Savings Vault - coming soon</Text>
    </View>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: '#333',
        tabBarInactiveTintColor: '#999',
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ color, size }) => <Ionicons name="home" color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="AI"
        component={AIScreen}
        options={{
          tabBarIcon: ({ color, size }) => <Ionicons name="sparkles" color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="BrainDump"
        component={BrainDumpScreen}
        options={{
          title: 'Dump',
          tabBarIcon: ({ color, size }) => <Ionicons name="bulb" color={color} size={size} />,
        }}
      />
      <Tab.Screen
        name="Savings"
        component={SavingsComingSoon}
        options={{
          tabBarIcon: ({ size }) => <Ionicons name="wallet" color="#ccc" size={size} />,
          tabBarButton: (props) => <TouchableOpacity {...(props as any)} style={{ opacity: 0.4 }} disabled />,
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          tabBarIcon: ({ color, size }) => <Ionicons name="settings" color={color} size={size} />,
        }}
      />
    </Tab.Navigator>
  );
}

function ResetPasswordWrapper() {
  const navigation = useNavigation<any>();
  return <ResetPasswordScreen onComplete={() => navigation.navigate('Login')} />;
}

export default function AppNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
      <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
      <Stack.Screen
        name="ResetPassword"
        options={{ presentation: 'modal', headerShown: true, title: 'Reset Password' }}
        component={ResetPasswordWrapper}
      />
      <Stack.Screen
        name="ChangePassword"
        component={ChangePasswordScreen}
        options={{ headerShown: true, title: 'Change Password' }}
      />
      <Stack.Screen name="MainTabs" component={MainTabs} />
      <Stack.Screen
        name="TaskDetail"
        component={TaskDetailScreen}
        options={{ headerShown: true, title: 'Task' }}
      />
      <Stack.Screen
        name="CheckIn"
        component={CheckInScreen}
        options={{ presentation: 'modal', headerShown: true, title: 'Check-In' }}
      />
      <Stack.Screen
        name="Calendar"
        component={CalendarScreen}
        options={{ headerShown: true, title: 'Calendar' }}
      />
      <Stack.Screen
        name="WinLog"
        component={WinLogScreen}
        options={{ headerShown: true, title: 'Wins' }}
      />
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  comingSoon: { color: '#999', fontSize: 16 },
});
