# TikTok Live AI Bot — Design Spec

**Date:** 2026-04-06
**Status:** Approved
**Author:** Lequocanh123

---

## 1. Mục tiêu

Xây dựng hệ thống AI bot tự động đọc comment TikTok Live, truy vấn knowledge base của seller, và reply lại comment bằng tiếng Việt tự nhiên thông qua RAG Pipeline.

**Constraints:**
- Solo developer, 6-8 tuần
- Giai đoạn đầu: single-seller, thiết kế sẵn cho multi-tenant
- AI provider có thể swap (không lock-in)
- Dev đơn giản, production qua Docker

---

## 2. Kiến trúc tổng thể

```
[TikTok Live Stream]
       │ WebSocket
       ▼
[TikTokLive lib]  ←── lib gốc isaackogan/TikTokLive (KHÔNG SỬA)
       │ CommentEvent
       ▼
[backend/core/tiktok/listener.py]
       │
       ▼
[Filter Layer]
  ├── Blacklist keywords
  ├── Intent detection
  └── Cooldown per user
       │ pass
       ▼
[RAG Pipeline]
  1. Embed comment (OpenAI / local)
  2. ChromaDB search → top-3 chunks
  3. Build prompt (System + Context + Comment)
  4. AI Provider → reply text
       │
       ▼
[Throttle: random 5–15s]
       │
       ▼
[replier.py → send_room_chat()]
       │
       ▼
[MessageLog → DB] + [WebSocket → Frontend Dashboard]
```

---

## 3. Project Structure

```
livetiktok/
├── TikTokLive/                      # lib gốc — KHÔNG CHỈNH SỬA
│   ├── client/
│   ├── events/
│   └── proto/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # pydantic-settings từ .env
│   │   ├── database.py              # SQLAlchemy setup
│   │   │
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── knowledge.py     # CRUD knowledge base
│   │   │   │   ├── sessions.py      # Start/stop live session
│   │   │   │   └── settings.py      # Bot config
│   │   │   └── ws.py                # WebSocket realtime
│   │   │
│   │   ├── core/                    # Business logic (framework-agnostic)
│   │   │   ├── tiktok/
│   │   │   │   ├── listener.py      # Wrap TikTokLiveClient
│   │   │   │   └── replier.py       # send_room_chat + throttle
│   │   │   ├── rag/
│   │   │   │   ├── embedder.py      # Embedding abstraction
│   │   │   │   ├── retriever.py     # ChromaDB interface
│   │   │   │   └── pipeline.py      # Orchestrate full RAG flow
│   │   │   └── ai/
│   │   │       ├── base.py          # AIProvider Protocol
│   │   │       ├── claude.py        # Anthropic implementation
│   │   │       └── openai_llm.py    # OpenAI implementation
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM
│   │   │   ├── seller.py
│   │   │   ├── knowledge.py
│   │   │   ├── session.py
│   │   │   └── message.py
│   │   │
│   │   └── schemas/                 # Pydantic request/response
│   │       ├── knowledge.py
│   │       ├── session.py
│   │       └── settings.py
│   │
│   ├── tests/
│   ├── chroma_data/                 # gitignored
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── knowledge/page.tsx       # Quản lý knowledge base
│   │   ├── monitor/page.tsx         # Dashboard live realtime
│   │   └── settings/page.tsx        # Cài đặt bot
│   ├── components/
│   │   ├── ui/                      # shadcn/ui
│   │   ├── knowledge/
│   │   ├── monitor/
│   │   └── settings/
│   ├── lib/
│   │   ├── api.ts                   # REST client
│   │   └── ws.ts                    # WebSocket client
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
│
├── docker-compose.yml               # Production
├── docker-compose.dev.yml           # Dev overrides
├── .env.example                     # Root env template
├── Makefile
├── pyproject.toml                   # TikTokLive lib config (giữ nguyên)
└── README.md
```

---

## 4. Data Models

### Seller
```python
id: UUID (PK)
name: str
tiktok_unique_id: str
tiktok_session_id: str          # cookie để post comment
bot_settings: JSON              # tone, blacklist, delay config
created_at: datetime
```

### KnowledgeChunk
```python
id: UUID (PK)
seller_id: UUID (FK → Seller)   # multi-tenant key
content: str                    # text gốc
category: str                   # "product" | "policy" | "faq"
metadata: JSON                  # product_name, price, stock, ...
updated_at: datetime
```
> Vector embedding lưu trong ChromaDB, link bằng chunk id.

### LiveSession
```python
id: UUID (PK)
seller_id: UUID (FK → Seller)
tiktok_room_id: str
status: str                     # "active" | "ended" | "paused"
started_at: datetime
ended_at: datetime | None
```

### MessageLog
```python
id: UUID (PK)
session_id: UUID (FK → LiveSession)
user_unique_id: str             # TikTok username của người comment
comment: str
reply: str | None
intent: str                     # "product_inquiry" | "greeting" | "unknown"
chunks_used: JSON               # debug: chunk ids được retrieve
created_at: datetime
```

