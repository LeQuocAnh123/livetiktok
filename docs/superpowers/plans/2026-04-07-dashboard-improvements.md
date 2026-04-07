# Dashboard Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WebSocket auto-reconnect, analytics date filter, feedItems limit (200), and JWT dashboard auth.

**Architecture:** JWT auth with httpOnly cookies protects all API endpoints and WebSocket. Frontend middleware redirects unauthenticated users to login page. WebSocket client auto-reconnects with exponential backoff. Analytics API accepts optional date range params.

**Tech Stack:** FastAPI, PyJWT, Next.js middleware, shadcn/ui

---

## File Structure

### Backend (New Files)
```
backend/
├── app/
│   ├── core/
│   │   └── security.py           # CREATE — JWT encode/decode, password verify
│   ├── api/v1/
│   │   └── auth.py               # CREATE — Login/logout/me endpoints
│   └── schemas/
│       └── auth.py               # CREATE — LoginRequest, UserResponse schemas
```

### Backend (Modified Files)
```
backend/
├── pyproject.toml                # ADD PyJWT dependency
├── .env.example                  # ADD ADMIN_USERNAME, ADMIN_PASSWORD
├── app/
│   ├── config.py                 # ADD admin_username, admin_password, jwt_expire_hours
│   ├── main.py                   # INCLUDE auth router
│   ├── api/
│   │   ├── ws.py                 # CHANGE to cookie-based auth
│   │   └── v1/
│   │       ├── knowledge.py      # ADD auth dependency
│   │       ├── sessions.py       # ADD auth dependency
│   │       ├── settings.py       # ADD auth dependency
│   │       └── analytics.py      # ADD auth dependency + date filter params
│   └── schemas/
│       └── analytics.py          # ADD start_date, end_date to response (optional)
```

### Frontend (New Files)
```
frontend/
├── app/login/
│   └── page.tsx                  # CREATE — Login page
├── components/auth/
│   └── LoginForm.tsx             # CREATE — Login form component
├── components/analytics/
│   └── DateRangeFilter.tsx       # CREATE — Date range picker
└── middleware.ts                 # CREATE — Auth redirect middleware
```

### Frontend (Modified Files)
```
frontend/
├── .env.example                  # REMOVE WS_TOKEN
├── lib/
│   ├── api.ts                    # ADD auth methods, credentials: "include"
│   └── ws.ts                     # ADD auto-reconnect logic
├── hooks/
│   └── useWebSocket.ts           # REMOVE token query param
└── app/
    ├── monitor/page.tsx          # ADD feedItems limit
    └── analytics/page.tsx        # ADD date range filter UI
```

---

## Task 1: Add PyJWT Dependency

**Files:**
- Modify: `backend/pyproject.toml:9-28`

- [ ] **Step 1.1: Add PyJWT to dependencies**

```toml
# In backend/pyproject.toml, add to dependencies list after line 18:
    "PyJWT>=2.8.0",
```

The full dependencies section should look like:
```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "aiosqlite>=0.19.0",
    "pydantic-settings>=2.0.0",
    "cryptography>=42.0.0",
    "httpx>=0.26.0",
    "python-dotenv>=1.0.0",
    "websockets>=12.0",
    "python-multipart>=0.0.9",
    "chromadb>=0.5.0",
    "openai>=1.0.0",
    "anthropic>=0.40.0",
    "openpyxl>=3.1.0",
    "groq>=0.9.0",
    "google-genai>=1.0.0",
    "TikTokLive>=6.0.0",
    "PyJWT>=2.8.0",
]
```

- [ ] **Step 1.2: Install the new dependency**

Run: `cd backend && pip install -e ".[dev]"`

Expected: Successfully installed PyJWT

- [ ] **Step 1.3: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add PyJWT dependency for auth"
```

---

## Task 2: Add Auth Config Settings

**Files:**
- Modify: `backend/app/config.py:7-34`
- Modify: `backend/.env.example`

- [ ] **Step 2.1: Add auth settings to config.py**

Add these fields to the Settings class in `backend/app/config.py` after line 33 (after `ws_monitor_token`):

```python
    # Dashboard auth
    admin_username: str = "admin"
    admin_password: str = ""  # Required in production
    jwt_expire_hours: int = 24
```

- [ ] **Step 2.2: Update .env.example**

Add to `backend/.env.example` at the end:

```bash

# Dashboard Auth
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
JWT_EXPIRE_HOURS=24
```

- [ ] **Step 2.3: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: add auth config settings"
```

---

## Task 3: Create Security Module

**Files:**
- Create: `backend/app/core/security.py`

- [ ] **Step 3.1: Create security.py with JWT and password functions**

