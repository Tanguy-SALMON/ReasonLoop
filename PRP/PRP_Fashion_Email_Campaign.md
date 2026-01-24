# Fashion Email Campaign Generator - Product Requirements Document (PRD)

**Version**: 1.0  
**Date**: 2026-01-16  
**Author**: ReasonLoop Product Team  
**Status**: Ready for Implementation  

---

## 📋 Executive Summary

### Product Overview
The Fashion Email Campaign Generator is an AI-orchestrated system that transforms raw recommendation engine outputs into personalized, segment-targeted email campaigns. The system leverages ReasonLoop's multi-agent architecture to automatically segment users, refine recommendations through LLM-as-a-Judge validation, and generate brand-aware email copy.

### Business Value
- **Automated Personalization**: Transform anonymous recommendations into targeted campaigns
- **Quality Assurance**: LLM-based recommendation validation ensures relevant product suggestions
- **Brand Consistency**: Automated copywriting maintains brand voice across all communications
- **Scalability**: Handle millions of users with minimal manual intervention
- **Cost Efficiency**: Reduce campaign creation time from days to minutes

---

## 🎯 Objectives & Goals

### Primary Objectives
1. **Automated Segmentation**: Cluster users by recommendation similarity using Jaccard similarity
2. **Quality Filtering**: Implement LLM-as-a-Judge for recommendation validation
3. **Brand-Aware Copywriting**: Generate email content that matches brand voice and tone
4. **Campaign Orchestration**: Coordinate multi-step pipeline from data to deployment-ready campaigns

### Success Metrics
- **Segmentation Quality**: Segments contain ≥85% user engagement correlation
- **Recommendation Accuracy**: LLM-judged recommendations achieve ≥90% relevance score
- **Brand Voice Consistency**: Generated copy matches brand guidelines ≥95%
- **Campaign Performance**: 15-25% improvement in email engagement vs. manual campaigns
- **Operational Efficiency**: Reduce campaign creation time by 80%

---

## 🏗️ Technical Architecture

### System Components

#### 1. SegmentationAgent
```python
class SegmentationAgent:
    def process_recommendations(self, recommendations: List[Tuple[str, List[str]]]) -> List[Segment]:
        """
        Input: [(user_id, [item_ids]), ...]
        Output: [Segment(segment_id, user_ids, top_items, size, label), ...]
        """
```

**Responsibilities**:
- Calculate Jaccard similarity between user recommendation vectors
- Cluster users using hierarchical clustering or DBSCAN
- Generate semantic segment labels using LLM
- Apply minimum segment size filtering

**Configuration**:
```python
SEGMENTATION_CONFIG = {
    "min_segment_size": 50,
    "similarity_threshold": 0.3,
    "clustering_method": "hierarchical",
    "max_segments": 10
}
```

#### 2. JudgmentAgent (LLM-as-a-Judge)
```python
class JudgmentAgent:
    def evaluate_recommendations(self, user_profile: dict, items: List[dict]) -> List[dict]:
        """
        Filter recommendations using LLM-based quality scoring
        """
```

**Evaluation Criteria**:
- Style compatibility (1-5 scale)
- Price appropriateness for user segment
- Brand alignment
- Seasonal relevance
- Availability status

**Model Configuration**:
```python
JUDGMENT_CONFIG = {
    "model_role": "reasoning_critic",
    "min_rating": 3.0,
    "include_reasoning": True,
    "suggest_alternatives": True
}
```

#### 3. CampaignWriter
```python
class CampaignWriter:
    def generate_email_copy(self, segment: Segment, refined_items: List[dict]) -> dict:
        """
        Generate complete email campaign for a segment
        """
```

**Output Structure**:
```python
{
    "subject_line": "Summer Style Alert: Your Personalized Picks Are Here!",
    "preview_text": "Handpicked styles just for you...",
    "body_html": "<html>...</html>",
    "cta_text": "Shop Your Looks",
    "utm_parameters": {...}
}
```

