# Cursor AI — Build Prompt
## WhatsApp Agent SaaS for Colombian SMEs

---

## ROLE & MISSION

You are a senior Python backend engineer building a production-ready, multi-tenant SaaS product from scratch. Your job is to implement **every file, every function, every test, and every configuration** described below. Do not skip anything. Do not use placeholders. Write real, working code.

When you finish each section, confirm what was built and what is still pending.

---

## WHAT WE ARE BUILDING

A **WhatsApp AI agent SaaS platform** that allows a single developer/operator to onboard multiple Colombian SMEs (restaurants, clinics, clothing stores) as tenants. Each tenant gets their own WhatsApp number with an AI agent that:

1. Receives customer messages via WhatsApp
2. Retrieves long-term memory about each customer (past orders, preferences, name)
3. Generates a contextual, helpful response in Colombian Spanish
4. Sends the response back via WhatsApp
5. Saves the new interaction to memory for future use

**The operator (you) manages multiple SME tenants from a single admin panel. Each SME pays a monthly subscription.**

---

## TECH STACK — NON-NEGOTIABLE

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Primary backend |
| Web framework | FastAPI | Async, fast, typed |
| AI agent runtime | Anthropic Claude Managed Agents API (`managed-agents-2026-04-01` beta) | Long-running sessions, persistent state |
| WhatsApp API | Kapso (`@kapso/whatsapp-cloud-api` + REST API) | Official Meta Cloud API wrapper, no ban risk |
| Long-term memory | Mem0 (`mem0ai` Python SDK) | Per-customer semantic memory across sessions |
| Database | Supabase (PostgreSQL via `supabase-py`) | Multi-tenant config, session cache, audit logs |
| Deployment | Railway (via `Procfile` + `railway.toml`) | Zero-cost start, auto-deploy from Git |
| Testing | pytest + pytest-asyncio + httpx | Full coverage |
| Config | python-dotenv + Pydantic Settings | Typed env vars |

**DO NOT substitute any of these. Do not use LangChain, OpenAI, or any other LLM library.**

---

## PROJECT STRUCTURE

Build exactly this structure:

```
whatsapp-agent-saas/
├── .env.example
├── .gitignore
├── Procfile
├── railway.toml
├── requirements.txt
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic Settings from env
│   ├── dependencies.py          # FastAPI dependency injection (DB, clients)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── webhook.py           # POST /webhook/whatsapp — main Kapso endpoint
│   │   └── admin.py             # Admin CRUD: businesses, sessions, memories
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py             # Claude Managed Agents: create, session mgmt
│   │   ├── memory.py            # Mem0 wrapper: add, search, delete
│   │   ├── whatsapp.py          # Kapso REST client: send message, verify sig
│   │   └── orchestrator.py     # Main brain: ties agent + memory + whatsapp
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── business.py          # Pydantic models for Business tenant
│   │   ├── message.py           # Kapso webhook payload models
│   │   └── session.py           # Agent session models
│   │
│   └── db/
│       ├── __init__.py
│       ├── client.py            # Supabase client singleton
│       └── queries.py           # All DB operations as typed functions
│
├── scripts/
│   ├── setup_kapso_webhook.py   # One-time: register webhook URL in Kapso
│   ├── create_business.py       # CLI: onboard a new SME tenant
│   └── seed_db.py               # Seed Supabase with demo data
│
├── sql/
│   └── schema.sql               # Complete Supabase schema
│
└── tests/
    ├── __init__.py
    ├── conftest.py              # Fixtures: mock clients, test DB
    ├── test_webhook.py          # Webhook signature, routing, background tasks
    ├── test_agent.py            # Agent creation, session reuse
    ├── test_memory.py           # Mem0 add/search/delete
    ├── test_orchestrator.py     # Full integration flow (mocked)
    └── test_admin.py            # Admin API CRUD
```

---

## DETAILED IMPLEMENTATION SPEC

### `app/config.py`

Use `pydantic_settings.BaseSettings`. Required fields:

```python
class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    
    # Kapso
    kapso_api_key: str
    kapso_webhook_secret: str
    
    # Mem0
    mem0_api_key: str
    
    # Supabase
    supabase_url: str
    supabase_key: str  # service role key
    
    # App
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    max_memory_results: int = 5
    agent_model: str = "claude-sonnet-4-6"
    
    model_config = SettingsConfig(env_file=".env", env_file_encoding="utf-8")
```

