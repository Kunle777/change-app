# Supabase Auth Migration

A full record of every architectural decision and code change made when migrating from a custom JWT auth system to Supabase Auth.

---

## What Changed and Why

### Before
- Backend issued its own JWTs using `python-jose`
- `public.users` stored `email` and `password_hash` directly
- `public.users.id` was a self-generated `uuid.uuid4()`
- Frontend called `/api/auth/register` and `/api/auth/login` on the FastAPI backend
- Tokens were manually stored with `SecureStore.setItemAsync`

### After
- Supabase Auth owns all credentials (`email`, `password_hash`, token issuance)
- `public.users.id` is a foreign key to `auth.users.id` — Supabase generates the UUID
- Frontend calls Supabase directly via the SDK for register/login
- Token storage and refresh is handled automatically by the Supabase SDK
- FastAPI only *verifies* Supabase-issued JWTs — it no longer creates them

---

## Backend Changes

### `app/users/models.py`

**Removed:**
- `email` column — Supabase Auth owns this
- `password_hash` column — Supabase Auth owns this
- `default=uuid.uuid4` on the `id` column — Supabase generates the ID now

**Added:**
- `ForeignKey("auth.users.id", ondelete="CASCADE")` on `id` — links the public profile row to the Supabase auth row
- A `_ensure_auth_users_reference` helper that registers the `auth.users` table in SQLAlchemy metadata so Alembic can resolve the foreign key without erroring

**Final model:**
```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    fcm_token: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)
    dnd_bypass_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

---

### `app/users/security.py`

**Removed:**
- `hash_password`, `verify_password` — no longer needed, Supabase handles password hashing
- `create_access_token`, `decode_access_token` — no longer issuing our own JWTs
- `create_refresh_token`, `decode_refresh_token` — Supabase SDK handles refresh
- `python-jose` dependency usage

**Added:**
- `decode_supabase_token(token)` — verifies incoming JWTs using Supabase's JWT secret with `audience="authenticated"`
- Uses `PyJWT` (imported as `jwt`) which was already installed

**Kept:**
- `limiter` (slowapi) — still used in `main.py` for rate limiting

```python
import jwt as pyjwt
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

limiter = Limiter(key_func=get_remote_address)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

def decode_supabase_token(token: str) -> dict:
    payload = pyjwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
    return payload
```

---

### `app/users/dependencies.py`

**Changed:**
- `decode_access_token` replaced with `decode_supabase_token`
- `user_id` is now extracted from `payload.get("sub")` — same field, but now it's a Supabase UUID
- Error handling wrapped in a broad `except Exception` since `pyjwt.decode` raises `jwt.exceptions.DecodeError` / `jwt.exceptions.InvalidAudienceError` etc.
- `tokenUrl` updated to `api/auth/token` (the no-op placeholder)

**Unchanged:**
- The function signature `get_current_user(token, db) -> User` is identical
- The DB lookup `select(User).where(User.id == user_id)` is identical
- Every task route using `Depends(get_current_user)` required zero changes

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_supabase_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user
```

---

### `app/users/routers.py`

**Removed (retired):**
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/token` (Swagger login helper)

All of the above are now handled client-side by the Supabase SDK.

**Kept:**
- `GET /api/auth/profile` — still useful for verifying the full token → DB lookup chain works
- `POST /api/auth/token` replaced with a no-op placeholder so Swagger UI's Authorize button doesn't 404

---

### `.env`

**Added:**
```
SUPABASE_JWT_SECRET = oZThZt6ztX67O3H721RH8/...
```

Found in Supabase → Settings → API → JWT Settings. This is the secret used to verify all tokens issued by Supabase Auth.

---

### Alembic Migration

File: `alembic/versions/09f12da7ddf3_link_users_table_to_supabase_auth.py`

```python
def upgrade() -> None:
    op.drop_constraint('users_email_key', 'users', type_='unique')
    op.create_foreign_key(None, 'users', 'users', ['id'], ['id'], referent_schema='auth', ondelete='CASCADE')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'snoozed_until')
    op.drop_column('users', 'email')
```

Since this was a dev-only database with no real users, the migration dropped `email`, `password_hash`, and the unique email constraint, then added the FK to `auth.users`.

---

## Database: Supabase SQL

### Trigger — auto-create `public.users` on signup

Run once in Supabase SQL Editor. Fires every time Supabase Auth creates a new `auth.users` row:

```sql
create function public.handle_new_user()
returns trigger as $$
begin
  insert into public.users (id, created_at)
  values (new.id, now());
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

This means you never manually create a `public.users` row — Postgres does it automatically the moment someone registers.

### Row Level Security

```sql
alter table public.tasks enable row level security;

create policy "Users can access own tasks"
  on public.tasks for all
  using (auth.uid() = user_id);
```