Create `backend/app/core/security.py`:

```python
"""Security utilities for JWT and password verification."""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def create_access_token(subject: str) -> str:
    """Create a JWT access token for the given subject (username)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    """
    Decode and verify a JWT token.
    Returns the subject (username) if valid, None otherwise.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None


def verify_password(plain_password: str, username: str) -> bool:
    """
    Verify password against configured admin credentials.
    Simple comparison — no hashing since credentials are from env vars.
    """
    settings = get_settings()
    return username == settings.admin_username and plain_password == settings.admin_password
```

- [ ] **Step 3.2: Verify file created**

Run: `cat backend/app/core/security.py`

Expected: File contents as above

- [ ] **Step 3.3: Commit**

```bash
git add backend/app/core/security.py
git commit -m "feat: add security module with JWT functions"
```

---

## Task 4: Create Auth Schemas

**Files:**
- Create: `backend/app/schemas/auth.py`

- [ ] **Step 4.1: Create auth.py schemas**

Create `backend/app/schemas/auth.py`:

```python
"""Auth request/response schemas."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Current user info."""

    username: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
```

- [ ] **Step 4.2: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "feat: add auth schemas"
```

---

## Task 5: Create Auth API Endpoints

**Files:**
- Create: `backend/app/api/v1/auth.py`
- Modify: `backend/app/main.py:72-85`

- [ ] **Step 5.1: Create auth.py router**

Create `backend/app/api/v1/auth.py`:

```python
"""Authentication API endpoints."""
import logging

from fastapi import APIRouter, HTTPException, Request, Response

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.schemas.auth import LoginRequest, MessageResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the auth cookie with appropriate settings."""
    settings = get_settings()
    max_age = settings.jwt_expire_hours * 3600
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=max_age,
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie."""
    response.delete_cookie(key="access_token")


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response):
    """Authenticate user and set httpOnly cookie."""
    if not verify_password(body.password, body.username):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(body.username)
    _set_auth_cookie(response, token)
    logger.info("User logged in: %s", body.username)
    return UserResponse(username=body.username)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Clear auth cookie."""
    _clear_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(request: Request):
    """Get current authenticated user info."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return UserResponse(username=username)


