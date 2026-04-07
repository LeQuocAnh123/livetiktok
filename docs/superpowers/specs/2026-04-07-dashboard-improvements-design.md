# Dashboard Improvements Design Spec

**Date:** 2026-04-07  
**Status:** Approved  
**Scope:** WebSocket auto-reconnect, Analytics date filter, feedItems limit, JWT auth

---

## Overview

This spec covers four improvements to the LiveTikTok dashboard:

1. **WebSocket Auto-Reconnect** - Automatic reconnection with exponential backoff
2. **Analytics Date Range Filter** - Filter stats by time period
3. **feedItems Limit** - Cap Live Monitor feed at 200 items
4. **Dashboard JWT Auth** - Proper authentication for all dashboard access

---

## 1. WebSocket Auto-Reconnect

### Current State
`WSClient` in `frontend/lib/ws.ts` has no reconnect logic. When server disconnects, client must manually reconnect or re-mount component.

### Design

#### New WSClient Behavior
```
WSClient
├── connect(url) - unchanged public API
├── Exponential backoff: 1s → 2s → 4s → 8s → 16s (max)
├── Max retries: 10
├── onclose event → schedule reconnect (unless manual disconnect)
├── New event type: "connection" with status field
└── disconnect() sets flag to prevent auto-reconnect
```

#### New Message Type
```typescript
// Add to WSMessage union in lib/ws.ts
| { type: "connection"; status: "connecting" | "connected" | "disconnected" | "reconnecting" }
```

#### Implementation Details
- Add private fields: `_reconnectAttempt`, `_reconnectTimer`, `_url`
- `onclose` handler: if close code !== 1000 (normal) → schedule reconnect
- `onopen` handler: reset `_reconnectAttempt` to 0, emit `{ type: "connection", status: "connected" }`
- `disconnect()`: set `_manualDisconnect = true`, clear timer, close socket
- Emit `reconnecting` status before each retry attempt

#### Files Changed
- `frontend/lib/ws.ts` - Add reconnect logic and connection status events

---

## 2. Analytics Date Range Filter

### Current State
`GET /api/v1/analytics/` returns all-time stats for a seller with no time filtering.

### Design

#### Backend API Change
```
GET /api/v1/analytics/?seller_id=xxx&start_date=2026-04-01&end_date=2026-04-07

Query params:
- seller_id: str (required, existing)
- start_date: Optional[date] - inclusive start
- end_date: Optional[date] - inclusive end

Behavior:
- Filter LiveSession.started_at within [start_date, end_date]
- If params omitted → all-time stats (backwards compatible)
```

#### Frontend UI
```
Analytics Page
├── Date range picker component (two date inputs or range picker)
├── Quick presets: "Hôm nay", "7 ngày", "30 ngày", "Tất cả"
├── Auto-load when dates change (debounced)
└── Display selected range in header
```

#### Files Changed
- `backend/app/api/v1/analytics.py` - Add date params and filter logic
- `backend/app/schemas/analytics.py` - No changes needed (response unchanged)
- `frontend/app/analytics/page.tsx` - Add date picker UI
- `frontend/lib/api.ts` - Update analytics.get() to accept date params
- `frontend/components/analytics/DateRangeFilter.tsx` - New component

---

## 3. feedItems Limit (200 items)

### Current State
`feedItems` in `monitor/page.tsx` accumulates indefinitely via WebSocket events. Long livestreams cause UI lag.

### Design

#### Constant
```typescript
const MAX_FEED_ITEMS = 200;
```

#### Updated Handler
```typescript
// In comment handler
addOrUpdate((items) => {
  const updated = [...items, { ...msg }];
  return updated.length > MAX_FEED_ITEMS 
    ? updated.slice(-MAX_FEED_ITEMS) 
    : updated;
});
```

#### Edge Case: Selected Item Removal
When an item is removed from feed, if it was selected:
- Clear `selectedId` to prevent stale reference
- Check in `addOrUpdate` or via useEffect watching feedItems

#### Files Changed
- `frontend/app/monitor/page.tsx` - Add limit logic and selection cleanup

---

## 4. Dashboard JWT Auth

### Current State
- `ws_monitor_token` env var protects WebSocket (query param auth)
- REST API endpoints have no authentication
- No login flow exists

### Design