Expose a cached `get_settings()` function using `@lru_cache`.

---

### `sql/schema.sql`

Create these tables in Supabase:

```sql
-- Tenant businesses (your SME clients)
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,              -- e.g. "restaurante-cazuela"
    phone_number_id TEXT UNIQUE NOT NULL,   -- Kapso phone number ID
    business_context TEXT NOT NULL,         -- System prompt context for this business
    agent_id TEXT,                          -- Claude Managed Agent ID (created once)
    environment_id TEXT,                    -- Claude Environment ID (created once)
    webhook_registered BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    plan TEXT DEFAULT 'basico' CHECK (plan IN ('basico', 'estandar', 'pro')),
    monthly_message_limit INTEGER DEFAULT 500,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Per-customer agent sessions (one per customer phone per business)
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_phone TEXT NOT NULL,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,              -- Claude Managed Agent session ID
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_phone, business_id)
);

-- Message audit log (every inbound and outbound message)
CREATE TABLE message_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    client_phone TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT NOT NULL,
    whatsapp_message_id TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Monthly usage counters per business
CREATE TABLE usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    month_year TEXT NOT NULL,              -- e.g. "2026-04"
    message_count INTEGER DEFAULT 0,
    UNIQUE(business_id, month_year)
);

-- Indexes
CREATE INDEX idx_agent_sessions_lookup ON agent_sessions(client_phone, business_id);
CREATE INDEX idx_message_logs_business ON message_logs(business_id, processed_at DESC);
CREATE INDEX idx_usage_business_month ON usage_counters(business_id, month_year);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER businesses_updated_at
    BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

### `app/models/message.py`

Model the Kapso webhook payload precisely:

```python
from pydantic import BaseModel
from typing import Literal, Optional

class KapsoTextContent(BaseModel):
    body: str

class KapsoMessage(BaseModel):
    id: str
    from_: str  # alias "from"
    type: Literal["text", "audio", "image", "document", "interactive"]
    text: Optional[KapsoTextContent] = None
    timestamp: str

    model_config = ConfigDict(populate_by_name=True)

class KapsoWebhookPayload(BaseModel):
    event: str                          # "whatsapp.message.received"
    phone_number_id: str
    message: Optional[KapsoMessage] = None
```

---

### `app/core/whatsapp.py`

Implement a `KapsoClient` class with:

- `__init__(self, api_key: str, phone_number_id: str, webhook_secret: str)`
- `verify_signature(self, payload_bytes: bytes, signature: str) -> bool` — HMAC-SHA256
- `async send_text(self, to: str, text: str) -> dict` — POST to Kapso REST API
- `async send_typing_indicator(self, to: str)` — marks message as read
- Handle HTTP errors with retries (3 attempts, exponential backoff using `tenacity`)
- Use `httpx.AsyncClient` with a shared client (not creating a new one per request)

Kapso endpoint: `POST https://api.kapso.ai/meta/whatsapp/v24.0/{phone_number_id}/messages`
Auth header: `X-API-Key: {kapso_api_key}`

---

### `app/core/memory.py`

Implement a `MemoryService` class:

```python
class MemoryService:
    def __init__(self, api_key: str, max_results: int = 5):
        self.client = MemoryClient(api_key=api_key)
        self.max_results = max_results
    
    def search(self, query: str, user_id: str) -> list[str]:
        """Returns list of memory strings relevant to the query."""
        ...
    
    def add(self, user_message: str, assistant_message: str, user_id: str) -> None:
        """Adds a conversation turn to memory."""
        ...
    
    def get_all(self, user_id: str) -> list[dict]:
        """Returns all memories for a user (for admin panel)."""
        ...
    
    def delete_all(self, user_id: str) -> None:
        """Deletes all memories for a user."""
        ...
    
    def format_for_prompt(self, memories: list[str]) -> str:
        """Formats memories as a bullet-point string for the system prompt."""
        if not memories:
            return ""
        lines = "\n".join(f"- {m}" for m in memories)
        return f"Lo que sé de este cliente:\n{lines}\n"
```

All Mem0 calls must be wrapped in try/except. If Mem0 is unavailable, log the error and continue (memory is a nice-to-have, not blocking).

---

### `app/core/agent.py`

