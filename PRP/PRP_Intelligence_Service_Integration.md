# PRP: Intelligence Service Integration (be-campaign + ReasonLoop)

## 1. Context & Objective
**Objective:** Integrate the `ReasonLoop` application (acting as an AI Intelligence Microservice) with the `be-campaign` application (the Main Backend).
**Goal:** Enable `be-campaign` to request website analysis (tone, keywords, audience) from `ReasonLoop` via a secure internal API, using an asynchronous background pattern to avoid blocking the main thread.

## 2. Technical Constraints
*   **Architecture:** Sidecar Microservices.
    *   `be-campaign`: FastAPI (Port 8000).
    *   `ReasonLoop`: FastAPI (Port 8001).
*   **Communication:** HTTP/JSON via `httpx`.
*   **Security:** Internal Secret Key (`X-Internal-Secret`) required for all inter-service calls.
*   **Performance:**
    *   Scraping/Analysis is slow (10-60s).
    *   Must use `FastAPI BackgroundTasks` in the main app.
    *   Must implement timeouts (45s hard limit) in the agent.
*   **Error Handling:** Fail gracefully. If `ReasonLoop` is down or blocked, `be-campaign` must log the error and continue without crashing.

## 3. File Structure References
*   **Main App:** `be-campaign/`
*   **Agent App:** `ReasonLoop/`
*   **Shared Secret:** `INTERNAL_SERVICE_SECRET` (env var).

---

## 4. AI Execution Plan (Step-by-Step)

**Instruction to AI:** Execute the following steps sequentially. Do not proceed to the next step until the current step is verified.

### Phase 1: ReasonLoop (The Server) Setup

**Step 1.1: Create Dependency for Auth**
*   **File:** `ReasonLoop/api/dependencies.py`
*   **Action:** Create a dependency function `verify_internal_secret` that checks the `X-Internal-Secret` header against `os.getenv("INTERNAL_SERVICE_SECRET")`. Raise 403 if invalid.

**Step 1.2: Create the Intelligence Router**
*   **File:** `ReasonLoop/api/routes/intelligence_route.py`
*   **Action:**
    *   Define a Pydantic model `AnalysisRequest` (url: str, force_refresh: bool).
    *   Create a POST endpoint `/v1/analyze`.
    *   **Logic:**
        1.  Validate URL (reject localhost/private IPs).
        2.  Check if `force_refresh` is False. If so, return mock/cached data (for now).
        3.  If True, call `WebsiteIntelligence.analyze_url(url)` (from existing `intelligence.py`).
        4.  Wrap the call in `asyncio.wait_for` with a 45-second timeout.
        5.  Handle `asyncio.TimeoutError` by returning 408.
    *   **Security:** Apply `Depends(verify_internal_secret)`.

**Step 1.3: Register Router**
*   **File:** `ReasonLoop/api/main.py`
*   **Action:** Import and include `intelligence_route` with prefix `/api`. Ensure the app runs on Port 8001 by default or via env var.

### Phase 2: be-campaign (The Client) Setup

**Step 2.1: Create the Adapter**
*   **File:** `be-campaign/adapters/ai_agent_adapter.py`
*   **Action:**
    *   Create class `AIAgentAdapter`.
    *   Initialize with `base_url` (default `http://localhost:8001`) and `secret_key`.
    *   Method `get_website_intelligence(url: str) -> Optional[Dict]`.
    *   Use `httpx.AsyncClient` with a 60s timeout.
    *   Include `X-Internal-Secret` header.
    *   Catch `httpx.RequestError` and `httpx.HTTPStatusError`. Log errors, return `None` on failure.

**Step 2.2: Create the Service Logic**
*   **File:** `be-campaign/services/customer_ai_service.py` (or similar)
*   **Action:**
    *   Create an async function `enrich_customer_background(customer_id: str, website: str, db: Session)`.
    *   **Logic:**
        1.  Instantiate `AIAgentAdapter`.
        2.  Call `get_website_intelligence(website)`.
        3.  If data returns, update the `Customer` model (fields: `brand_tone`, `ai_keywords`).
        4.  Commit to DB.
        5.  Log success/failure.

