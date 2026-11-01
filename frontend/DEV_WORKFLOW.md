# Development workflow

## Daily UI work: development APK + Metro

Build and install the development client once:

```powershell
cd frontend
npx eas build --platform android --profile development
```

Install the APK on your phone, then start Metro:

```powershell
npm run dev
```

Scan the Metro QR code from the installed development app. Fast Refresh applies JavaScript, TypeScript, styles, and Metro-bundled asset edits without another APK build.

Create the local environment file and set `EXPO_PUBLIC_API_URL` to the reachable API origin (including `http://` or `https://` and port):

```powershell
Copy-Item .env.example .env
```

Set the Supabase public URL and anon key if overriding the app defaults. Restart Metro after changing environment variables.

## Browser layout checks

```powershell
cd frontend
npm run web
```

Open the local URL in Chrome and use Device Mode to check responsive layout. Web is for layout checks only; it does not represent Android font scaling, native controls, permissions, notifications, or device behavior.

Speech capture is stubbed on web; local notifications, calendar sync, and Google sign-in are unavailable in this preview. Secure storage uses browser local storage, and SVG assets bundle for web.

## Android typography checks

Use the development APK on an Android emulator or device. In Android Settings, set **Font size = Largest** and **Display size = Large**, then review the screens on-device.

For a USB connection when Wi-Fi discovery is unreliable:

```powershell
cd frontend
npm run android:usb
```

Connect the device with USB debugging enabled and accept the debugging prompt before running the command.

## Tester builds

Use EAS preview/production builds for tester distribution only:

```powershell
cd frontend
npx eas build --platform android --profile preview
npx eas build --platform android --profile production
```

## When a rebuild is required

Rebuild the development APK after adding or upgrading native packages, changing `app.json` plugins or permissions, or upgrading the Expo SDK. A rebuild is **not** required for JavaScript, TSX, styles, or assets bundled through Metro.

## Troubleshooting

- **Phone cannot connect:** Confirm phone and computer are on the same Wi-Fi and allow Metro through the computer firewall. If Wi-Fi discovery remains unreliable, connect USB debugging and use `npm run android:usb`.
- **Stale bundle:** Stop Metro, then run `npm run dev:clear`.
- **API unreachable:** Set `EXPO_PUBLIC_API_URL` in `frontend/.env` to the API URL reachable from the device, then restart Metro. A dev build with this variable missing logs a warning.
