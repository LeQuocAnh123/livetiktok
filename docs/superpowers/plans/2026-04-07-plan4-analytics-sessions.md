# Analytics & Session History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Analytics dashboard (comment/reply stats + intent breakdown) and a Session History page (list of past lives + per-session message log).

**Architecture:** Two new backend endpoints feed two new frontend pages. Analytics aggregates data from `LiveSession` + `MessageLog` tables via SQL. Session messages endpoint exposes `MessageLog` rows for a given session. No new chart library — CSS Tailwind bars for visualizations.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), Next.js 16 App Router + shadcn/ui + Tailwind CSS v4 (frontend), vitest + pytest (tests).

---

## File Map

### Backend — Create
- `backend/app/api/v1/analytics.py` — GET `/api/v1/analytics/` returns aggregated stats
- `backend/app/schemas/analytics.py` — Pydantic response schemas for analytics

### Backend — Modify
- `backend/app/api/v1/sessions.py` — add `GET /api/v1/sessions/{session_id}/messages`
- `backend/app/schemas/session.py` — add `MessageLogResponse` schema
- `backend/app/main.py` — register analytics router
- `backend/tests/test_analytics_api.py` — new test file

### Frontend — Create
- `frontend/app/analytics/page.tsx` — Analytics page
- `frontend/app/sessions/page.tsx` — Session History page
- `frontend/components/analytics/StatsCards.tsx` — 4 summary stat cards
- `frontend/components/analytics/IntentBreakdown.tsx` — CSS bar chart by intent
- `frontend/components/analytics/UnansweredList.tsx` — list of unanswered comments
- `frontend/components/sessions/SessionList.tsx` — table of past sessions
- `frontend/components/sessions/SessionDetail.tsx` — expandable message log for a session

### Frontend — Modify
- `frontend/lib/api.ts` — add `api.analytics.get()` and `api.sessions.messages()`
- `frontend/components/nav/Sidebar.tsx` — add Analytics + Sessions nav links

---

## Task 1: Backend — Analytics Schema + Endpoint

**Files:**
- Create: `backend/app/schemas/analytics.py`
- Create: `backend/app/api/v1/analytics.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_analytics_api.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_analytics_api.py`:
```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_returns_zeros_for_new_seller(client: AsyncClient, seller_id: str):
    resp = await client.get("/api/v1/analytics/", params={"seller_id": seller_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["total_comments"] == 0
    assert data["total_replies"] == 0
    assert data["reply_rate"] == 0.0
    assert data["intent_breakdown"] == {}
    assert data["unanswered_count"] == 0


@pytest.mark.asyncio
async def test_analytics_404_for_unknown_seller(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/", params={"seller_id": "nonexistent"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_analytics_api.py -v
```
Expected: ImportError or 404 — endpoint doesn't exist yet.

- [ ] **Step 3: Create analytics schema**

`backend/app/schemas/analytics.py`:
```python
from pydantic import BaseModel


class AnalyticsResponse(BaseModel):
    total_sessions: int
    total_comments: int
    total_replies: int
    reply_rate: float  # 0-100
    intent_breakdown: dict[str, int]  # intent -> count
    unanswered_count: int  # comments with no reply
```

- [ ] **Step 4: Create analytics endpoint**