async def get_current_user(request: Request) -> str:
    """
    Dependency to get the current authenticated user.
    Use with Depends(get_current_user) on protected routes.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username
```

- [ ] **Step 5.2: Include auth router in main.py**

Add to `backend/app/main.py` after line 85 (after analytics router):

```python
from app.api.v1.auth import router as auth_router  # noqa: E402
app.include_router(auth_router)
```

- [ ] **Step 5.3: Verify router is included**

Run: `cd backend && python -c "from app.main import app; print([r.path for r in app.routes if 'auth' in r.path])"`

Expected: Routes containing '/api/v1/auth' paths

- [ ] **Step 5.4: Commit**

```bash
git add backend/app/api/v1/auth.py backend/app/main.py
git commit -m "feat: add auth API endpoints (login/logout/me)"
```

---

## Task 6: Add Auth to Protected Routes

**Files:**
- Modify: `backend/app/api/v1/knowledge.py`
- Modify: `backend/app/api/v1/sessions.py`
- Modify: `backend/app/api/v1/settings.py`
- Modify: `backend/app/api/v1/analytics.py`

- [ ] **Step 6.1: Add auth to knowledge.py**

Add import at top of `backend/app/api/v1/knowledge.py`:

```python
from app.api.v1.auth import get_current_user
```

Add `_: str = Depends(get_current_user)` parameter to each endpoint:

For `create_chunk` (line 62-80):
```python
@router.post("/", response_model=KnowledgeChunkResponse, status_code=201)
async def create_chunk(
    body: KnowledgeChunkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `list_chunks` (line 83-109):
```python
@router.get("/", response_model=KnowledgeListResponse)
async def list_chunks(
    seller_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `update_chunk` (line 112-138):
```python
@router.put("/{chunk_id}", response_model=KnowledgeChunkResponse)
async def update_chunk(
    chunk_id: str,
    body: KnowledgeChunkUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `delete_chunk_endpoint` (line 141-152):
```python
@router.delete("/{chunk_id}", status_code=204)
async def delete_chunk_endpoint(
    chunk_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `preview_knowledge` (line 189-213):
```python
@router.post("/preview", response_model=CsvPreviewResponse)
async def preview_knowledge(
    file: UploadFile,
    _: str = Depends(get_current_user),
):
```

For `upload_knowledge` (line 216-280):
```python
@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    seller_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

- [ ] **Step 6.2: Add auth to sessions.py**

Add import at top of `backend/app/api/v1/sessions.py`:

```python
from app.api.v1.auth import get_current_user
```

Add `_: str = Depends(get_current_user)` to: `start_session` (line 154), `stop_session` (line 218), `get_status` (line 253), `get_history` (line 268), `get_session_messages` (line 285).

For `start_session`:
```python
@router.post("/start", response_model=SessionStatusResponse)
async def start_session(
    body: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SessionStatusResponse:
```

For `stop_session`:
```python
@router.post("/stop")
async def stop_session(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> dict[str, str]:
```

For `get_status`:
```python
@router.get("/status", response_model=SessionStatusResponse)
async def get_status(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> SessionStatusResponse:
```

For `get_history`:
```python
@router.get("/history", response_model=list[SessionResponse])
async def get_history(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> list[SessionResponse]:
```

For `get_session_messages`:
```python
@router.get("/{session_id}/messages", response_model=list[MessageLogResponse])
async def get_session_messages(
    session_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
) -> list[MessageLogResponse]:
```

- [ ] **Step 6.3: Add auth to settings.py**

Add import at top of `backend/app/api/v1/settings.py`:

```python
from app.api.v1.auth import get_current_user
```

Add `_: str = Depends(get_current_user)` to: `get_settings` (line 26), `update_settings` (line 32), `test_reply` (line 51).

For `get_settings`:
```python
@router.get("/", response_model=BotSettingsResponse)
async def get_settings(
    seller_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `update_settings`:
```python
@router.put("/", response_model=BotSettingsResponse)
async def update_settings(
    seller_id: str,
    body: BotSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

For `test_reply`:
```python
@router.post("/test-reply", response_model=TestReplyResponse)
async def test_reply(
    body: TestReplyRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

- [ ] **Step 6.4: Add auth to analytics.py**

Add import at top of `backend/app/api/v1/analytics.py`:

```python
from app.api.v1.auth import get_current_user
```

Add `_: str = Depends(get_current_user)` to `get_analytics`:

```python
@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    seller_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
```

- [ ] **Step 6.5: Commit**

```bash
git add backend/app/api/v1/knowledge.py backend/app/api/v1/sessions.py backend/app/api/v1/settings.py backend/app/api/v1/analytics.py
git commit -m "feat: add auth protection to all API endpoints"
```

---

## Task 7: Update WebSocket to Cookie Auth

**Files:**
- Modify: `backend/app/api/ws.py:5-36`

- [ ] **Step 7.1: Change WebSocket auth from query param to cookie**

Update `backend/app/api/ws.py` - change the `websocket_monitor` function:

```python
@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    # Auth via cookie instead of query param
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    from app.core.security import decode_access_token
    username = decode_access_token(token)
    if not username:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _connections.append(websocket)
    logger.info("Dashboard client connected: %s (%d total)", username, len(_connections))
    try:
        while True:
            # ... rest of the function unchanged ...
```

Remove the `token: str = Query(default="")` parameter and related check.

Full updated function:

```python
@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    # Auth via cookie
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008)
        return

    from app.core.security import decode_access_token
    username = decode_access_token(token)
    if not username:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _connections.append(websocket)
    logger.info("Dashboard client connected: %s (%d total)", username, len(_connections))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WS client, ignoring")
                continue

            msg_type = msg.get("type")
            logger.info("WS command received: %s", msg_type)

            if msg_type == "pause_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = True
                await broadcast({"type": "status", "paused": True})

            elif msg_type == "resume_bot":
                import app.api.v1.sessions as sessions_module
                sessions_module._bot_paused = False
                await broadcast({"type": "status", "paused": False})

            elif msg_type == "manual_reply":
                await _handle_manual_reply(msg)

    except WebSocketDisconnect:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))
    except Exception:
        logger.exception("WebSocket error")
        if websocket in _connections:
            _connections.remove(websocket)
```

Also remove the `Query` import if no longer needed:
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
```

- [ ] **Step 7.2: Commit**

```bash
git add backend/app/api/ws.py
git commit -m "feat: switch WebSocket auth from query param to cookie"
```

---

## Task 8: Frontend - Add credentials to API client

**Files:**
- Modify: `frontend/lib/api.ts:125-152`

- [ ] **Step 8.1: Add credentials: "include" to fetch wrapper**

Update the `request` function in `frontend/lib/api.ts` to include credentials:

```typescript
async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  // Don't set Content-Type for FormData — browser sets it with boundary automatically
  const isFormData = options.body instanceof FormData;
  const res = await fetch(url, {
    credentials: "include",  // ADD THIS LINE
    headers: isFormData
      ? (options.headers ?? {})
      : { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      // ignore parse error
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
```

- [ ] **Step 8.2: Add auth API methods**

Add auth namespace to the `api` object in `frontend/lib/api.ts` before the closing brace:

```typescript
  auth: {
    login(username: string, password: string): Promise<{ username: string }> {
      return request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    },

    logout(): Promise<{ message: string }> {
      return request("/api/v1/auth/logout", { method: "POST" });
    },

    me(): Promise<{ username: string }> {
      return request("/api/v1/auth/me", { method: "GET" });
    },
  },
```

- [ ] **Step 8.3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add auth API methods and credentials to fetch"
```

---

## Task 9: Frontend - Create Login Page

**Files:**
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/components/auth/LoginForm.tsx`

- [ ] **Step 9.1: Create LoginForm component**

Create `frontend/components/auth/LoginForm.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.auth.login(username, password);
      router.push("/monitor");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="username">Username</Label>
        <Input
          id="username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoComplete="username"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? "Logging in..." : "Login"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 9.2: Create login page**

Create `frontend/app/login/page.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">TikTok Live AI Bot</CardTitle>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 9.3: Commit**

```bash
mkdir -p frontend/components/auth frontend/app/login
git add frontend/components/auth/LoginForm.tsx frontend/app/login/page.tsx
git commit -m "feat: add login page and form"
```

---

## Task 10: Frontend - Create Auth Middleware

**Files:**
- Create: `frontend/middleware.ts`

- [ ] **Step 10.1: Create middleware.ts**

Create `frontend/middleware.ts`:

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that don't require authentication
const publicRoutes = ["/login"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (publicRoutes.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for auth cookie
  const token = request.cookies.get("access_token");

  if (!token) {
    // Redirect to login
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Match all routes except static files and api
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
```

- [ ] **Step 10.2: Commit**

```bash
git add frontend/middleware.ts
git commit -m "feat: add auth middleware for protected routes"
```

---

## Task 11: Frontend - Update Layout for Login Page

**Files:**
- Modify: `frontend/app/login/layout.tsx` (create)

- [ ] **Step 11.1: Create login layout without sidebar**

Create `frontend/app/login/layout.tsx`:

```tsx
export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 11.2: Commit**

```bash
git add frontend/app/login/layout.tsx
git commit -m "feat: add login layout without sidebar"
```

---

## Task 12: WebSocket Auto-Reconnect

**Files:**
- Modify: `frontend/lib/ws.ts`

- [ ] **Step 12.1: Add auto-reconnect logic to WSClient**

Replace `frontend/lib/ws.ts` with:

```typescript
// lib/ws.ts — WebSocket singleton client with auto-reconnect

export type WSMessage =
  | {
      type: "comment";
      message_id: string;
      user: string;
      content: string;
      timestamp: string;
    }
  | { type: "reply"; message_id: string; content: string; intent: string; chunks_used: string[] }
  | { type: "status"; connected?: boolean; paused?: boolean; room_id?: number }
  | { type: "error"; message: string }
  | { type: "connection"; status: "connecting" | "connected" | "disconnected" | "reconnecting" };

type Handler<T extends WSMessage = WSMessage> = (msg: T) => void;

export type SendMessage =
  | { type: "pause_bot" }
  | { type: "resume_bot" }
  | { type: "manual_reply"; message_id: string; content: string };

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 16000;

export class WSClient {
  _ws: WebSocket | null = null;
  private _listeners: Map<string, Set<Handler>> = new Map();
  private _url: string = "";
  private _reconnectAttempt: number = 0;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _manualDisconnect: boolean = false;

  connect(url: string): void {
    if (this._ws && this._ws.readyState <= WebSocket.OPEN) return;

    this._url = url;
    this._manualDisconnect = false;
    this._doConnect();
  }

  private _doConnect(): void {
    this._emit({ type: "connection", status: "connecting" });

    this._ws = new WebSocket(this._url);

    this._ws.onopen = () => {
      this._reconnectAttempt = 0;
      this._emit({ type: "connection", status: "connected" });
    };

    this._ws.onmessage = (event: MessageEvent) => {
      let msg: WSMessage;
      try {
        msg = JSON.parse(event.data as string) as WSMessage;
      } catch {
        return;
      }
      this._emit(msg);
    };

    this._ws.onerror = () => {
      // Suppress — onclose will follow
    };

    this._ws.onclose = (event) => {
      this._emit({ type: "connection", status: "disconnected" });

      // Don't reconnect if manually disconnected or normal close
      if (this._manualDisconnect || event.code === 1000) {
        return;
      }

      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    if (this._reconnectAttempt >= MAX_RETRIES) {
      this._emit({ type: "error", message: "Max reconnection attempts reached" });
      return;
    }

    const delay = Math.min(
      BASE_DELAY_MS * Math.pow(2, this._reconnectAttempt),
      MAX_DELAY_MS
    );

    this._reconnectAttempt++;
    this._emit({ type: "connection", status: "reconnecting" });

    this._reconnectTimer = setTimeout(() => {
      this._doConnect();
    }, delay);
  }

  private _emit(msg: WSMessage): void {
    const handlers = this._listeners.get(msg.type);
    if (handlers) {
      handlers.forEach((h) => h(msg));
    }
  }

  disconnect(): void {
    this._manualDisconnect = true;

    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }

    if (this._ws) {
      this._ws.close(1000);
      this._ws = null;
    }
  }

  send(msg: SendMessage): boolean {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }

  on<T extends WSMessage>(type: T["type"], handler: Handler<T>): () => void {
    if (!this._listeners.has(type)) {
      this._listeners.set(type, new Set());
    }
    this._listeners.get(type)!.add(handler as Handler);
    return () => this.off(type, handler);
  }

  off<T extends WSMessage>(type: T["type"], handler: Handler<T>): void {
    this._listeners.get(type)?.delete(handler as Handler);
  }
}

export const wsClient = new WSClient();
```

- [ ] **Step 12.2: Commit**

```bash
git add frontend/lib/ws.ts
git commit -m "feat: add WebSocket auto-reconnect with exponential backoff"
```

---

## Task 13: Update useWebSocket Hook

**Files:**
- Modify: `frontend/hooks/useWebSocket.ts`

- [ ] **Step 13.1: Remove token query param, use cookie-based auth**

Replace `frontend/hooks/useWebSocket.ts` with:

```typescript
"use client";
// hooks/useWebSocket.ts — React hook for the WS singleton

import { useEffect, useRef } from "react";
import { wsClient, type WSMessage } from "@/lib/ws";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

/**
 * Subscribes to wsClient events for the handler types present at mount time.
 * Handler *values* may change between renders — the latest version is always
 * called via handlersRef. However, new handler *keys* added after mount are
 * NOT subscribed. Pass a stable, complete set of handler keys.
 *
 * Auto-reconnects when connection is lost (handled by WSClient).
 * Auth is via httpOnly cookie (no token in URL).
 */
export function useWebSocket(
  handlers: Partial<{
    [T in WSMessage as T["type"]]: (msg: Extract<WSMessage, { type: T["type"] }>) => void;
  }>,
) {
  // Stable ref — won't cause re-renders when handlers change identity
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const url = `${WS_URL}/ws/monitor`;

    wsClient.connect(url);

    const unsubs = (Object.keys(handlers) as Array<keyof typeof handlers>).map(
      (type) =>
        wsClient.on(type, (msg) => {
          (
            handlersRef.current[type] as
              | ((m: typeof msg) => void)
              | undefined
          )?.(msg);
        }),
    );

    return () => {
      unsubs.forEach((u) => u());
    };
    // Only run once — handlers are accessed via ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
```

- [ ] **Step 13.2: Update frontend .env.example**

Remove WS_TOKEN from `frontend/.env.example`:

```bash
# Backend REST API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Backend WebSocket
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Single-seller v1: ID of the Seller record in the backend DB
NEXT_PUBLIC_SELLER_ID=your-seller-id-here
```

- [ ] **Step 13.3: Commit**

```bash
git add frontend/hooks/useWebSocket.ts frontend/.env.example
git commit -m "feat: update useWebSocket for cookie-based auth"
```

---

## Task 14: feedItems Limit (200 items)

**Files:**
- Modify: `frontend/app/monitor/page.tsx`

- [ ] **Step 14.1: Add MAX_FEED_ITEMS constant and limit logic**

Update `frontend/app/monitor/page.tsx`:

Add constant at top of file after imports:

```typescript
const MAX_FEED_ITEMS = 200;
```

Update the `comment` handler in `useWebSocket` to limit items:

```typescript
useWebSocket({
  comment: (msg) => {
    addOrUpdate((items) => {
      const updated = [...items, { ...msg }];
      // Keep only the most recent MAX_FEED_ITEMS items
      if (updated.length > MAX_FEED_ITEMS) {
        const trimmed = updated.slice(-MAX_FEED_ITEMS);
        // Clear selection if selected item was removed
        const removedIds = new Set(
          updated.slice(0, updated.length - MAX_FEED_ITEMS).map((i) => i.message_id)
        );
        if (selectedId && removedIds.has(selectedId)) {
          setSelectedId(null);
        }
        return trimmed;
      }
      return updated;
    });
  },
  // ... rest unchanged
});
```

However, since `setSelectedId` is not accessible inside the callback, we need a different approach. Update the full file:

```typescript
"use client";
import { useState, useCallback, useEffect } from "react";
import { toast } from "sonner";
import { SessionControl } from "@/components/monitor/SessionControl";
import { CommentFeed, type FeedItem } from "@/components/monitor/CommentFeed";
import { BotControls } from "@/components/monitor/BotControls";
import { useSession } from "@/hooks/useSession";
import { useWebSocket } from "@/hooks/useWebSocket";

const MAX_FEED_ITEMS = 200;

export default function MonitorPage() {
  const { state, loading, start, stop, refresh } = useSession();
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [paused, setPaused] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const addOrUpdate = useCallback((updater: (items: FeedItem[]) => FeedItem[]) => {
    setFeedItems((prev) => {
      const updated = updater(prev);
      // Limit to MAX_FEED_ITEMS
      return updated.length > MAX_FEED_ITEMS
        ? updated.slice(-MAX_FEED_ITEMS)
        : updated;
    });
  }, []);

  // Clear selection if selected item is no longer in feed
  useEffect(() => {
    if (selectedId && !feedItems.some((item) => item.message_id === selectedId)) {
      setSelectedId(null);
    }
  }, [feedItems, selectedId]);

  useWebSocket({
    comment: (msg) => {
      addOrUpdate((items) => [...items, { ...msg }]);
    },
    reply: (msg) => {
      addOrUpdate((items) =>
        items.map((item) =>
          item.message_id === msg.message_id
            ? { ...item, reply: msg.content, intent: msg.intent }
            : item,
        ),
      );
    },
    status: (msg) => {
      if (typeof msg.connected === "boolean") {
        refresh();
      }
      if (typeof msg.paused === "boolean") {
        setPaused(msg.paused);
      }
    },
    error: (msg) => {
      toast.error(msg.message);
    },
  });

  async function handleStart() {
    try {
      await start();
      toast.success("Session started");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to start session");
    }
  }

  async function handleStop() {
    try {
      await stop();
      setFeedItems([]);
      toast.success("Session stopped");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to stop session");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Live Monitor</h2>
        <SessionControl
          state={state}
          loading={loading}
          onStart={handleStart}
          onStop={handleStop}
        />
      </div>

      <div className="grid grid-cols-[1fr_260px] gap-4">
        <CommentFeed
          items={feedItems}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        <div className="space-y-4 rounded-md border p-4">
          <h3 className="font-semibold text-sm">Bot Controls</h3>
          <BotControls
            paused={paused}
            connected={state.connected}
            replyTargetId={selectedId}
          />
          {state.session && (
            <div className="text-xs text-muted-foreground space-y-1 border-t pt-3">
              <p>Session ID: <span className="font-mono">{state.session.id.slice(0, 8)}…</span></p>
              <p>Started: {new Date(state.session.started_at).toLocaleTimeString()}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 14.2: Commit**

```bash
git add frontend/app/monitor/page.tsx
git commit -m "feat: limit feedItems to 200 most recent items"
```

---

## Task 15: Analytics Date Range Filter - Backend

**Files:**
- Modify: `backend/app/api/v1/analytics.py`

- [ ] **Step 15.1: Add date filter params to analytics endpoint**

Update `backend/app/api/v1/analytics.py`:

```python
"""Analytics API — aggregated stats for a seller."""
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    seller_id: str,
    start_date: date | None = Query(default=None, description="Filter sessions from this date (inclusive)"),
    end_date: date | None = Query(default=None, description="Filter sessions until this date (inclusive)"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user),
):
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Base session filter
    session_filter = LiveSession.seller_id == seller_id

    # Add date filters if provided
    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        session_filter = session_filter & (LiveSession.started_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, time.max)
        session_filter = session_filter & (LiveSession.started_at <= end_datetime)

    total_sessions = await db.scalar(
        select(func.count(LiveSession.id)).where(session_filter)
    ) or 0

    session_subquery = select(LiveSession.id).where(session_filter).scalar_subquery()

    total_comments = await db.scalar(
        select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_subquery))
    ) or 0

    total_replies = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_subquery),
            MessageLog.reply.isnot(None),
        )
    ) or 0

    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_subquery))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    unanswered_count = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_subquery),
            MessageLog.reply.is_(None),
            MessageLog.intent.notin_(["skipped", "blacklist"]),
        )
    ) or 0

    return AnalyticsResponse(
        total_sessions=total_sessions,
        total_comments=total_comments,
        total_replies=total_replies,
        reply_rate=reply_rate,
        intent_breakdown=intent_breakdown,
        unanswered_count=unanswered_count,
    )
```

- [ ] **Step 15.2: Commit**

```bash
git add backend/app/api/v1/analytics.py
git commit -m "feat: add date range filter to analytics API"
```

---

## Task 16: Analytics Date Range Filter - Frontend API

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 16.1: Update analytics.get() to accept date params**

Update the `analytics` namespace in `frontend/lib/api.ts`:

```typescript
  analytics: {
    get(params: { start_date?: string; end_date?: string } = {}): Promise<AnalyticsData> {
      const queryParams: Record<string, string | number> = { seller_id: SELLER_ID };
      if (params.start_date) queryParams.start_date = params.start_date;
      if (params.end_date) queryParams.end_date = params.end_date;
      return request(`/api/v1/analytics/${qs(queryParams)}`, {
        method: "GET",
      });
    },
  },
```

- [ ] **Step 16.2: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add date params to analytics API client"
```

---

## Task 17: Analytics Date Range Filter - Frontend UI

**Files:**
- Create: `frontend/components/analytics/DateRangeFilter.tsx`
- Modify: `frontend/app/analytics/page.tsx`

- [ ] **Step 17.1: Create DateRangeFilter component**

Create `frontend/components/analytics/DateRangeFilter.tsx`:

```tsx
"use client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface DateRangeFilterProps {
  startDate: string;
  endDate: string;
  onStartChange: (date: string) => void;
  onEndChange: (date: string) => void;
  onApply: () => void;
  loading: boolean;
}

export function DateRangeFilter({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  onApply,
  loading,
}: DateRangeFilterProps) {
  // Quick presets
  const setPreset = (days: number | null) => {
    if (days === null) {
      onStartChange("");
      onEndChange("");
    } else {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - days + 1);
      onStartChange(start.toISOString().split("T")[0]);
      onEndChange(end.toISOString().split("T")[0]);
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="space-y-1">
        <Label htmlFor="start-date" className="text-xs">
          Từ ngày
        </Label>
        <Input
          id="start-date"
          type="date"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="end-date" className="text-xs">
          Đến ngày
        </Label>
        <Input
          id="end-date"
          type="date"
          value={endDate}
          onChange={(e) => onEndChange(e.target.value)}
          className="w-36"
        />
      </div>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(1)}
          className="text-xs"
        >
          Hôm nay
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(7)}
          className="text-xs"
        >
          7 ngày
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(30)}
          className="text-xs"
        >
          30 ngày
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPreset(null)}
          className="text-xs"
        >
          Tất cả
        </Button>
      </div>

      <Button size="sm" onClick={onApply} disabled={loading}>
        {loading ? "Đang tải..." : "Áp dụng"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 17.2: Update analytics page to use date filter**

Update `frontend/app/analytics/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatsCards } from "@/components/analytics/StatsCards";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { UnansweredSummary } from "@/components/analytics/UnansweredSummary";
import { DateRangeFilter } from "@/components/analytics/DateRangeFilter";
import { api, type AnalyticsData } from "@/lib/api";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  function load() {
    setError(false);
    setLoading(true);
    api.analytics
      .get({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      .then(setData)
      .catch(() => {
        setData(null);
        setError(true);
        toast.error("Không tải được thống kê");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Thống kê buổi live
            {startDate && endDate
              ? ` từ ${startDate} đến ${endDate}`
              : " (tất cả thời gian)"}
          </p>
        </div>
      </div>

      <DateRangeFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onApply={load}
        loading={loading}
      />

      {error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Không tải được dữ liệu.</p>
          <button
            onClick={load}
            className="text-sm underline"
          >
            Thử lại
          </button>
        </div>
      )}

      {loading && !data && (
        <p className="text-sm text-muted-foreground">Đang tải…</p>
      )}

      {data && (
        <div className="space-y-6">
          <StatsCards data={data} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <IntentBreakdown breakdown={data.intent_breakdown} />
            <UnansweredSummary count={data.unanswered_count} />
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 17.3: Commit**

```bash
git add frontend/components/analytics/DateRangeFilter.tsx frontend/app/analytics/page.tsx
git commit -m "feat: add date range filter UI to analytics page"
```

---

## Task 18: Update Tests

**Files:**
- Modify: `frontend/tests/unit/ws.test.ts`

- [ ] **Step 18.1: Update WebSocket tests for auto-reconnect**

Update `frontend/tests/unit/ws.test.ts` to test new reconnect behavior:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WSClient } from "@/lib/ws";

// ── Mock WebSocket ───────────────────────────────────────────────────────────
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send = vi.fn();

  close(code = 1000) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }
}

vi.stubGlobal("WebSocket", MockWebSocket);

describe("WSClient", () => {
  let wsClient: WSClient;
  let mockWS: MockWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    wsClient = new WSClient();
    wsClient.connect("ws://localhost:8000/ws/monitor");
    mockWS = wsClient._ws as unknown as MockWebSocket;
  });

  afterEach(() => {
    wsClient.disconnect();
    vi.useRealTimers();
  });

  it("connects to the WebSocket server", async () => {
    await vi.runAllTimersAsync();
    expect(mockWS.readyState).toBe(MockWebSocket.OPEN);
  });

  it("emits connection status on connect", async () => {
    const handler = vi.fn();
    wsClient.on("connection", handler);
    await vi.runAllTimersAsync();
    expect(handler).toHaveBeenCalledWith({ type: "connection", status: "connected" });
  });

  it("dispatches messages to registered handlers", async () => {
    await vi.runAllTimersAsync();
    const handler = vi.fn();
    wsClient.on("comment", handler);

    const msg = { type: "comment", message_id: "1", user: "u", content: "hi", timestamp: "" };
    mockWS.onmessage?.({ data: JSON.stringify(msg) });

    expect(handler).toHaveBeenCalledWith(msg);
  });

  it("unsubscribes handler when calling returned function", async () => {
    await vi.runAllTimersAsync();
    const handler = vi.fn();
    const unsub = wsClient.on("comment", handler);
    unsub();

    const msg = { type: "comment", message_id: "1", user: "u", content: "hi", timestamp: "" };
    mockWS.onmessage?.({ data: JSON.stringify(msg) });

    expect(handler).not.toHaveBeenCalled();
  });

  it("sends messages when connected", async () => {
    await vi.runAllTimersAsync();
    const result = wsClient.send({ type: "pause_bot" });
    expect(result).toBe(true);
    expect(mockWS.send).toHaveBeenCalledWith('{"type":"pause_bot"}');
  });

  it("returns false when sending while disconnected", () => {
    wsClient.disconnect();
    const result = wsClient.send({ type: "pause_bot" });
    expect(result).toBe(false);
  });

  it("closes the WebSocket connection", async () => {
    await vi.runAllTimersAsync();
    wsClient.disconnect();
    expect(mockWS.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("does not auto-reconnect after manual disconnect", async () => {
    await vi.runAllTimersAsync();
    wsClient.disconnect();

    // Advance timers - should not reconnect
    await vi.advanceTimersByTimeAsync(5000);
    expect(wsClient._ws).toBeNull();
  });

  it("schedules reconnect on abnormal close", async () => {
    await vi.runAllTimersAsync();
    const connectionHandler = vi.fn();
    wsClient.on("connection", connectionHandler);

    // Simulate abnormal close
    mockWS.onclose?.({ code: 1006 });

    expect(connectionHandler).toHaveBeenCalledWith({ type: "connection", status: "disconnected" });
    expect(connectionHandler).toHaveBeenCalledWith({ type: "connection", status: "reconnecting" });
  });
});
```

- [ ] **Step 18.2: Run tests**

Run: `cd frontend && npm test`

Expected: All tests pass

- [ ] **Step 18.3: Commit**

```bash
git add frontend/tests/unit/ws.test.ts
git commit -m "test: update WebSocket tests for auto-reconnect"
```

---

## Task 19: Final Verification

- [ ] **Step 19.1: Run backend tests**

Run: `cd backend && pytest -v`

Expected: All tests pass (some may fail due to auth - will need test fixtures update)

- [ ] **Step 19.2: Run frontend tests**

Run: `cd frontend && npm test`

Expected: All tests pass

- [ ] **Step 19.3: Run linter**

Run: `cd backend && ruff check . && cd ../frontend && npm run lint`

Expected: No errors

- [ ] **Step 19.4: Manual test login flow**

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Visit http://localhost:3000 → should redirect to /login
4. Login with ADMIN_USERNAME/ADMIN_PASSWORD from .env
5. Should redirect to /monitor
6. Verify WebSocket connects (check console/network tab)
7. Visit /analytics → date filter should work

- [ ] **Step 19.5: Final commit**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```

---

## Summary

| Feature | Files Changed | Test |
|---------|---------------|------|
| JWT Auth | 12 backend + 6 frontend | Login flow manual test |
| WebSocket Auto-Reconnect | `lib/ws.ts` | Unit tests in `ws.test.ts` |
| feedItems Limit | `monitor/page.tsx` | Manual test |
| Analytics Date Filter | `analytics.py` + 3 frontend | Manual test |