---

## 5. AI Provider Abstraction

```python
# backend/app/core/ai/base.py
from typing import Protocol

class AIProvider(Protocol):
    async def generate_reply(self, system: str, context: str, user_msg: str) -> str: ...

class EmbedProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...
```

- Reply mặc định: **Claude (claude-sonnet-4-6)**
- Embedding mặc định: **OpenAI text-embedding-3-small**
- Swap bằng env var `AI_REPLY_PROVIDER=claude|openai`

---

## 6. REST API Routes

```
# Knowledge Base
POST   /api/v1/knowledge/           → Thêm chunk
GET    /api/v1/knowledge/           → List chunks
PUT    /api/v1/knowledge/{id}       → Sửa chunk
DELETE /api/v1/knowledge/{id}       → Xóa chunk
POST   /api/v1/knowledge/upload     → Bulk import Excel/CSV

# Live Session
POST   /api/v1/sessions/start       → Kết nối TikTok Live
POST   /api/v1/sessions/stop        → Dừng bot
GET    /api/v1/sessions/status      → Trạng thái hiện tại
GET    /api/v1/sessions/history     → Lịch sử sessions

# Settings
GET    /api/v1/settings/
PUT    /api/v1/settings/
POST   /api/v1/settings/test-reply  → Test comment → preview reply

# Health
GET    /health                      → { status, chroma, ai_provider }
```

---

## 7. WebSocket Protocol

**Endpoint:** `WS /ws/monitor`

**Server → Client:**
```json
{ "type": "comment",  "user": "...", "content": "...", "timestamp": "..." }
{ "type": "reply",    "content": "...", "intent": "...", "chunks_used": [...] }
{ "type": "status",   "connected": true, "room_id": "..." }
{ "type": "error",    "message": "..." }
```

**Client → Server:**
```json
{ "type": "pause_bot" }
{ "type": "resume_bot" }
{ "type": "manual_reply", "content": "..." }
```

---

## 8. Environment Variables

```bash
# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
AI_REPLY_PROVIDER=claude          # claude | openai
AI_EMBED_PROVIDER=openai          # openai | local

# TikTok
TIKTOK_SESSION_ID=                # cookie sessionid
TIKTOK_SIGN_API_KEY=              # Euler Stream key (optional)

# App
DATABASE_URL=sqlite:///./app.db   # → postgresql:// khi scale
CHROMA_PATH=./chroma_data
REPLY_DELAY_MIN=5
REPLY_DELAY_MAX=15

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 9. Makefile Commands

```makefile
# Development
dev-backend   # uvicorn app.main:app --reload --port 8000
dev-frontend  # cd frontend && npm run dev
dev           # chạy cả 2 song song

# Setup
install       # pip install -e . && pip install -e backend/
install-fe    # cd frontend && npm install
setup         # install + install-fe + copy .env files

# Production
up            # docker compose up -d
down          # docker compose down
logs          # docker compose logs -f
build         # docker compose build

# Database
db-migrate    # alembic upgrade head
db-reset      # alembic downgrade base && alembic upgrade head

# Utils
test          # pytest backend/tests/
lint          # ruff check backend/
kb-import     # python backend/scripts/import_kb.py --file data.xlsx
```

---

## 10. Quyết định kỹ thuật quan trọng

| Vấn đề | Quyết định | Lý do |
|--------|-----------|-------|
| TikTokLive lib | Không sửa, import trực tiếp | Tránh merge conflict khi upstream update |
| Database | SQLite → Alembic → PostgreSQL | Đơn giản ban đầu, migrate dễ |
| Vector store | ChromaDB local | Không cần infra, đủ cho giai đoạn đầu |
| Multi-tenant | seller_id trong tất cả model | Thêm auth layer sau, không rewrite |
| Reply throttle | Random 5-15s delay | Giảm risk bị TikTok ban |
| AI abstraction | Protocol pattern | Swap provider = đổi 1 dòng config |
| Realtime | FastAPI native WebSocket | Không cần Redis/Kafka giai đoạn đầu |

---

## 11. Rủi ro & Mitigation

| Rủi ro | Khả năng | Mitigation |
|--------|---------|-----------|
| TikTok ban account khi reply | Cao | Throttle random, user-agent rotation |
| Sign API rate limit | Trung bình | Cache connection, retry logic |
| Embedding cost OpenAI | Thấp | Batch embed khi import, không embed realtime |
| ChromaDB không scale | Thấp (giai đoạn đầu) | Migrate sang Qdrant/Pinecone khi cần |

---

## 12. Timeline

| Tuần | Milestone |
|------|-----------|
| 1-2 | Backend core: listener + replier + FastAPI skeleton |
| 3-4 | RAG pipeline + ChromaDB + prompt engineering tiếng Việt |
| 5-6 | Frontend: Knowledge page + Monitor dashboard + Settings |
| 7   | Integration + E2E test với live thật |
| 8   | Tìm khách hàng đầu tiên, onboard thủ công |