---

## 📊 Data Models

### Core Entities

#### Segment
```python
@dataclass
class Segment:
    segment_id: str
    user_ids: List[str]
    top_items: List[str]
    size: int
    label: str  # "Contemporary Minimalists", "Bohemian Dreamers"
    description: str
    avg_order_value: float
    style_tags: List[str]
    created_at: datetime
```

#### Campaign
```python
@dataclass
class Campaign:
    campaign_id: str
    tenant_id: str
    segments: List[SegmentCampaign]
    total_recipients: int
    brand_voice: BrandVoice
    template_id: str
    scheduled_send: datetime
    status: CampaignStatus
    performance_metrics: dict
```

#### SegmentCampaign
```python
@dataclass
class SegmentCampaign:
    segment: Segment
    refined_items: List[dict]
    email_copy: EmailCopy
    recipient_count: int
    performance_predictions: dict
```

### Database Schema

```sql
-- Segments table
CREATE TABLE segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    label VARCHAR(128) NOT NULL,
    description TEXT,
    size INTEGER NOT NULL,
    style_tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_segment (tenant_id, segment_id)
);

-- Segment members
CREATE TABLE segment_members (
    segment_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    similarity_score DECIMAL(5,4),
    PRIMARY KEY (segment_id, user_id),
    FOREIGN KEY (segment_id) REFERENCES segments(segment_id)
);

-- Campaigns
CREATE TABLE campaigns (
    campaign_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    status ENUM('draft', 'scheduled', 'sending', 'sent', 'failed'),
    total_recipients INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_status (tenant_id, status)
);

-- Campaign performance
CREATE TABLE campaign_performance (
    campaign_id VARCHAR(64) PRIMARY KEY,
    open_rate DECIMAL(5,4),
    click_rate DECIMAL(5,4),
    conversion_rate DECIMAL(5,4),
    revenue_generated DECIMAL(10,2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 🔧 Implementation Plan

### Phase 1: Core Pipeline (Weeks 1-2)
1. **SegmentationAgent Implementation**
   - Jaccard similarity calculation
   - Clustering algorithm implementation
   - Basic segment labeling

2. **JudgmentAgent Integration**
   - LLM-as-a-Judge prompt engineering
   - Recommendation filtering logic
   - Quality scoring system

### Phase 2: Campaign Generation (Weeks 3-4)
1. **CampaignWriter Development**
   - Email template system
   - Brand voice integration
   - Personalization engine

2. **Content Validation**
   - HTML generation
   - Brand compliance checking
   - A/B testing framework

### Phase 3: Integration & Deployment (Weeks 5-6)
1. **API Development**
   - FastAPI endpoint creation
   - Authentication system
   - Async task processing

2. **Monitoring & Analytics**
   - Performance tracking
   - Error handling
   - Cost monitoring

### Phase 4: Optimization (Weeks 7-8)
1. **Performance Tuning**
   - Batch processing optimization
   - Caching implementation
   - Resource scaling

2. **Advanced Features**
   - Real-time segmentation
   - Dynamic segment evolution
   - Multi-channel campaigns

---

## 🔌 Integration Points

### External Systems

#### Recommendation Engine
```python
# Expected input format
recommendations = [
    {
        "user_id": "user_123",
        "items": ["item_456", "item_789", "item_012"],
        "scores": [0.95, 0.87, 0.76],
        "context": {"season": "summer", "category": "dresses"}
    }
]
```

#### Email Service Provider (ESP)
```python
# Campaign payload format
campaign_payload = {
    "campaign_name": "Summer Style Segments",
    "segments": [
        {
            "segment_id": "seg_001",
            "recipients": ["user_123", "user_456"],
            "email_content": {...},
            "send_time": "2026-01-20T10:00:00Z"
        }
    ]
}
```

#### Product Catalog API
```python
# Item enrichment
item_details = {
    "item_id": "item_456",
    "name": "Floral Midi Dress",
    "category": "dresses",
    "price": 89.99,
    "brand": "ChicBoutique",
    "style_tags": ["floral", "midi", "casual"],
    "seasonal_tags": ["summer", "spring"],
    "image_url": "https://cdn.example.com/item_456.jpg"
}
```

---

## 🚀 API Specifications

### Core Endpoints

#### Generate Campaign
```http
POST /v1/campaigns/generate
Content-Type: application/json
Authorization: Bearer {tenant_api_key}

