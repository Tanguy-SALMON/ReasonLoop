# ReasonLoop API Design Proposals

Three distinct API architectures for exposing ReasonLoop as a service.

---

## Option 1: Simple REST API (Synchronous)

**Best for**: Simple integrations, small workloads, MVP

### Design
```
POST /api/v1/campaigns/generate
GET  /api/v1/campaigns/{id}
GET  /api/v1/campaigns/{id}/files/{filename}
GET  /api/v1/templates
```

### Flow
```
Client                          Server
  |                               |
  |  POST /campaigns/generate     |
  |  {url, template, options}     |
  |------------------------------>|
  |                               | [Blocks for 2-3 min]
  |                               | - Crawl website
  |                               | - Generate emails
  |                               | - Save files
  |<------------------------------|
  |  200 OK                       |
  |  {id, files: [...], status}   |
```

### Endpoints

```python
# POST /api/v1/campaigns/generate
{
    "url": "https://th.cos.com",
    "template": "email_campaign_generator",
    "options": {
        "num_designs": 3,
        "max_pages": 5,
        "design_styles": ["minimalist", "bold", "elegant"]
    }
}

# Response 200 OK
{
    "id": "camp_abc123",
    "status": "completed",
    "duration_seconds": 156,
    "files": [
        {"name": "minimalist.html", "path": "/files/camp_abc123/minimalist.html"},
        {"name": "bold.html", "path": "/files/camp_abc123/bold.html"},
        {"name": "elegant.html", "path": "/files/camp_abc123/elegant.html"},
        {"name": "design_system.json", "path": "/files/camp_abc123/design_system.json"}
    ],
    "design_system": {
        "colors": {"primary": "#212121", "background": "#FFFFFF"},
        "fonts": {"primary": "SuisseIntl"}
    }
}
```

### Pros
- Simple to implement and consume
- Stateless (no job tracking needed)
- Easy debugging

### Cons
- Long HTTP timeout (3+ minutes)
- No progress visibility
- Connection may drop on slow networks
- Doesn't scale (thread per request)

### Implementation
```python
# api/routes/campaigns.py
from fastapi import APIRouter, HTTPException
from core.execution_loop import run_execution_loop

router = APIRouter()

@router.post("/campaigns/generate")
async def generate_campaign(request: CampaignRequest):
    update_setting("PROMPT_TEMPLATE", request.template)
    objective = f"Create {request.options.num_designs} email designs for {request.url}"
    
    result_file = run_execution_loop(objective)
    
    if not result_file:
        raise HTTPException(500, "Generation failed")
    
    return CampaignResponse(
        id=generate_id(),
        status="completed",
        files=list_generated_files(result_file)
    )
```

---

## Option 2: Async Job Queue API

**Best for**: Production systems, multiple concurrent users, reliability

### Design
```
POST   /api/v1/jobs                    # Submit job
GET    /api/v1/jobs/{id}               # Get job status
GET    /api/v1/jobs/{id}/result        # Get completed result
DELETE /api/v1/jobs/{id}               # Cancel job
GET    /api/v1/jobs                    # List user's jobs
WS     /api/v1/jobs/{id}/stream        # Real-time updates (optional)
```

### Flow
```
Client                          Server                      Worker
  |                               |                            |
  |  POST /jobs                   |                            |
  |  {url, template}              |                            |
  |------------------------------>|                            |
  |  202 Accepted                 |                            |
  |  {id, status: "queued"}       |                            |
  |<------------------------------|                            |
  |                               |  Push to Redis/RabbitMQ    |
  |                               |--------------------------->|
  |  GET /jobs/{id}               |                            |
  |------------------------------>|                            | [Processing]
  |  {status: "crawling", 30%}    |                            |
  |<------------------------------|                            |
  |                               |                            |
  |  GET /jobs/{id}               |                            |
  |------------------------------>|                            |
  |  {status: "generating", 70%}  |                            |
  |<------------------------------|                            |
  |                               |<---------------------------|
  |  GET /jobs/{id}               |  Job complete              |
  |------------------------------>|                            |
  |  {status: "completed",        |                            |
  |   result: {...}}              |                            |
  |<------------------------------|                            |
```

### Endpoints