**Step 2.3: Expose Trigger Endpoint**
*   **File:** `be-campaign/api/routers/customers.py`
*   **Action:**
    *   Add endpoint `POST /{id}/enrich`.
    *   Inject `BackgroundTasks`.
    *   Fetch customer URL from DB.
    *   Call `background_tasks.add_task(enrich_customer_background, ...)`
    *   Return immediate 202 Accepted response: `{"status": "queued"}`.

### Phase 3: Integration Testing

**Step 3.1: Create Integration Test Script**
*   **File:** `scripts/test_integration.py` (in root)
*   **Action:**
    *   Script that starts both servers (mocking the DB if needed).
    *   Sends a request to `be-campaign` port 8000.
    *   Asserts that `be-campaign` returns 202.
    *   Asserts that `ReasonLoop` received the request (via logs or mock).

---

## 5. Definition of Done
1.  ✅ `ReasonLoop` rejects requests without the correct header (403).
2.  ✅ `be-campaign` can trigger an analysis without freezing the API.
3.  ✅ If `ReasonLoop` is turned off, `be-campaign` logs an error but does not crash.
4.  ✅ The `run-rl.sh` and `run-be.sh` scripts successfully start both services on 8001 and 8000 respectively.

---

## 6. Implementation Summary (Completed 2026-01-24)

### Files Created

#### Phase 1: ReasonLoop (Server)
| File | Description |
|------|-------------|
| `api/dependencies.py` | Auth verification with `verify_internal_secret()` and SSRF protection |
| `api/routes/internal.py` | Internal API router with `/v1/analyze` endpoint, caching, 45s timeout |
| `api/core/config.py` | Updated to use port 8001 by default |
| `api/routes/__init__.py` | Registered internal router |
| `api/main.py` | Included internal router |

#### Phase 2: be-campaign (Client) - Reference Implementation
| File | Description |
|------|-------------|
| `integrations/be_campaign/adapters/ai_agent_adapter.py` | HTTP client with retry, timeout, error handling |
| `integrations/be_campaign/services/customer_ai_service.py` | Business logic for customer enrichment |
| `integrations/be_campaign/api/routers/customers.py` | FastAPI router with `/enrich` endpoint |
| `integrations/be_campaign/models/customer.py` | Customer model with AI fields |

#### Phase 3: Testing & Scripts
| File | Description |
|------|-------------|
| `scripts/test_integration.py` | Integration test suite (auth, SSRF, analysis) |
| `scripts/run-rl.sh` | Start ReasonLoop on port 8001 |
| `scripts/run-be.sh` | Start mock be-campaign on port 8000 |

### API Endpoints

#### ReasonLoop (Port 8001)
```
POST /api/v1/internal/v1/analyze   - Website analysis (requires X-Internal-Secret)
GET  /api/v1/internal/v1/health    - Internal health check (requires X-Internal-Secret)
GET  /api/v1/health                - Public health check
```

#### be-campaign (Port 8000)
```
GET  /api/v1/customers             - List customers
GET  /api/v1/customers/{id}        - Get customer
POST /api/v1/customers/{id}/enrich - Trigger AI enrichment (returns 202)
GET  /api/v1/customers/{id}/enrichment-status - Check enrichment status
```

### Quick Start

```bash
# Terminal 1: Start ReasonLoop
export INTERNAL_SERVICE_SECRET="my-secret-key"
./scripts/run-rl.sh

# Terminal 2: Start be-campaign mock
export INTERNAL_SERVICE_SECRET="my-secret-key"
./scripts/run-be.sh

# Terminal 3: Run tests
export INTERNAL_SERVICE_SECRET="my-secret-key"
python scripts/test_integration.py
```

### Security Features
- X-Internal-Secret header authentication
- SSRF protection (blocks localhost, private IPs, internal domains)
- 45-second timeout to prevent hanging
- Graceful error handling (never crashes caller)

### Caching
- In-memory cache with 1-hour TTL
- `force_refresh=true` bypasses cache
- Production: Replace with Redis