Implement `AgentService` class:

```python
class AgentService:
    def __init__(self, anthropic_client: Anthropic, settings: Settings):
        ...
    
    def create_agent_and_environment(self, business_name: str, business_context: str) -> tuple[str, str]:
        """
        Creates a Claude Managed Agent + Environment for a business.
        Returns (agent_id, environment_id).
        Called ONCE per business onboarding, IDs stored in Supabase.
        
        System prompt structure:
        - Role: customer service for {business_name}
        - Language: Colombian Spanish, warm, concise (max 3-4 sentences)
        - Rules: no invented info, escalate to human when asked
        - Context: {business_context} injected here
        - Tools: agent_toolset_20260401
        """
        ...
    
    def get_or_create_session(
        self, 
        client_phone: str, 
        agent_id: str, 
        environment_id: str,
        db_session_id: Optional[str]
    ) -> str:
        """
        Returns an existing session_id or creates a new Claude session.
        session_id is persisted in Supabase agent_sessions table.
        """
        ...
    
    def send_message(self, session_id: str, prompt: str) -> str:
        """
        Sends a message to an existing session and collects the full response.
        Uses beta header: managed-agents-2026-04-01
        Collects all text content blocks from the response stream.
        Returns the concatenated text response.
        """
        ...
```

The system prompt template (stored as a constant `SYSTEM_PROMPT_TEMPLATE`):

```
Eres el asistente virtual de {business_name}, un negocio colombiano.

REGLAS DE COMPORTAMIENTO:
1. Responde SIEMPRE en español colombiano natural y cálido
2. Sé conciso: máximo 3-4 oraciones por mensaje (esto es WhatsApp)
3. Usa el nombre del cliente si lo conoces de las memorias
4. Si el cliente pide hablar con un humano, responde exactamente: "Entendido, te conecto con un asesor en breve 🤝 [ESCALATE]"
5. NUNCA inventes precios, horarios o disponibilidad
6. Si no sabes algo, di honestamente que lo verificarás

INFORMACIÓN DEL NEGOCIO:
{business_context}

MEMORIA DEL CLIENTE:
{memory_context}
```

Note: `memory_context` is injected per-message at runtime, not stored in the agent definition.

---

### `app/core/orchestrator.py`

This is the **central brain**. Implement `MessageOrchestrator`:

```python
class MessageOrchestrator:
    def __init__(
        self,
        whatsapp: KapsoClient,
        memory: MemoryService,
        agent: AgentService,
        db: DatabaseService
    ):
        ...
    
    async def handle_incoming_message(
        self,
        business_id: str,
        client_phone: str,
        message_text: str,
        whatsapp_message_id: str
    ) -> None:
        """
        Full pipeline:
        1. Load business config from DB (or cache)
        2. Check monthly usage limit — if exceeded, send "plan limit" message and return
        3. Search Mem0 for relevant memories about this client
        4. Build prompt: memory_context + message_text
        5. Get or create Claude session for this client+business pair
        6. Send to Claude Managed Agents, get response
        7. Send response back via Kapso WhatsApp
        8. Save conversation to Mem0
        9. Log message to audit table
        10. Increment usage counter
        """
        ...
    
    async def _get_business_config(self, business_id: str) -> Business:
        """Load from DB with simple in-memory TTL cache (60s)."""
        ...
    
    def _build_prompt(self, memory_context: str, user_message: str) -> str:
        """Combines memory and user message into the final prompt for the agent."""
        ...
```

**Important:** `handle_incoming_message` must NEVER raise an exception to the caller. All errors must be caught, logged, and if possible a fallback message sent to the client.

---

### `app/api/webhook.py`

```python
@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    orchestrator: MessageOrchestrator = Depends(get_orchestrator)
) -> JSONResponse:
    """
    1. Read raw body bytes (needed for HMAC verification)
    2. Verify Kapso HMAC-SHA256 signature
       - Header: x-webhook-signature
       - Return 401 if invalid
    3. Parse body as KapsoWebhookPayload
    4. Filter: only process event == "whatsapp.message.received"
    5. Filter: only process message.type == "text"
    6. Extract: phone_number_id → look up business_id in DB
    7. Add to background_tasks: orchestrator.handle_incoming_message(...)
    8. Return 200 immediately (Kapso requires fast ACK)
    """
```