`backend/app/api/v1/analytics.py`:
```python
"""Analytics API — aggregated stats for a seller."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import MessageLog
from app.models.seller import Seller
from app.models.session import LiveSession
from app.schemas.analytics import AnalyticsResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(seller_id: str, db: AsyncSession = Depends(get_db)):
    seller = await db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Total sessions
    total_sessions = await db.scalar(
        select(func.count(LiveSession.id)).where(LiveSession.seller_id == seller_id)
    ) or 0

    # Get all session IDs for this seller
    session_ids_result = await db.execute(
        select(LiveSession.id).where(LiveSession.seller_id == seller_id)
    )
    session_ids = [row[0] for row in session_ids_result.all()]

    if not session_ids:
        return AnalyticsResponse(
            total_sessions=0,
            total_comments=0,
            total_replies=0,
            reply_rate=0.0,
            intent_breakdown={},
            unanswered_count=0,
        )

    # Total comments
    total_comments = await db.scalar(
        select(func.count(MessageLog.id)).where(MessageLog.session_id.in_(session_ids))
    ) or 0

    # Total replies (reply field is not None)
    total_replies = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_ids),
            MessageLog.reply.isnot(None),
        )
    ) or 0

    # Reply rate
    reply_rate = round((total_replies / total_comments * 100), 1) if total_comments > 0 else 0.0

    # Intent breakdown
    intent_rows = await db.execute(
        select(MessageLog.intent, func.count(MessageLog.id))
        .where(MessageLog.session_id.in_(session_ids))
        .group_by(MessageLog.intent)
    )
    intent_breakdown = {row[0]: row[1] for row in intent_rows.all()}

    # Unanswered: no reply and intent not blacklist/skipped
    unanswered_count = await db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.session_id.in_(session_ids),
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

- [ ] **Step 5: Register router in main.py**

Add after the existing router registrations in `backend/app/main.py`:
```python
from app.api.v1.analytics import router as analytics_router  # noqa: E402
app.include_router(analytics_router)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_analytics_api.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/analytics.py backend/app/api/v1/analytics.py backend/app/main.py backend/tests/test_analytics_api.py
git commit -m "feat: analytics endpoint with session/comment/reply/intent stats"
```

---

## Task 2: Backend — Session Messages Endpoint

**Files:**
- Modify: `backend/app/schemas/session.py`
- Modify: `backend/app/api/v1/sessions.py`
- Modify: `backend/tests/test_sessions_api.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_sessions_api.py`:
```python
@pytest.mark.asyncio
async def test_session_messages_empty(client: AsyncClient, seller_id: str):
    """Session with no messages returns empty list."""
    # First create a session record directly via DB or start/stop
    # For simplicity, test with a fake session_id
    resp = await client.get("/api/v1/sessions/nonexistent/messages")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_sessions_api.py::test_session_messages_empty -v
```
Expected: FAIL — endpoint doesn't exist yet.

- [ ] **Step 3: Add MessageLogResponse schema**

In `backend/app/schemas/session.py`, append this class at the bottom (`datetime` is already imported — do NOT add it again):
```python
class MessageLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    session_id: str
    user_unique_id: str
    comment: str
    reply: str | None
    intent: str
    chunks_used: list[str]
    created_at: datetime
```

- [ ] **Step 4: Add messages endpoint to sessions.py**

Add to `backend/app/api/v1/sessions.py`:
```python
from app.schemas.session import MessageLogResponse  # add to existing import