{
    "tenant_id": "tenant_123",
    "recommendations": [...],  // Two-tower recommendation output
    "campaign_settings": {
        "name": "Spring Collection Launch",
        "send_date": "2026-02-01T10:00:00Z",
        "template_id": "spring_2026_v1"
    },
    "brand_voice": {
        "tone": "friendly",
        "personality": "sophisticated",
        "avoid_phrases": ["cheap", "discount"]
    }
}
```

**Response**:
```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
    "task_id": "task_campaign_789",
    "status": "processing",
    "estimated_completion": "2026-01-16T16:30:00Z"
}
```

#### Campaign Status
```http
GET /v1/campaigns/{campaign_id}
Authorization: Bearer {tenant_api_key}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "campaign_id": "camp_456",
    "status": "completed",
    "segments": [
        {
            "segment_id": "seg_001",
            "label": "Contemporary Minimalists",
            "recipient_count": 1250,
            "estimated_performance": {
                "predicted_open_rate": 0.32,
                "predicted_click_rate": 0.08,
                "predicted_conversion_rate": 0.02
            }
        }
    ],
    "total_cost": {
        "llm_tokens": 15420,
        "estimated_cost_usd": 2.45,
        "processing_time_seconds": 180
    }
}
```

#### Retrieve Campaign Content
```http
GET /v1/campaigns/{campaign_id}/content
Authorization: Bearer {tenant_api_key}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "campaign_id": "camp_456",
    "segments": [
        {
            "segment_id": "seg_001",
            "email_copy": {
                "subject_line": "Minimalist Elegance: Your Curated Picks",
                "preview_text": "Sophisticated styles just for your aesthetic...",
                "body_html": "<!DOCTYPE html>...",
                "cta_text": "Explore Collection"
            },
            "items": [
                {
                    "item_id": "item_123",
                    "name": "Structured Blazer",
                    "price": 149.99,
                    "image_url": "..."
                }
            ]
        }
    ]
}
```

### Rate Limiting & Authentication
- **Rate Limits**: 10 requests/hour per tenant
- **Authentication**: Bearer token in Authorization header
- **API Key Management**: Tenant portal for key generation/rotation

---

## 📈 Monitoring & Analytics

### Key Performance Indicators (KPIs)

#### Operational Metrics
- **Processing Time**: Target <5 minutes for 100K users
- **Segmentation Quality**: Cluster cohesion score >0.7
- **Recommendation Accuracy**: LLM-judged relevance >90%
- **System Uptime**: 99.9% availability target

#### Business Metrics
- **Campaign Performance**: vs. baseline manual campaigns
  - Open Rate: Target +20% improvement
  - Click Rate: Target +25% improvement
  - Conversion Rate: Target +15% improvement
- **Cost Efficiency**: Cost per campaign <$5
- **Time Savings**: 80% reduction in campaign creation time

### Monitoring Dashboard
```python
# Real-time metrics
METRICS_DASHBOARD = {
    "campaigns_generated_today": 12,
    "total_segments_created": 89,
    "average_processing_time": "4m 32s",
    "system_health": "operational",
    "cost_today_usd": 24.50,
    "active_tenants": 15
}
```

---

## 🔒 Security & Compliance

### Data Privacy
- **PII Protection**: No user PII stored in campaign logs
- **Data Retention**: Campaign data retained 90 days
- **GDPR Compliance**: User consent tracking for segmentation
- **Encryption**: All data encrypted in transit and at rest

### Access Control
- **Multi-tenant Isolation**: Strict data separation
- **Role-based Access**: Admin, Developer, Read-only roles
- **API Key Management**: Automated key rotation
- **Audit Logging**: All actions logged with timestamps

---

## 💰 Cost Estimation

### LLM Usage Breakdown
```python
COST_BREAKDOWN = {
    "segmentation_agent": {
        "tokens_per_campaign": 5000,
        "cost_per_campaign": 0.05
    },
    "judgment_agent": {
        "tokens_per_item": 200,
        "items_per_user": 5,
        "cost_per_user": 0.02
    },
    "campaign_writer": {
        "tokens_per_segment": 1500,
        "segments_per_campaign": 5,
        "cost_per_campaign": 0.15
    }
}