Also implement `GET /webhook/whatsapp` for Kapso webhook verification challenge (returns the `hub.challenge` query param).

---

### `app/api/admin.py`

Implement these endpoints (no auth for MVP, add API key header check):

```
POST   /admin/businesses              Create new business tenant
GET    /admin/businesses              List all businesses
GET    /admin/businesses/{id}         Get business details
PATCH  /admin/businesses/{id}         Update business context/plan
DELETE /admin/businesses/{id}         Deactivate business

GET    /admin/businesses/{id}/sessions     List all client sessions
DELETE /admin/businesses/{id}/sessions/{phone}  Delete session (force new)

GET    /admin/businesses/{id}/logs         Last 100 message logs
GET    /admin/businesses/{id}/usage        Current month usage stats

GET    /admin/businesses/{id}/memories/{phone}   List memories for a client
DELETE /admin/businesses/{id}/memories/{phone}   Delete all memories for a client
```

---

### `app/db/queries.py`

Implement these typed functions using `supabase-py`:

```python
async def get_business_by_phone_number_id(phone_number_id: str) -> Optional[Business]
async def get_business_by_id(business_id: str) -> Optional[Business]
async def update_business_agent_ids(business_id: str, agent_id: str, environment_id: str) -> None
async def list_businesses() -> list[Business]
async def create_business(data: BusinessCreate) -> Business
async def update_business(business_id: str, data: BusinessUpdate) -> Business

async def get_session(client_phone: str, business_id: str) -> Optional[AgentSession]
async def upsert_session(client_phone: str, business_id: str, session_id: str) -> None
async def increment_session_message_count(client_phone: str, business_id: str) -> None

async def log_message(business_id: str, client_phone: str, direction: str, content: str, wa_message_id: str) -> None
async def get_message_logs(business_id: str, limit: int = 100) -> list[MessageLog]

async def get_or_create_usage_counter(business_id: str, month_year: str) -> UsageCounter
async def increment_usage_counter(business_id: str, month_year: str) -> int  # returns new count
```

---

### `scripts/create_business.py`

CLI script to onboard a new SME tenant:

```
Usage: python scripts/create_business.py \
  --name "Restaurante La Cazuela" \
  --slug "restaurante-cazuela" \
  --phone-number-id "647015955153740" \
  --context "Restaurante en Medellín. Menú del día: bandeja paisa $18.000..."
  
This script:
1. Inserts the business in Supabase
2. Calls AgentService.create_agent_and_environment()
3. Updates the DB with agent_id and environment_id
4. Registers the webhook in Kapso (calls setup_kapso_webhook logic)
5. Prints a summary with all IDs
```

---

### `scripts/setup_kapso_webhook.py`

Standalone script to register/update the webhook URL for a given `phone_number_id`:

```python
# Usage: python scripts/setup_kapso_webhook.py --phone-number-id XXX --webhook-url https://your-app.railway.app
```

---

## SYSTEM PROMPT DESIGN — DETAILED

The system prompt must be constructed as follows (store as `SYSTEM_PROMPT_TEMPLATE` in `app/core/agent.py`):

```
Eres el asistente virtual de WhatsApp de {business_name}.

ROL: Atender clientes colombianos de manera cálida, útil y eficiente.

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en español colombiano natural (usa "usted" si el cliente lo usa, "tú" si el cliente lo usa)
2. Sé CONCISO: máximo 3-4 oraciones. Esto es WhatsApp, no un correo.
3. Usa el nombre del cliente si lo conoces.
4. Si el cliente dice "quiero hablar con una persona", "necesito un asesor" o similar, responde EXACTAMENTE: "Entendido [nombre si lo tienes], te conecto con un asesor de inmediato 🤝 [ESCALATE]" — no agregues nada más.
5. NUNCA inventes precios, productos, horarios o disponibilidad. Si no tienes la info, di: "Esa información la verifica un asesor en breve."
6. Para saludos iniciales, preséntate: "¡Hola! Soy el asistente virtual de {business_name}. ¿En qué te puedo ayudar?"
7. Termina los mensajes con una pregunta cuando sea apropiado, para mantener la conversación.

INFORMACIÓN DEL NEGOCIO:
{business_context}
```

The `memory_context` is NOT part of the stored system prompt. It is injected at runtime into each user message prompt as a prefix.

---

## ERROR HANDLING STRATEGY

