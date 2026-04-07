# Multi-Tenant Design Spec

**Date:** 2026-04-07  
**Status:** Approved  
**Approach:** Seller-as-User (Approach A)

## Overview

Convert the single-tenant TikTok Live Bot to multi-tenant, allowing multiple sellers to use a shared deployment with isolated data and sessions.

## Requirements

- Each seller has their own account (username/password)
- Admin creates seller accounts via CLI (no self-registration)
- Each seller can run one active live session at a time
- Data isolation: sellers only see their own knowledge base, sessions, analytics
- WebSocket broadcasts isolated per seller

## Out of Scope

- Admin dashboard UI (CLI only)
- Self-registration for sellers
- One user managing multiple sellers
- Multiple concurrent sessions per seller

---

## 1. Database & Model Changes

### Seller Model

Add three columns to the existing `Seller` model:

```python
class Seller(Base):
    __tablename__ = "sellers"
    
    # Existing fields...
    id: Mapped[str]
    name: Mapped[str]
    tiktok_unique_id: Mapped[str]
    tiktok_session_id_encrypted: Mapped[str]
    tiktok_target_idc_encrypted: Mapped[str]
    bot_settings: Mapped[dict]
    created_at: Mapped[datetime]
    
    # New fields
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
```

**Field descriptions:**
- `username`: Unique login identifier (can differ from `tiktok_unique_id`)
- `password_hash`: bcrypt hashed password
- `is_active`: Allows disabling account without deleting data

### Migration

Alembic migration to add the three columns. Existing sellers must have username/password set via CLI before they can login.

---

## 2. Authentication Flow

### Login Process

1. Seller POSTs to `/api/v1/auth/login` with `username` + `password`
2. Backend looks up `Seller` by username
3. Verify password against `Seller.password_hash` using bcrypt
4. If `is_active` is False, reject login
5. Create JWT with payload: `{ "sub": "<seller_id>", "type": "seller" }`
6. Set httpOnly cookie (same mechanism as current)

### JWT Payload Change

```python
# Current (hardcoded admin)
{ "sub": "admin" }

# New (seller-based)
{ "sub": "seller-uuid-123", "type": "seller" }
```

### `get_current_seller` Dependency

Replace `get_current_user` with `get_current_seller`:

```python
async def get_current_seller(
    request: Request, 
    db: AsyncSession = Depends(get_db)
) -> Seller:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    seller = await db.get(Seller, payload["sub"])
    if not seller or not seller.is_active:
        raise HTTPException(status_code=401, detail="Account disabled or not found")
    
    return seller
```

All protected endpoints use `Depends(get_current_seller)` and get `seller_id` from the returned Seller object.

---

## 3. API Endpoint Changes

### Endpoints to Modify

Remove `seller_id` from request params/body - get from JWT instead:

| Endpoint | Current Source | New Source |
|----------|---------------|------------|
| `GET /api/v1/knowledge/` | `?seller_id=xxx` | JWT |
| `POST /api/v1/knowledge/` | `body.seller_id` | JWT |
| `POST /api/v1/knowledge/upload` | `?seller_id=xxx` | JWT |
| `GET /api/v1/settings/` | `?seller_id=xxx` | JWT |
| `PUT /api/v1/settings/` | `?seller_id=xxx` | JWT |
| `POST /api/v1/settings/test-reply` | `body.seller_id` | JWT |
| `GET /api/v1/analytics/` | `?seller_id=xxx` | JWT |
| `POST /api/v1/sessions/start` | `body.seller_id` | JWT |

### Auth Endpoints

- `POST /api/v1/auth/login` - Authenticate Seller by username/password
- `GET /api/v1/auth/me` - Return seller info: `{ id, username, name, tiktok_unique_id }`
- `POST /api/v1/auth/logout` - Clear cookie (unchanged)

### Schema Changes

```python
# LoginRequest - unchanged
class LoginRequest(BaseModel):
    username: str
    password: str

# UserResponse -> SellerResponse
class SellerResponse(BaseModel):
    id: str
    username: str
    name: str
    tiktok_unique_id: str
```

---

## 4. Session State Isolation

### Current (Single-Tenant)

```python
class SessionState:
    active_session_id: Optional[str] = None
    active_listener: Optional[LiveListener] = None
    # ... other fields

session_state = SessionState()  # Global singleton
```

### New (Multi-Tenant)

```python
class SessionState:
    # Same fields as before
    active_session_id: Optional[str] = None
    active_listener: Optional[LiveListener] = None
    active_replier: Optional[Replier] = None
    active_pipeline: Optional[RAGPipeline] = None
    active_task: Optional[asyncio.Task] = None
    bot_paused: bool = False
    reply_count: int = 0
    
    def reset(self) -> None:
        # Reset all fields to initial values
        ...

# Dict keyed by seller_id
session_states: dict[str, SessionState] = {}

def get_session_state(seller_id: str) -> SessionState:
    if seller_id not in session_states:
        session_states[seller_id] = SessionState()
    return session_states[seller_id]
```

Each seller has independent session state. One seller's session doesn't affect others.

---

## 5. WebSocket Changes

### Current (Broadcast to All)

```python
_connections: set[WebSocket] = set()

async def broadcast(message: dict) -> None:
    for ws in _connections:
        await ws.send_json(message)
```

### New (Isolated by Seller)