# Total estimated cost per 100K user campaign
TOTAL_COST = (
    0.05 +           # Segmentation
    (100000 * 0.02) + # Judgment (100K users)
    0.15             # Campaign writing
)  # ≈ $2,000 per campaign
```

---

## 🧪 Testing Strategy

### Unit Tests
- **Segmentation Accuracy**: Test clustering on synthetic data
- **Judgment Quality**: Validate LLM scoring consistency
- **Content Generation**: Brand voice compliance testing
- **API Integration**: End-to-end workflow testing

### Integration Tests
```python
# Mock two-tower output test
def test_full_pipeline():
    # Input: 1000 users, 5 recommendations each
    recommendations = generate_mock_recommendations(1000, 5)
    
    # Execute full pipeline
    campaign = generate_campaign(recommendations)
    
    # Assertions
    assert len(campaign.segments) >= 1
    assert all(seg.size >= 50 for seg in campaign.segments)
    assert campaign.validate_html()
    assert not campaign.contains_pii()
```

### Load Testing
- **Segmentation**: 1M users in <10 minutes
- **Campaign Generation**: 100K users in <5 minutes
- **API Throughput**: 100 requests/second
- **Database Performance**: 10K queries/second

---

## 📅 Timeline & Milestones

### Development Schedule (8 Weeks)

| Week | Milestone | Deliverables |
|------|-----------|-------------|
| 1-2 | Core Pipeline | SegmentationAgent, JudgmentAgent |
| 3-4 | Campaign Generation | CampaignWriter, Templates |
| 5-6 | Integration | FastAPI, Authentication, Monitoring |
| 7-8 | Optimization | Performance tuning, Advanced features |

### Launch Criteria
- [ ] All unit tests passing (≥95% coverage)
- [ ] Integration tests completing successfully
- [ ] Load testing benchmarks met
- [ ] Security audit completed
- [ ] Documentation finalized
- [ ] Training materials prepared

---

## 🎯 Success Criteria

### Technical Success
- ✅ System processes 100K users in <5 minutes
- ✅ Segmentation creates ≥3 viable segments per campaign
- ✅ LLM judgments achieve ≥90% relevance accuracy
- ✅ Generated HTML validates W3C standards
- ✅ API handles 100 RPS with <200ms response time

### Business Success
- ✅ 15-25% improvement in email engagement
- ✅ 80% reduction in campaign creation time
- ✅ <$5 cost per campaign (100K users)
- ✅ 99.9% system uptime
- ✅ Customer satisfaction score >4.5/5

---

## 🚀 Next Steps

1. **Stakeholder Approval**: Present PRD to engineering and product teams
2. **Resource Allocation**: Assign development team and timeline
3. **Infrastructure Setup**: Provision development environment
4. **Data Pipeline**: Establish connection with recommendation engine
5. **Pilot Program**: Launch with 2-3 beta tenants

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-16  
**Next Review**: 2026-01-30  

This PRD provides a comprehensive blueprint for implementing the Fashion Email Campaign Generator using the ReasonLoop framework. The system will transform anonymous recommendation data into personalized, brand-consistent email campaigns while maintaining high quality standards and operational efficiency.