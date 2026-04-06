# TikTok Live AI Bot — Design Spec

**Date:** 2026-04-06
**Status:** Approved (v2 — post spec review)
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
       │ CommentEvent / LiveEndEvent / DisconnectEvent
       ▼
[backend/core/tiktok/listener.py]
       │
       ├── LiveEndEvent / DisconnectEvent
       │       └── cập nhật LiveSession.status = "ended"
       │           broadcast WS { type: "status", connected: false }
       │
       ▼
[Filter Layer]
  ├── Blacklist keywords
  ├── Intent detection
  └── Cooldown per user (user_cooldown_seconds từ bot_settings)
       │ pass
       ▼
[RAG Pipeline]
  1. Embed comment (OpenAI text-embedding-3-small)
  2. ChromaDB search (collection: seller_{seller_id}) → top-3 chunks
  3. Build prompt (System + Context + Comment)
  4. AI Provider → reply text
       │
       ▼
[Throttle: random REPLY_DELAY_MIN–REPLY_DELAY_MAX giây]
       │
       ▼
[replier.py → send_room_chat(session_id, tt_target_idc)]
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
│   │   │       ├── base.py          # AIProvider + EmbedProvider Protocol
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
│   │       ├── settings.py
│   │       └── message.py           # MessageLogSchema cho dashboard
│   │
│   ├── alembic/                     # DB migrations
│   │   └── versions/
│   ├── alembic.ini
│   ├── scripts/
│   │   └── import_kb.py             # Bulk import Excel/CSV
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
├── docker-compose.dev.yml           # Dev: volume mounts hot-reload, no restart policy, debug ports exposed
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
tiktok_session_id: str          # [ENCRYPTED at rest — Fernet key từ SECRET_KEY env]
tiktok_target_idc: str          # cookie tt-target-idc (e.g. "useast1a") — bắt buộc để post chat
bot_settings: JSON              # xem schema bên dưới
created_at: datetime
```

**bot_settings JSON schema:**
```json
{
  "tone": "friendly",
  "blacklist_keywords": ["từ cấm 1", "từ cấm 2"],
  "reply_delay_min": 5,
  "reply_delay_max": 15,
  "user_cooldown_seconds": 60,
  "max_replies_per_session": 500,
  "auto_reply_enabled": true
}
```

> **Bảo mật:** `tiktok_session_id` và `tiktok_target_idc` được mã hóa bằng `cryptography.fernet`
> trước khi lưu DB. Key mã hóa lấy từ env var `SECRET_KEY`. Không bao giờ log hoặc trả về plaintext qua API.

### KnowledgeChunk
```python
id: UUID (PK)
seller_id: UUID (FK → Seller)   # multi-tenant key
content: str                    # text gốc
category: Enum                  # PRODUCT | POLICY | FAQ  (DB check constraint)
metadata: JSON                  # product_name, price, stock, color, size, ...
updated_at: datetime
needs_reembed: bool             # True khi content thay đổi, background task sẽ re-embed
```
> Vector embedding lưu trong ChromaDB collection `seller_{seller_id}`, link bằng chunk id.
> Khi `PUT /knowledge/{id}` được gọi: set `needs_reembed = True` → background task embed lại.

### LiveSession
```python
id: UUID (PK)
seller_id: UUID (FK → Seller)
tiktok_room_id: int             # BigInteger — khớp với kiểu int của TikTokLive lib
status: Enum                    # ACTIVE | ENDED | PAUSED
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
intent: str                     # "product_inquiry" | "greeting" | "unknown" | "skipped"
chunks_used: JSON               # debug: list chunk ids được retrieve
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
- `AI_EMBED_PROVIDER=local` không được hỗ trợ trong v1 — chỉ dùng `openai`

---

## 6. REST API Routes

```
# Knowledge Base
POST   /api/v1/knowledge/                    → Thêm chunk (embed ngay)
GET    /api/v1/knowledge/?page=1&limit=20    → List chunks có phân trang
PUT    /api/v1/knowledge/{id}                → Sửa chunk (set needs_reembed=True)
DELETE /api/v1/knowledge/{id}                → Xóa chunk + xóa khỏi ChromaDB
POST   /api/v1/knowledge/upload              → Bulk import Excel/CSV (max 500 rows, async job)

# Live Session
POST   /api/v1/sessions/start                → Kết nối TikTok Live
POST   /api/v1/sessions/stop                 → Dừng bot
GET    /api/v1/sessions/status               → Trạng thái hiện tại (scoped by seller_id)
GET    /api/v1/sessions/history?page=1&limit=20 → Lịch sử sessions có phân trang

# Settings
GET    /api/v1/settings/
PUT    /api/v1/settings/
POST   /api/v1/settings/test-reply           → Test comment → preview reply (không gửi TikTok)

# Health
GET    /health                               → { status, chroma, ai_provider, db }
```