```python
_connections: dict[str, set[WebSocket]] = {}  # seller_id -> connections

async def connect(websocket: WebSocket) -> Optional[str]:
    """Accept connection and return seller_id from JWT cookie."""
    await websocket.accept()
    token = websocket.cookies.get("access_token")
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return None
    
    seller_id = payload["sub"]
    if seller_id not in _connections:
        _connections[seller_id] = set()
    _connections[seller_id].add(websocket)
    return seller_id

def disconnect(seller_id: str, websocket: WebSocket) -> None:
    if seller_id in _connections:
        _connections[seller_id].discard(websocket)

async def broadcast(seller_id: str, message: dict) -> None:
    """Broadcast only to connections belonging to this seller."""
    for ws in _connections.get(seller_id, set()):
        try:
            await ws.send_json(message)
        except Exception:
            pass  # Connection already closed
```

### Broadcast Call Sites

Update all `broadcast()` calls to include `seller_id`:

```python
# In sessions.py - seller_id available from session state
seller_id = "..."  # stored when session starts
await broadcast(seller_id, {"type": "status", "connected": True})
```

### Callback Seller Context

`_handle_comment` and `_handle_disconnect` are callbacks that need `seller_id`. Solution: store `seller_id` in `SessionState`:

```python
class SessionState:
    seller_id: Optional[str] = None  # Set when session starts
    # ... other fields

# In start_session:
state = get_session_state(seller.id)
state.seller_id = seller.id

# In _handle_comment:
async def _handle_comment(user: str, text: str, seller_id: str) -> None:
    state = get_session_state(seller_id)
    # ... use state.seller_id for broadcast
    await broadcast(seller_id, {"type": "comment", ...})
```

Use `functools.partial` to bind `seller_id` when registering callbacks:

```python
from functools import partial

# In start_session:
listener.on_comment(partial(_handle_comment, seller_id=seller.id))
listener.on_disconnect(partial(_handle_disconnect, seller_id=seller.id))
```

---

## 6. Frontend Changes

### Remove SELLER_ID

Delete from:
- `frontend/.env`
- `frontend/.env.example`
- `docker-compose.yml`

### Update `lib/api.ts`

Remove all `seller_id` params:

```typescript
// Before
const SELLER_ID = process.env.NEXT_PUBLIC_SELLER_ID ?? "";

knowledge: {
  list(params) {
    return request(`/api/v1/knowledge/${qs({ seller_id: SELLER_ID, ...params })}`);
  }
}

// After
knowledge: {
  list(params) {
    return request(`/api/v1/knowledge/${qs(params)}`);
  }
}
```

### Auth Context

```typescript
// Current
interface AuthUser {
  username: string;
}

// New
interface AuthUser {
  id: string;
  username: string;
  name: string;
  tiktok_unique_id: string;
}
```

### UI Updates

- Login page: unchanged (already exists)
- Header/navbar: display `seller.name` instead of hardcoded "Admin"
- No seller switching UI needed

---

## 7. CLI Tool

### `scripts/manage_seller.py`

```bash
# Create new seller
python scripts/manage_seller.py create \
  --username "shop1" \
  --password "secret123" \
  --name "Shop ABC" \
  --tiktok-id "@shopabc" \
  --session-id "tiktok_session_id_value" \
  --target-idc "useast1a"

# Set/reset password for existing seller
python scripts/manage_seller.py set-password --username "shop1"

# List all sellers
python scripts/manage_seller.py list

# Disable seller (soft delete)
python scripts/manage_seller.py disable --username "shop1"

# Enable seller
python scripts/manage_seller.py enable --username "shop1"
```

### Implementation Notes

- Use `asyncio.run()` for async DB operations
- Use `getpass` for secure password input
- Encrypt TikTok credentials with existing `app.core.crypto.encrypt()`
- Hash passwords with bcrypt via `passlib`

---

## 8. Testing Strategy

### Backend Tests

- Auth tests: seller login, invalid credentials, disabled account
- API tests: verify endpoints use seller from JWT, not params
- Session isolation: two sellers can have independent sessions
- WebSocket: broadcasts only reach correct seller

### Frontend Tests

- Remove SELLER_ID from test mocks
- Auth flow tests with seller response shape

---

## 9. Migration Path

1. Run Alembic migration to add columns
2. Use CLI to set username/password for existing sellers
3. Deploy backend changes
4. Deploy frontend changes (remove SELLER_ID env)
5. Test login flow

---

## Files to Modify

### Backend
- `app/models/seller.py` - Add fields
- `app/core/security.py` - Update JWT functions
- `app/core/session_state.py` - Multi-tenant state dict
- `app/api/v1/auth.py` - Seller authentication
- `app/api/v1/knowledge.py` - Use get_current_seller
- `app/api/v1/settings.py` - Use get_current_seller
- `app/api/v1/analytics.py` - Use get_current_seller
- `app/api/v1/sessions.py` - Use get_current_seller + seller_id in state
- `app/api/ws.py` - Isolated connections/broadcast
- `app/schemas/auth.py` - SellerResponse schema
- `scripts/manage_seller.py` - New CLI tool
- `alembic/versions/xxx_add_seller_auth.py` - Migration

### Frontend
- `lib/api.ts` - Remove SELLER_ID
- `.env.example` - Remove SELLER_ID
- Components using auth context - Update types

### Config
- `docker-compose.yml` - Remove NEXT_PUBLIC_SELLER_ID
