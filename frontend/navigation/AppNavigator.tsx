import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import HomeScreen from '../screens/HomeScreen';
import CheckInScreen from '../screens/CheckInScreen';
import AIScreen from '../screens/AIScreen';
import BrainDumpScreen from '../screens/BrainDumpScreen';

// 1. Define the types for your routes
export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  Home: undefined;
  CheckIn: { type: 'morning' | 'evening' };
  AI: undefined;
  BrainDump: undefined;
};

// 2. Create the Stack Navigator instance
const Stack = createNativeStackNavigator<RootStackParamList>();

function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Login"
      screenOptions={{
        headerShown: false, // Hides the default native top navigation bar
      }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="CheckIn" component={CheckInScreen} />
      <Stack.Screen name="AI" component={AIScreen} options={{ headerShown: true, title: 'AI Assistant' }} />
      <Stack.Screen name="BrainDump" component={BrainDumpScreen} options={{ headerShown: true, title: 'Brain Dump' }} />
    </Stack.Navigator>
  );
}

export default AppNavigator;
