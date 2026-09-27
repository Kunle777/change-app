// plugins/withNotificationManifestFix.js
const { withAndroidManifest, withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

function withCleartextAndKeyboard(config) {
  return withAndroidManifest(config, (config) => {
    const manifest = config.modResults;
    const app = manifest.manifest.application[0];
    app.$['android:usesCleartextTraffic'] = 'true';
    app.$['android:windowSoftInputMode'] = 'adjustResize';
    return config;
  });
}

function withFirebaseNotificationFix(config) {
  return withDangerousMod(config, [
    'android',
    async (config) => {
      const manifestPath = path.join(
        config.modRequest.platformProjectRoot,
        'app/src/main/AndroidManifest.xml',
      );

      let manifest = fs.readFileSync(manifestPath, 'utf-8');

      const target =
        '<meta-data android:name="com.google.firebase.messaging.default_notification_color" android:resource="@color/notification_icon_color"/>';

      const replacement =
        '<meta-data android:name="com.google.firebase.messaging.default_notification_color" android:resource="@color/notification_icon_color" tools:replace="android:resource"/>';

      if (manifest.includes(target)) {
        manifest = manifest.replace(target, replacement);
        fs.writeFileSync(manifestPath, manifest, 'utf-8');
      }

      return config;
    },
  ]);
}

module.exports = function withNotificationManifestFix(config) {
  config = withCleartextAndKeyboard(config);
  config = withFirebaseNotificationFix(config);
  return config;
};
