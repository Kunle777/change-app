const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

const { transformer, resolver } = config;

config.transformer = {
  ...transformer,
  babelTransformerPath: require.resolve('react-native-svg-transformer'),
};
config.resolver = {
  ...resolver,
  assetExts: resolver.assetExts.filter((ext) => ext !== 'svg'),
  sourceExts: [...resolver.sourceExts, 'svg'],
};

// In Expo Go, expo-notifications throws at module evaluation time on Android.
// DevicePushTokenAutoRegistration.fx.js calls addPushTokenListener() at the
// top level → warnOfExpoGoPushUsage() → throws (SDK 53+). Runtime isExpoGo
// checks cannot prevent this. We redirect the entire package to a no-op stub
// so it is never evaluated. Set EXPO_GO=1 when running `expo start` for Expo Go.
if (process.env.EXPO_GO === '1') {
  const noopPath = path.resolve(__dirname, 'services/notifications.noop.ts');
  const existingResolveRequest = config.resolver.resolveRequest;

  config.resolver.resolveRequest = (context, moduleName, platform) => {
    if (moduleName === 'expo-notifications') {
      return { filePath: noopPath, type: 'sourceFile' };
    }
    if (existingResolveRequest) {
      return existingResolveRequest(context, moduleName, platform);
    }
    return context.resolveRequest(context, moduleName, platform);
  };
}

module.exports = config;
