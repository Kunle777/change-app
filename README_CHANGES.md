# Historical Changes Applied (summary)

Some notes below describe an earlier workspace state. For current behavior, see [README_change.md](README_change.md), especially its sections on local notifications, recurring tasks, activity streaks, and outbox delivery.

This document explains all edits I made across the workspace, why I made them, and recommended next steps. Use it as a single-source summary when testing or cleaning up temporary fixes.

## What I changed (high level)

- Backend
  - Restarted the dev server bound to all interfaces so physical devices can reach it: run `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` from [change-backend](change-backend).
  - Implemented `PATCH /api/auth/fcm-token` route and `update_fcm_token` service (previously added in session).

- Frontend
  - `frontend/services/api.ts`: added runtime detection so web builds use the browser origin (`window.location`), Expo debugger host is used during local native dev, and a LAN fallback (`http://10.198.145.217:8000`) is kept for physical devices. [frontend/services/api.ts](frontend/services/api.ts#L1)
  - `frontend/app.json`: added Firebase plugins and `googleServicesFile`, and fixed `ios.icon` to point to an existing image. [frontend/app.json](frontend/app.json#L1)
  - UI and FCM wiring (previous session changes): `HomeScreen`, `TaskCard`, `auth` service updates to send FCM token to backend.

- TypeScript / IDE fixes (temporary)
  - Created a minimal shim under `frontend/node_modules/expo-module-scripts/` so TypeScript can resolve `expo-module-scripts/tsconfig.base` referenced by some package-generated tsconfig files.
    - Added `package.json` to declare the package name.
    - Added `tsconfig.base.json` and an extra no-extension `tsconfig.base` file to match some extend patterns exactly.
    - Files: [frontend/node_modules/expo-module-scripts/tsconfig.base.json](frontend/node_modules/expo-module-scripts/tsconfig.base.json#L1), [frontend/node_modules/expo-module-scripts/tsconfig.base](frontend/node_modules/expo-module-scripts/tsconfig.base#L1), [frontend/node_modules/expo-module-scripts/package.json](frontend/node_modules/expo-module-scripts/package.json#L1)

## Why these changes were needed

- Device -> local backend connectivity: The dev server previously bound to `127.0.0.1`, which blocks requests from a physical device on the same LAN. Binding to `0.0.0.0` allows the server to accept connections from other network interfaces.

- Expo Go vs native vs web API host: Expo provides several runtime contexts (web, Expo Go, dev client). Using `window.location` on web ensures the browser-origin is used; using `debuggerHost` helps in Expo-managed flows; a LAN fallback helps when the debugger host isn't available.

- TypeScript error about `expo-module-scripts/tsconfig.base`: some packages (e.g., `expo-constants`) include a generated tsconfig that extends `expo-module-scripts/tsconfig.base`. In environments where that package isn't installed (or its generated file isn't available), the TypeScript language server reports a missing-extends error. I added a small shim in `node_modules` to silence the error immediately.

## Why the tsserver error may still appear (and how to fully remove it)

- The TypeScript language server caches resolution results. After file-system fixes you should reload the editor TypeScript server and/or the VS Code window:

```bash
# In VS Code command palette
> TypeScript: Restart TS Server
> Developer: Reload Window
```

- Long-term fixes (recommended):
  - Install and keep the correct package that provides `expo-module-scripts` as a proper dependency instead of a local shim. Typically this means using the Expo CLI and `expo` tooling or adding the appropriate package versions via `npm` or `yarn`.
  - Remove the temporary files from `node_modules` and instead update the package that produces the generated tsconfig (or adjust upstream config).

## Files I edited or added

- Edited: [frontend/services/api.ts](frontend/services/api.ts#L1)
- Edited: [frontend/app.json](frontend/app.json#L1)
- Added: [frontend/node_modules/expo-module-scripts/tsconfig.base.json](frontend/node_modules/expo-module-scripts/tsconfig.base.json#L1)
- Added: [frontend/node_modules/expo-module-scripts/tsconfig.base](frontend/node_modules/expo-module-scripts/tsconfig.base#L1)
- Added: [frontend/node_modules/expo-module-scripts/package.json](frontend/node_modules/expo-module-scripts/package.json#L1)

## Next recommended actions (priority order)

1. Restart the TypeScript server / reload VS Code to clear cached diagnostics.
2. Verify web build: run the web app and check browser console for `API base URL:` and test API calls.
3. If you need a persistent fix for `expo-module-scripts`, install the correct package or update your workspace tooling so the generated tsconfig is present during development.
4. (Optional) Remove the temporary node_modules shims once the proper packages are present.
5. To get native FCM working: install Android SDK, configure `ANDROID_SDK_ROOT`, and either build a dev client or use EAS builds.

## Quick commands

Start backend bound to LAN:

```bash
cd change-backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Restart TS server (VS Code):

1. Open Command Palette (Ctrl+Shift+P)
2. Run `TypeScript: Restart TS Server`
3. Run `Developer: Reload Window`

If issues persist, tell me and I will try a different resolution (edit generated tsconfig files directly or apply a workspace-level tsconfig override).

---

If you want, I can now:

- Automatically remove the temporary node_modules shims and instead patch the offending package `expo-constants` to extend a known base.
- Or add a workspace-level `tsconfig.base.json` and have project tsconfig extend that (less invasive).

Which option do you prefer?
