// plugins/withNotificationManifestFix.js
const { withAndroidManifest } = require('@expo/config-plugins');

module.exports = function withNotificationManifestFix(config) {
  return withAndroidManifest(config, (config) => {
    const application = config.modResults.manifest.application[0];
    const metaData = application['meta-data'] || [];

    const target = metaData.find(
      (item) =>
        item.$['android:name'] === 'com.google.firebase.messaging.default_notification_color',
    );

    if (target) {
      target.$['tools:replace'] = 'android:resource';
    }

    return config;
  });
};
