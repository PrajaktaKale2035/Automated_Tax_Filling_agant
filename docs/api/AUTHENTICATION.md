# Authentication Guide — Indian Tax Filing API

JWT bearer-token auth backed by FastAPI's OAuth2 password flow. Tokens are issued by `POST /api/auth/login` and signed with `HS256` against the server-side `SECRET_KEY`.

Base URL (dev): `http://localhost:8000`
OpenAPI: <http://localhost:8000/api/openapi.json>
Source of truth: [`backend/app/api/auth.py`](../../backend/app/api/auth.py), [`backend/app/security.py`](../../backend/app/security.py)

---

## Flow overview

1. `POST /api/auth/register` — create the account.
2. `POST /api/auth/login` — exchange email + password for a JWT.
3. Send `Authorization: Bearer <token>` on every protected call.
4. When the token expires (default 30 min), the server returns `401`. Re-login.
5. `POST /api/auth/logout` is a best-effort marker — JWTs are stateless, so the client just discards the token.

```
[client]  -- email/password -->  POST /api/auth/login
[server]  --   access_token  -->  [client]
[client]  --   Bearer token  -->  GET  /api/v2/filings, /api/documents/upload, ...
```

---

## Endpoints

### `POST /api/auth/register`

JSON body:
```json
{
  "email": "asha@example.in",
  "password": "Aa12345678",
  "full_name": "Asha Verma"
}
```

Password rules (enforced by `schemas.UserCreate`):
- minimum 8 characters
- at least 1 digit
- at least 1 uppercase letter

Notes:
- Password is hashed with `passlib`'s `pbkdf2_sha256` scheme.
- Inputs are byte-truncated to 72 bytes before hashing (see `security._truncate_for_bcrypt`) for cross-environment compatibility.

Returns `201 Created`:
```json
{
  "id": 1,
  "email": "asha@example.in",
  "full_name": "Asha Verma",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-05-02T10:15:00Z"
}
```

Errors:
- `400` — `Email already registered`
- `422` — password fails validation rules

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"asha@example.in","password":"Aa12345678","full_name":"Asha Verma"}'
```

---

### `POST /api/auth/login`

OAuth2 password flow — **`application/x-www-form-urlencoded`**, not JSON. Field names are `username` (the email) and `password`.

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=asha@example.in&password=Aa12345678"
```

Returns `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": 1,
  "email": "asha@example.in",
  "full_name": "Asha Verma"
}
```

Token claims: `{"sub": <email>, "user_id": <id>, "iat": <issued>, "exp": <expiry>}`.

Errors:
- `401` — `Incorrect email or password`
- `403` — `User account is inactive`

---

### `GET /api/auth/me`

Bearer token required. Returns the current user (same shape as `register` response).

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

### `POST /api/auth/logout`

Bearer token required. Writes an audit-log entry; the JWT is **not** server-side-blacklisted. Clients must drop the token themselves.

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

Returns:
```json
{"message": "Successfully logged out"}
```

---

## Using the token

Add the header to every protected request:

```
Authorization: Bearer <access_token>
```

Example — list current user's filings:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=asha@example.in&password=Aa12345678" \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/api/v2/filings \
  -H "Authorization: Bearer $TOKEN"

# Download a filing's PDF
curl http://localhost:8000/api/v2/filing/1/pdf \
  -H "Authorization: Bearer $TOKEN" -o itr1-1.pdf
```

---

## Token expiry

- Default lifetime: **30 minutes** from issue.
- Configurable via env var `ACCESS_TOKEN_EXPIRE_MINUTES`.
- No refresh-token endpoint is implemented. On `401 Could not validate credentials`, re-call `/api/auth/login`.
- `SECRET_KEY` and `ALGORITHM` (default `HS256`) are also env-driven. `ENCRYPTION_KEY` is a separate Fernet key used for at-rest encryption of sensitive fields (PAN, etc.) — it is not the JWT signing key.

---

## Which endpoints require auth

**Protected** (require `Authorization: Bearer <token>` and an active user):
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/v2/filings`
- `GET /api/v2/filing/{filing_id}/status`
- `GET /api/v2/filing/{filing_id}/pdf`
- `GET /api/v2/filing/{filing_id}/json`
- `POST /api/documents/upload`
- `GET /api/users/me`, `GET /api/users/me/profile`, `GET /api/users/{user_id}`, `GET /api/users/`

**Public** (no token required):
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/v2/calc/preview`
- `POST /api/v2/rag/search`
- `GET /api/health`
- `WS /api/ws/{client_id}`

`POST /api/v2/filing/start` and the LangGraph chat endpoints currently accept anonymous calls in development; do not rely on that in production.

---

## Common errors

| Status | Detail | Cause |
|--------|--------|-------|
| `401` | `Could not validate credentials` | Missing, malformed, or expired token. Re-login. |
| `401` | `Incorrect email or password` | Wrong credentials on `/api/auth/login`. |
| `403` | `User account is inactive` | `is_active = false` on the user row. |
| `400` | `Inactive user` | `get_current_active_user` rejected an authenticated-but-inactive user. |
| `400` | `Email already registered` | Duplicate `/api/auth/register`. |
| `422` | `Validation error - please check your input` | Pydantic validation: short password, missing digit/uppercase, malformed email. |

`401` responses include a `WWW-Authenticate: Bearer` header.

---

## Python example (`requests`)

```python
import requests

BASE = "http://localhost:8000"

# 1. Register (one-time)
requests.post(f"{BASE}/api/auth/register", json={
    "email": "asha@example.in",
    "password": "Aa12345678",
    "full_name": "Asha Verma",
})

# 2. Login — OAuth2 password flow uses form data, not JSON
resp = requests.post(
    f"{BASE}/api/auth/login",
    data={"username": "asha@example.in", "password": "Aa12345678"},
)
resp.raise_for_status()
token = resp.json()["access_token"]

# 3. Reuse the token across calls
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {token}"})

me = session.get(f"{BASE}/api/auth/me").json()
filings = session.get(f"{BASE}/api/v2/filings").json()

# 4. On 401, re-login
r = session.get(f"{BASE}/api/v2/filing/1/status")
if r.status_code == 401:
    token = requests.post(
        f"{BASE}/api/auth/login",
        data={"username": "asha@example.in", "password": "Aa12345678"},
    ).json()["access_token"]
    session.headers["Authorization"] = f"Bearer {token}"
    r = session.get(f"{BASE}/api/v2/filing/1/status")
```

---

## Postman / HTTPie

**Postman.** Use the built-in *OAuth 2.0 — Password Credentials* helper:
- Grant Type: `Password Credentials`
- Access Token URL: `http://localhost:8000/api/auth/login`
- Username: `<email>`
- Password: `<password>`
- Client Authentication: `Send client credentials in body` (no client_id/secret needed)

Postman will POST form data to `/api/auth/login`, store the token, and inject `Authorization: Bearer <token>` on subsequent requests.

**HTTPie.**
```bash
# Login (form-encoded with --form)
http --form POST :8000/api/auth/login username=asha@example.in password=Aa12345678

# Authenticated call
http :8000/api/v2/filings "Authorization: Bearer $TOKEN"
```