#### Backend Architecture
```
New files:
├── app/core/security.py        # JWT encode/decode, password verify
├── app/api/v1/auth.py          # Login/logout/me endpoints
└── app/schemas/auth.py         # LoginRequest, UserResponse

No User model - credentials from env vars:
├── ADMIN_USERNAME (default: "admin")
└── ADMIN_PASSWORD (required, no default)
```

#### Auth Endpoints
```
POST /api/v1/auth/login
  Body: { "username": str, "password": str }
  Success: Set httpOnly cookie "access_token", return { "username": str }
  Failure: 401 Unauthorized

POST /api/v1/auth/logout
  Clear cookie, return { "message": "Logged out" }

GET /api/v1/auth/me
  Protected - requires valid JWT
  Return: { "username": str }
```

#### JWT Configuration
```python
# In app/config.py - add:
admin_username: str = "admin"
admin_password: str  # Required, no default
jwt_expire_hours: int = 24
```

#### Cookie Settings
```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # False in dev
    samesite="lax",
    max_age=86400,  # 24 hours
)
```

#### Protected Routes
```python
# Dependency for protected endpoints
async def get_current_user(
    request: Request,
) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

# Apply to routers:
# - /api/v1/knowledge/*
# - /api/v1/sessions/*
# - /api/v1/analytics/*
# - /api/v1/settings/*
# - /ws/monitor (verify from cookie instead of query param)
```

#### Frontend Architecture
```
New files:
├── app/login/page.tsx              # Login form
├── middleware.ts                   # Auth redirect logic
└── components/auth/LoginForm.tsx   # Form component

Auth flow:
├── middleware.ts checks cookie presence
├── Unauthenticated → redirect to /login
├── /login page: form submit → POST /api/v1/auth/login
├── Success → redirect to /monitor
├── API 401 → redirect to /login (via fetch wrapper or interceptor)
```

#### Files Changed

**Backend:**
- `backend/app/config.py` - Add admin_username, admin_password, jwt_expire_hours
- `backend/app/core/security.py` - New: JWT functions, password verify
- `backend/app/api/v1/auth.py` - New: login/logout/me endpoints
- `backend/app/schemas/auth.py` - New: request/response schemas
- `backend/app/main.py` - Include auth router
- `backend/app/api/v1/*.py` - Add Depends(get_current_user) to all protected routes
- `backend/app/api/ws.py` - Change to cookie-based auth
- `backend/.env.example` - Add ADMIN_USERNAME, ADMIN_PASSWORD
- `backend/pyproject.toml` - Add PyJWT dependency

**Frontend:**
- `frontend/app/login/page.tsx` - New: login page
- `frontend/components/auth/LoginForm.tsx` - New: form component
- `frontend/middleware.ts` - New: auth redirect
- `frontend/lib/api.ts` - Add login/logout/me methods, handle 401
- `frontend/hooks/useWebSocket.ts` - Remove token query param (cookie-based now)
- `frontend/.env.example` - Remove WS_TOKEN (no longer needed)

---

## Security Considerations

1. **httpOnly cookie** - Token not accessible via JavaScript (XSS protection)
2. **SameSite=Lax** - Prevents CSRF for state-changing requests
3. **secure=True in production** - Cookie only sent over HTTPS
4. **24h expiry** - Limits token lifetime
5. **No token in URL** - WebSocket uses cookie, not query param

---

## Testing Strategy

1. **WebSocket reconnect** - Unit test with mock WebSocket, verify backoff timing
2. **Analytics filter** - Integration test with date params, verify SQL filtering
3. **feedItems limit** - Unit test slice logic, verify oldest items dropped
4. **Auth flow** - Integration tests for login/logout, protected routes return 401

---

## Migration Notes

1. **Backend env vars** - Must add `ADMIN_PASSWORD` before deploying
2. **Existing WS_MONITOR_TOKEN** - Can be removed after migration
3. **Frontend env** - Remove `NEXT_PUBLIC_WS_TOKEN` after migration
4. **No database migration** - No new models, credentials from env

---

## Implementation Order

1. **JWT Auth (Backend)** - Foundation for other protected features
2. **JWT Auth (Frontend)** - Login flow, middleware
3. **WebSocket Auth Migration** - Switch from query param to cookie
4. **WebSocket Auto-Reconnect** - Independent of auth
5. **feedItems Limit** - Quick win, independent
6. **Analytics Date Filter** - Backend then frontend