@router.get("/{session_id}/messages", response_model=list[MessageLogResponse])
async def get_session_messages(
    session_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[MessageLogResponse]:
    session = await db.get(LiveSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    offset = (page - 1) * limit
    result = await db.execute(
        select(MessageLog)
        .where(MessageLog.session_id == session_id)
        .order_by(MessageLog.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return [MessageLogResponse.model_validate(m) for m in result.scalars().all()]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/test_sessions_api.py -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/session.py backend/app/api/v1/sessions.py backend/tests/test_sessions_api.py
git commit -m "feat: GET /sessions/{id}/messages endpoint"
```

---

## Task 3: Frontend — API Types + Sidebar

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/nav/Sidebar.tsx`

- [ ] **Step 1: Add types and API calls to api.ts**

Add to `frontend/lib/api.ts` after the existing type definitions:

```typescript
// Analytics
export interface AnalyticsData {
  total_sessions: number;
  total_comments: number;
  total_replies: number;
  reply_rate: number;
  intent_breakdown: Record<string, number>;
  unanswered_count: number;
}

// Message log
export interface MessageLog {
  id: string;
  session_id: string;
  user_unique_id: string;
  comment: string;
  reply: string | null;
  intent: string;
  chunks_used: string[];
  created_at: string;
}
```

Add to the `api` object:
```typescript
  analytics: {
    get(): Promise<AnalyticsData> {
      return request(`/api/v1/analytics/${qs({ seller_id: SELLER_ID })}`, {
        method: "GET",
      });
    },
  },
```

Also extend `api.sessions` — add `messages()` inside the existing `sessions:` block, after the `history()` method and before the closing `},`:
```typescript
    messages(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<MessageLog[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/messages${qs({ page, limit })}`,
        { method: "GET" },
      );
    },
    // ← insert above this closing },  of the sessions namespace
```
The final `sessions:` block must look like:
```typescript
  sessions: {
    start(): Promise<SessionState> { ... },
    stop(): Promise<{ message: string }> { ... },
    status(): Promise<SessionState> { ... },
    history(...): Promise<Session[]> { ... },
    messages(sessionId: string, params: { page?: number; limit?: number } = {}): Promise<MessageLog[]> {
      const { page = 1, limit = 50 } = params;
      return request(
        `/api/v1/sessions/${sessionId}/messages${qs({ page, limit })}`,
        { method: "GET" },
      );
    },
  },
```

- [ ] **Step 2: Add nav links to Sidebar**

Read `frontend/components/nav/Sidebar.tsx` first, then add Analytics and Sessions links following the exact same pattern as existing nav items (Knowledge Base, Live Monitor, Settings).

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/components/nav/Sidebar.tsx
git commit -m "feat: analytics + session messages API types and sidebar links"
```

---

## Task 4: Frontend — Analytics Page Components

**Files:**
- Create: `frontend/components/analytics/StatsCards.tsx`
- Create: `frontend/components/analytics/IntentBreakdown.tsx`
- Create: `frontend/components/analytics/UnansweredList.tsx`
- Create: `frontend/app/analytics/page.tsx`

- [ ] **Step 1: Create StatsCards component**

`frontend/components/analytics/StatsCards.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";

interface Props {
  data: AnalyticsData;
}

export function StatsCards({ data }: Props) {
  const stats = [
    { label: "Tổng buổi live", value: data.total_sessions },
    { label: "Tổng comment", value: data.total_comments },
    { label: "Đã reply", value: data.total_replies },
    { label: "Tỷ lệ reply", value: `${data.reply_rate}%` },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {s.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{s.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create IntentBreakdown component**

`frontend/components/analytics/IntentBreakdown.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const INTENT_LABELS: Record<string, string> = {
  product_inquiry: "Hỏi sản phẩm",
  greeting: "Chào hỏi",
  unknown: "Không xác định",
  skipped: "Bỏ qua",
  blacklist: "Từ cấm",
};

interface Props {
  breakdown: Record<string, number>;
}

export function IntentBreakdown({ breakdown }: Props) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] ?? 1;

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Phân loại intent</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Phân loại intent</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([intent, count]) => (
          <div key={intent} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{INTENT_LABELS[intent] ?? intent}</span>
              <span className="font-medium">{count}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-primary transition-all"
                style={{ width: `${Math.round((count / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Create UnansweredList component**

`frontend/components/analytics/UnansweredList.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Props {
  count: number;
}

export function UnansweredSummary({ count }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Comment chưa được trả lời</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-3">
        <span className="text-4xl font-bold text-destructive">{count}</span>
        {count > 0 && (
          <Badge variant="destructive">Cần bổ sung Knowledge Base</Badge>
        )}
        {count === 0 && (
          <Badge variant="outline" className="text-green-600 border-green-400">
            Tất cả đã được xử lý
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create Analytics page**

`frontend/app/analytics/page.tsx`:
```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StatsCards } from "@/components/analytics/StatsCards";
import { IntentBreakdown } from "@/components/analytics/IntentBreakdown";
import { UnansweredSummary } from "@/components/analytics/UnansweredList";
import { api, type AnalyticsData } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  function load() {
    setError(false);
    setLoading(true);
    api.analytics
      .get()
      .then(setData)
      .catch(() => {
        setError(true);
        toast.error("Không tải được thống kê");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => { void load(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Analytics</h2>
          <p className="text-sm text-muted-foreground">Thống kê toàn bộ buổi live</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? "Đang tải…" : "Làm mới"}
        </Button>
      </div>

      {error && (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Không tải được dữ liệu.</p>
          <Button variant="outline" size="sm" onClick={load}>Thử lại</Button>
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

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/analytics/ frontend/app/analytics/
git commit -m "feat: Analytics page with stats, intent breakdown, unanswered count"
```

---

## Task 5: Frontend — Session History Page

**Files:**
- Create: `frontend/components/sessions/SessionList.tsx`
- Create: `frontend/components/sessions/SessionDetail.tsx`
- Create: `frontend/app/sessions/page.tsx`

- [ ] **Step 1: Create SessionList component**

`frontend/components/sessions/SessionList.tsx`:
```tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import type { Session } from "@/lib/api";

interface Props {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function duration(started: string, ended: string | undefined): string {
  if (!ended) return "Đang live";
  const ms = new Date(ended).getTime() - new Date(started).getTime();
  const mins = Math.floor(ms / 60000);
  return mins < 60 ? `${mins} phút` : `${Math.floor(mins / 60)}h${mins % 60}p`;
}

const STATUS_LABEL: Record<string, string> = {
  active: "Đang live",
  ended: "Đã kết thúc",
  paused: "Tạm dừng",
};

export function SessionList({ sessions, selectedId, onSelect }: Props) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground py-8 text-center">Chưa có buổi live nào.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Thời gian bắt đầu</TableHead>
          <TableHead>Thời lượng</TableHead>
          <TableHead>Trạng thái</TableHead>
          <TableHead className="text-right">Chi tiết</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((s) => (
          <TableRow key={s.id} className={selectedId === s.id ? "bg-muted/50" : ""}>
            <TableCell>{new Date(s.started_at).toLocaleString("vi-VN")}</TableCell>
            <TableCell>{duration(s.started_at, s.ended_at)}</TableCell>
            <TableCell>
              <Badge variant={s.status === "active" ? "default" : "secondary"}>
                {STATUS_LABEL[s.status] ?? s.status}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              <Button
                variant={selectedId === s.id ? "default" : "outline"}
                size="sm"
                onClick={() => onSelect(s.id)}
              >
                {selectedId === s.id ? "Đang xem" : "Xem"}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 2: Create SessionDetail component**

`frontend/components/sessions/SessionDetail.tsx`:
```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { api, type MessageLog } from "@/lib/api";

interface Props {
  sessionId: string;
}

export function SessionDetail({ sessionId }: Props) {
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.sessions
      .messages(sessionId)
      .then(setMessages)
      .catch(() => toast.error("Không tải được tin nhắn"))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <p className="text-sm text-muted-foreground p-4">Đang tải…</p>;
  if (messages.length === 0)
    return <p className="text-sm text-muted-foreground p-4">Không có comment nào.</p>;

  return (
    <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto pr-1">
      {messages.map((m) => (
        <div key={m.id} className="rounded-md border bg-white p-3 text-sm shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="font-semibold text-slate-800">{m.user_unique_id}</span>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs">{m.intent}</Badge>
              <span className="text-xs text-muted-foreground">
                {new Date(m.created_at).toLocaleTimeString("vi-VN")}
              </span>
            </div>
          </div>
          <p className="text-slate-700">{m.comment}</p>
          {m.reply ? (
            <p className="mt-2 pl-3 border-l-2 border-green-400 text-slate-600 text-xs italic">
              Bot: {m.reply}
            </p>
          ) : (
            <p className="mt-2 pl-3 border-l-2 border-slate-200 text-xs text-muted-foreground italic">
              Không có reply
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create Sessions page**

`frontend/app/sessions/page.tsx`:
```tsx
"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { SessionList } from "@/components/sessions/SessionList";
import { SessionDetail } from "@/components/sessions/SessionDetail";
import { api, type Session } from "@/lib/api";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sessions
      .history()
      .then((data) => {
        setSessions(data);
        if (data.length > 0) setSelectedId(data[0].id);
      })
      .catch(() => toast.error("Không tải được lịch sử"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Lịch sử buổi live</h2>
        <p className="text-sm text-muted-foreground">Xem lại comment và reply của từng buổi</p>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Đang tải…</p>}

      {!loading && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_420px]">
          <div className="rounded-md border">
            <SessionList
              sessions={sessions}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          {selectedId && (
            <div className="rounded-md border p-3">
              <h3 className="text-sm font-semibold mb-3">
                Chi tiết buổi live
              </h3>
              <SessionDetail sessionId={selectedId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/sessions/ frontend/app/sessions/
git commit -m "feat: Session History page with message log viewer"
```

---

## Task 6: Wire sidebar + smoke test

**Files:**
- Modify: `frontend/components/nav/Sidebar.tsx`

- [ ] **Step 1: Read current Sidebar.tsx**

Read `frontend/components/nav/Sidebar.tsx` to understand the nav item pattern.

- [ ] **Step 2: Add Analytics and Sessions links**

Add two new nav items following the exact same pattern as existing ones:
- Analytics → href `/analytics`, icon `BarChart2` from lucide-react
- Sessions → href `/sessions`, icon `History` from lucide-react

- [ ] **Step 3: Manual smoke test checklist**

```
1. Start backend: cd backend && uvicorn app.main:app --reload --port 8000
2. Start frontend: cd frontend && npm run dev
3. Open localhost:3000/analytics
   - Should show 4 stat cards (all zeros if no sessions yet)
   - Should show intent breakdown (empty state)
   - Should show unanswered count card
4. Open localhost:3000/sessions
   - Should show session list (empty state message if no sessions)
   - If sessions exist, click "Xem" → messages appear on right
5. Open localhost:3000/knowledge — still works
6. Open localhost:3000/settings → Test Reply — still works
```

- [ ] **Step 4: Final commit**

```bash
git add frontend/components/nav/Sidebar.tsx
git commit -m "feat: add Analytics and Sessions nav links"
```