Second layer of defense on top of FastAPI's `WHERE user_id = current_user.id` filtering. Prevents any direct Supabase client access to other users' tasks.

---

## Frontend Changes

### `services/supabase.ts` (new file)

Created the Supabase client. Key decisions:
- Uses `expo-secure-store` (already installed) as the session storage adapter — same secure storage, now managed by the SDK instead of manual `setItemAsync` calls
- `detectSessionInUrl: false` — required for React Native (no URL-based OAuth redirects)
- `autoRefreshToken: true` — SDK silently refreshes the JWT before it expires

```typescript
import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(
  'https://jcflmvahszgqikxtnuwn.supabase.co',
  '<ANON_KEY>',
  {
    auth: {
      storage: ExpoSecureStoreAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  }
);
```

---

### `screens/LoginScreen.tsx`

**Removed:**
- Import of `login` from `../services/auth`
- Manual `SecureStore.setItemAsync("access_token", ...)` — this was also the root cause of the `ExpoSecureStore.default.setValueWithKeyAsync is not a function` error in web mode
- Broken code that had been pasted outside a function body (leftover from a previous edit)

**Added:**
- `supabase.auth.signInWithPassword({ email, password })`
- `React` import (required for JSX return type to resolve correctly with this tsconfig)
- Destructured response as `{ error: authError }` to avoid name clash with the `error` state variable

```typescript
const handleLogin = async () => {
  setLoading(true);
  setError("");
  const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
  if (authError) {
    setError(authError.message);
  }
  setLoading(false);
};
```

---

### `screens/RegisterScreen.tsx`

**Removed:**
- Import of `register` from `../services/auth`
- `phone` field (Supabase Auth doesn't take phone on `signUp` by default — can be added later via `supabase.auth.updateUser`)
- Manual error handling against `err?.response?.data?.detail`

**Added:**
- `supabase.auth.signUp({ email, password })`
- `React` import
- State variable renamed from `error` to `errorMsg` to fully eliminate any TypeScript redeclaration clash with the destructured `authError`

```typescript
const handleRegister = async () => {
  if (password !== confirmPassword) {
    setErrorMsg("Passwords do not match");
    return;
  }
  setLoading(true);
  setErrorMsg("");
  const { error: authError } = await supabase.auth.signUp({ email, password });
  if (authError) {
    setErrorMsg(authError.message);
  } else {
    navigation.navigate("Login");
  }
  setLoading(false);
};
```

---

### `services/auth.ts`

Not deleted — kept as-is since it still exports `getProfile` which may be useful. The `register` and `login` exports are now dead code but harmless.

---

## Token Flow: Before vs After

| Step | Before | After |
|---|---|---|
| Register | `POST /api/auth/register` → FastAPI creates user + returns JWT | `supabase.auth.signUp()` → Supabase creates `auth.users` row → trigger creates `public.users` row |
| Login | `POST /api/auth/login` → FastAPI verifies password + returns JWT | `supabase.auth.signInWithPassword()` → Supabase returns JWT |
| Token storage | Manual `SecureStore.setItemAsync` | Automatic via SDK's SecureStore adapter |
| Token refresh | Manual `POST /api/auth/refresh` | Automatic via SDK's `autoRefreshToken` |
| API calls | `Authorization: Bearer <custom_jwt>` | `Authorization: Bearer <supabase_jwt>` (same header format) |
| Backend verification | `jose.jwt.decode` with custom secret | `pyjwt.decode` with Supabase JWT secret + `audience="authenticated"` |

---

## What Was Not Changed

- `app/tasks/routers.py` — zero changes, all routes still use `Depends(get_current_user)` and receive a `User` object with `.id`
- `app/tasks/models.py` — unchanged
- `app/tasks/service.py` — unchanged
- `app/tasks/schemas.py` — unchanged
- `app/database.py` — unchanged
- `navigation/AppNavigator.tsx` — unchanged
- `App.tsx` — unchanged
- `services/api.ts` — unchanged (still used for task API calls with axios)

---

## Testing Checklist

- [ ] Register a new account → user appears in Supabase Auth → Users
- [ ] `public.users` row auto-created by trigger with matching UUID
- [ ] Login succeeds with no error
- [ ] `GET /api/auth/profile` returns `{"id": "..."}` with the Supabase JWT
- [ ] `GET /api/tasks` returns tasks correctly attributed to the user
- [ ] `POST /api/tasks` creates a task with correct `user_id`
- [ ] Token refresh happens silently (check after 1 hour)
- [ ] RLS blocks direct Supabase client access to another user's tasks

---

## Known Dev-Only Settings to Revisit Before Production

- Email confirmation is likely disabled in Supabase dashboard for dev — re-enable before launch
- `allow_origins=["*"]` in FastAPI CORS middleware — restrict to your actual domain
- Supabase anon key is embedded in the frontend bundle — this is intentional and safe, but RLS must be properly configured to limit what the anon key can access