```python
# POST /api/v1/jobs
{
    "type": "email_campaign",
    "url": "https://th.cos.com",
    "template": "email_campaign_generator",
    "webhook_url": "https://myapp.com/webhooks/reasonloop",  # Optional
    "options": {
        "num_designs": 3,
        "priority": "normal"  # normal, high
    }
}

# Response 202 Accepted
{
    "id": "job_xyz789",
    "status": "queued",
    "created_at": "2026-01-22T17:45:00Z",
    "estimated_duration_seconds": 120,
    "position_in_queue": 0
}

# GET /api/v1/jobs/{id}
{
    "id": "job_xyz789",
    "status": "processing",  # queued, processing, completed, failed, cancelled
    "progress": {
        "current_task": 2,
        "total_tasks": 6,
        "current_task_name": "Taking screenshots",
        "percent": 33
    },
    "created_at": "2026-01-22T17:45:00Z",
    "started_at": "2026-01-22T17:45:02Z",
    "updated_at": "2026-01-22T17:46:15Z"
}

# GET /api/v1/jobs/{id}/result (when completed)
{
    "id": "job_xyz789",
    "status": "completed",
    "result": {
        "campaign_id": "camp_abc123",
        "files": [...],
        "design_system": {...},
        "content": {...}
    },
    "duration_seconds": 142,
    "completed_at": "2026-01-22T17:47:22Z"
}
```

### Webhook Callback
```python
# POST to webhook_url when job completes
{
    "event": "job.completed",
    "job_id": "job_xyz789",
    "timestamp": "2026-01-22T17:47:22Z",
    "result": {
        "campaign_id": "camp_abc123",
        "files_url": "https://api.reasonloop.com/api/v1/jobs/job_xyz789/result"
    }
}
```

### Pros
- Non-blocking (immediate response)
- Real-time progress tracking
- Handles failures gracefully (retry logic)
- Scales horizontally (add workers)
- Webhook support for integrations

### Cons
- More complex infrastructure (Redis/RabbitMQ)
- Client needs polling or webhook handling
- State management overhead

### Implementation
```python
# api/routes/jobs.py
from fastapi import APIRouter, BackgroundTasks
from celery import Celery

router = APIRouter()
celery = Celery('reasonloop', broker='redis://localhost:6379')

@router.post("/jobs", status_code=202)
async def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    job_id = generate_job_id()
    
    # Store job in Redis
    await redis.hset(f"job:{job_id}", mapping={
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "request": request.json()
    })
    
    # Queue async task
    execute_campaign.delay(job_id, request.dict())
    
    return {"id": job_id, "status": "queued"}

@celery.task(bind=True)
def execute_campaign(self, job_id: str, request: dict):
    # Update progress during execution
    self.update_state(state='PROGRESS', meta={'task': 1, 'total': 6})
    # ... run pipeline
```

---

## Option 3: GraphQL API with Subscriptions

**Best for**: Complex queries, real-time UIs, mobile apps

### Design
```graphql
type Query {
    campaign(id: ID!): Campaign
    campaigns(filter: CampaignFilter): [Campaign!]!
    templates: [Template!]!
}

type Mutation {
    generateCampaign(input: GenerateCampaignInput!): CampaignJob!
    cancelJob(jobId: ID!): Boolean!
}

type Subscription {
    jobProgress(jobId: ID!): JobProgress!
}
```

### Schema

```graphql
# Input types
input GenerateCampaignInput {
    url: String!
    template: String! = "email_campaign_generator"
    options: CampaignOptionsInput
}

input CampaignOptionsInput {
    numDesigns: Int = 3
    maxPages: Int = 5
    designStyles: [DesignStyle!] = [MINIMALIST, BOLD, ELEGANT]
    includeScreenshots: Boolean = true
}

enum DesignStyle {
    MINIMALIST
    BOLD
    ELEGANT
    MODERN
    CLASSIC
}

# Output types
type CampaignJob {
    id: ID!
    status: JobStatus!
    progress: JobProgress
    campaign: Campaign
    createdAt: DateTime!
    completedAt: DateTime
}

enum JobStatus {
    QUEUED
    CRAWLING
    SCREENSHOTTING
    ANALYZING
    GENERATING
    COMPLETED
    FAILED
}

type JobProgress {
    status: JobStatus!
    currentTask: Int!
    totalTasks: Int!
    taskName: String!
    percent: Float!
    logs: [String!]
}

type Campaign {
    id: ID!
    url: String!
    createdAt: DateTime!
    
    # Nested design system
    designSystem: DesignSystem!
    
    # Email designs with content
    emails: [EmailDesign!]!
    
    # Screenshots taken
    screenshots: [Screenshot!]!
    
    # Raw files
    files: [File!]!
}

type DesignSystem {
    colors: ColorPalette!
    typography: Typography!
    buttons: ButtonStyle!
    spacing: Spacing!
}

type ColorPalette {
    primary: String!
    secondary: String
    accent: String
    background: String!
    text: String!
}

type EmailDesign {
    id: ID!
    style: DesignStyle!
    html: String!
    preview: String  # Base64 rendered preview
    content: EmailContent!
}

type EmailContent {
    subjectLine: String!
    previewText: String!
    headline: String!
    bodyCopy: String!
    ctaText: String!
    products: [ProductDescription!]
}
```