---

## 7. WebSocket Protocol

**Endpoint:** `WS /ws/monitor`

**Server → Client:**
```json
{ "type": "comment",  "message_id": "uuid", "user": "...", "content": "...", "timestamp": "..." }
{ "type": "reply",    "message_id": "uuid", "content": "...", "intent": "...", "chunks_used": [...] }
{ "type": "status",   "connected": true, "room_id": 12345678 }
{ "type": "error",    "message": "..." }
```

**Client → Server:**
```json
{ "type": "pause_bot" }
{ "type": "resume_bot" }
{ "type": "manual_reply", "message_id": "uuid", "content": "..." }
```
> `message_id` trong `manual_reply` map về `MessageLog.id` để biết reply cho comment nào.

---

## 8. Environment Variables

```bash
# Security
SECRET_KEY=                       # Fernet key để encrypt session_id — BẮT BUỘC

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
AI_REPLY_PROVIDER=claude          # claude | openai
AI_EMBED_PROVIDER=openai          # chỉ hỗ trợ openai trong v1

# TikTok (stored encrypted in DB, env chỉ dùng để bootstrap seller đầu tiên)
TIKTOK_SESSION_ID=                # cookie sessionid
TIKTOK_TARGET_IDC=useast1a        # cookie tt-target-idc — BẮT BUỘC để post chat
TIKTOK_SIGN_API_KEY=              # Euler Stream key (free tier có rate limit cho chat route)
WHITELIST_AUTHENTICATED_SESSION_ID_HOST=tiktok.eulerstream.com  # BẮT BUỘC cho send_room_chat

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

# Production (Docker)
up            # docker compose up -d
down          # docker compose down
logs          # docker compose logs -f
build         # docker compose build

# docker-compose.dev.yml overrides production:
#   - volume mounts cho hot reload (./backend:/app, ./frontend:/app)
#   - không có restart: always
#   - expose port 5678 (debugpy)
#   - NODE_ENV=development

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
| Vector store | ChromaDB, 1 collection/seller | Namespace sạch cho multi-tenant |
| Multi-tenant | seller_id trong tất cả model | Thêm auth layer sau, không rewrite |
| Reply throttle | Random 5-15s delay | Giảm risk bị TikTok ban |
| AI abstraction | Protocol pattern | Swap provider = đổi 1 dòng config |
| Realtime | FastAPI native WebSocket | Không cần Redis/Kafka giai đoạn đầu |
| Session credential | Fernet encrypt at rest | session_id = full TikTok account access |
| Re-embed | needs_reembed flag + background task | Không block API response khi update chunk |

---

## 11. Rủi ro & Mitigation

| Rủi ro | Khả năng | Mitigation |
|--------|---------|-----------|
| TikTok ban account khi reply | Cao | Throttle random 5-15s, max_replies_per_session |
| Sign API rate limit (Euler Stream chat route) | Trung bình | Euler Stream free tier có giới hạn riêng cho chat; cần API key trả phí khi dùng thật |
| `WHITELIST_AUTHENTICATED_SESSION_ID_HOST` sai → chat không gửi được | Cao | Set đúng hostname trong .env, validate khi startup |
| Embedding cost OpenAI | Thấp | Batch embed khi import, re-embed chỉ khi cần |
| ChromaDB không scale | Thấp (giai đoạn đầu) | Migrate sang Qdrant/Pinecone khi cần |
| Test với live thật phụ thuộc stream đang chạy | Trung bình | Dùng public stream (e.g. @tv_asahi_news) để integration test, mock TikTokLiveClient cho unit test |

---

## 12. Timeline

| Tuần | Milestone |
|------|-----------|
| 1-2 | Backend core: listener + replier (validate send_room_chat end-to-end trước) + FastAPI skeleton |
| 3-4 | RAG pipeline + ChromaDB + prompt engineering tiếng Việt + test accuracy |
| 5-6 | Frontend: Knowledge page + Monitor dashboard + Settings |
| 7   | Integration + test với live thật (dùng public stream để không phụ thuộc seller) |
| 8   | Tìm 3-5 seller đầu tiên, onboard thủ công, thu feedback |