| Scenario | Behavior |
|---|---|
| Invalid webhook signature | Return HTTP 401, log warning |
| Business not found for phone_number_id | Return HTTP 200 (ACK), log error, no message sent |
| Mem0 unavailable | Log error, continue without memory context |
| Claude API error | Send fallback: "Disculpa, tuve un inconveniente técnico. Por favor escribe de nuevo en un momento." |
| Claude session expired/invalid | Create new session, retry once |
| Usage limit reached | Send: "Por el momento hemos alcanzado el límite de mensajes del plan. Un asesor te contactará pronto." |
| Supabase unavailable | Log critical error, send fallback message, do not crash |

All errors must be logged with `structlog` in JSON format including: `business_id`, `client_phone` (last 4 digits only for privacy), `error_type`, `timestamp`.

---

## CONFIGURATION FILES

### `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
anthropic==0.49.0
mem0ai==1.0.11
supabase==2.10.0
httpx==0.27.0
tenacity==8.3.0
pydantic-settings==2.3.0
python-dotenv==1.0.1
structlog==24.4.0
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-httpx==0.30.0
```

### `Procfile`

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

### `railway.toml`

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### `.env.example`

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Kapso
KAPSO_API_KEY=kap_live_...
KAPSO_WEBHOOK_SECRET=your_32_char_secret_here

# Mem0
MEM0_API_KEY=m0-...

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# App
APP_ENV=development
LOG_LEVEL=INFO
MAX_MEMORY_RESULTS=5
AGENT_MODEL=claude-sonnet-4-6
```

---

## TESTING REQUIREMENTS

### `tests/conftest.py`

Provide fixtures for:
- `mock_anthropic_client` — mocks `client.beta.agents.create`, `client.beta.environments.create`, `client.beta.sessions.create`, `client.beta.sessions.send_message_and_wait`
- `mock_mem0_client` — mocks `MemoryClient.search`, `MemoryClient.add`
- `mock_supabase_client` — mocks all DB queries
- `mock_kapso_client` — mocks `send_text`, `verify_signature`
- `test_business` — a `Business` fixture with all fields populated
- `test_client` — `AsyncClient` pointed at the FastAPI app

### Test coverage targets:
- `test_webhook.py`: valid message flow, invalid signature, non-text message, unknown phone_number_id
- `test_orchestrator.py`: full happy path, Mem0 failure (graceful), Claude failure (fallback), usage limit exceeded
- `test_agent.py`: session reuse vs new session, response text extraction
- `test_memory.py`: search formats correctly, add handles errors, empty memory returns empty string
- `test_admin.py`: CRUD for businesses, logs endpoint, usage endpoint

---

## LOGGING

Use `structlog` configured for JSON output in production, pretty-print in development.

Every request must log:
```json
{
  "event": "message_processed",
  "business_id": "uuid",
  "client_phone_suffix": "1234",
  "message_length": 42,
  "memory_results": 3,
  "response_length": 87,
  "duration_ms": 1240,
  "timestamp": "2026-04-11T10:30:00Z"
}
```

---

## WHAT TO BUILD FIRST (ORDER OF OPERATIONS)

1. `sql/schema.sql` → run it in Supabase first
2. `app/config.py` → settings foundation
3. `app/db/` → database layer (all queries)
4. `app/models/` → all Pydantic models
5. `app/core/whatsapp.py` → Kapso client
6. `app/core/memory.py` → Mem0 wrapper
7. `app/core/agent.py` → Claude Managed Agents service
8. `app/core/orchestrator.py` → main pipeline
9. `app/api/webhook.py` → webhook endpoint
10. `app/api/admin.py` → admin endpoints
11. `app/main.py` → wire everything together
12. `scripts/` → setup scripts
13. `tests/` → full test suite
14. `README.md` → deployment guide

---

## DEFINITION OF DONE

The implementation is complete when:
- [ ] All files listed in the project structure exist with real code (no TODOs, no placeholders)
- [ ] `uvicorn app.main:app` starts without errors
- [ ] `pytest tests/ -v` passes with >80% coverage
- [ ] `python scripts/create_business.py --help` works
- [ ] A real WhatsApp message sent to the Kapso number gets a real Claude response
- [ ] The admin API returns correct data for all endpoints
- [ ] The README has accurate setup and deployment instructions