### Example Queries

```graphql
# Generate a campaign
mutation GenerateCampaign {
    generateCampaign(input: {
        url: "https://th.cos.com"
        options: {
            numDesigns: 3
            designStyles: [MINIMALIST, BOLD]
        }
    }) {
        id
        status
    }
}

# Subscribe to progress (WebSocket)
subscription WatchJob {
    jobProgress(jobId: "job_xyz789") {
        status
        percent
        taskName
        logs
    }
}

# Fetch completed campaign with specific fields
query GetCampaign {
    campaign(id: "camp_abc123") {
        designSystem {
            colors {
                primary
                background
            }
            typography {
                primaryFont
            }
        }
        emails {
            style
            content {
                subjectLine
                headline
            }
        }
    }
}

# List campaigns with filtering
query ListCampaigns {
    campaigns(filter: { 
        urlContains: "cos.com"
        createdAfter: "2026-01-01"
    }) {
        id
        url
        createdAt
        emails {
            style
        }
    }
}
```

### Pros
- Flexible queries (client chooses fields)
- Real-time subscriptions built-in
- Strong typing with schema
- Single endpoint, multiple operations
- Great for complex UIs

### Cons
- Steeper learning curve
- More complex server implementation
- Caching is harder than REST
- Overkill for simple integrations

### Implementation
```python
# api/graphql/schema.py
import strawberry
from strawberry.types import Info

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def generate_campaign(
        self, 
        input: GenerateCampaignInput,
        info: Info
    ) -> CampaignJob:
        job_id = await create_job(input)
        background_tasks = info.context["background_tasks"]
        background_tasks.add_task(execute_pipeline, job_id, input)
        return CampaignJob(id=job_id, status=JobStatus.QUEUED)

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def job_progress(self, job_id: str) -> AsyncGenerator[JobProgress, None]:
        async for progress in redis_pubsub.listen(f"job:{job_id}:progress"):
            yield JobProgress(**progress)
```

---

## Comparison Matrix

| Feature | REST Sync | REST Async (Jobs) | GraphQL |
|---------|-----------|-------------------|---------|
| **Complexity** | Low | Medium | High |
| **Real-time** | No | Polling/Webhook | Subscriptions |
| **Scalability** | Low | High | High |
| **Flexibility** | Fixed responses | Fixed responses | Client chooses |
| **Learning curve** | Easy | Easy | Moderate |
| **Mobile-friendly** | Yes | Yes | Yes (efficient) |
| **Caching** | Easy (HTTP) | Medium | Hard |
| **Best for** | MVP, scripts | Production | Complex UIs |

## Recommendation

**Start with Option 2 (Async Job Queue)** because:

1. **Non-blocking**: 2-3 minute operations shouldn't block HTTP connections
2. **Progress tracking**: Users can see what's happening
3. **Reliability**: Jobs can retry on failure
4. **Scalability**: Add workers as demand grows
5. **Webhook support**: Easy integration with other systems

Later, add GraphQL as a **layer on top** if you need:
- Complex client queries
- Real-time UI updates
- Mobile app optimization

---

## File Storage Structure

All outputs saved to `output/{domain}/`:

```
output/
└── th.cos.com/
    ├── campaigns/
    │   └── camp_abc123_20260122/
    │       ├── minimalist.html
    │       ├── bold.html
    │       ├── elegant.html
    │       ├── design_system.json
    │       └── report.md
    ├── screenshots/
    │   ├── home.png
    │   ├── product_1.png
    │   └── checkout.png
    └── cache/
        └── crawl_20260122.json
```
