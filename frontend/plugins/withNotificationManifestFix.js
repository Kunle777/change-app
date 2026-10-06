// plugins/withNotificationManifestFix.js
const { withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

module.exports = function withNotificationManifestFix(config) {
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
};
