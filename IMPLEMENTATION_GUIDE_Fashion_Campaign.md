# Fashion Email Campaign Generator - Implementation Guide

**Version**: 1.0  
**Date**: 2026-01-16  
**Framework**: ReasonLoop v2.0  
**Status**: Ready for Implementation  

---

## 🎯 Overview

This guide provides step-by-step instructions for implementing the Fashion Email Campaign Generator using ReasonLoop's multi-agent architecture. The system transforms raw recommendation engine outputs into personalized, segment-targeted email campaigns.

## 📋 Prerequisites

### System Requirements
- ReasonLoop v2.0+ installed and configured
- Python 3.8+
- Access to LLM providers (XAI, OpenAI, or Anthropic)
- Database (MySQL/PostgreSQL) for campaign storage
- Email service provider integration

### Environment Setup
```bash
# Install additional dependencies
pip install scikit-learn fastapi uvicorn sqlalchemy alembic

# Create campaign directories
mkdir -p /var/campaign/templates/{tenant_id}
mkdir -p /var/campaign/logs
mkdir -p /var/campaign/outputs
```

## 🏗️ Implementation Steps

### Step 1: Create Custom Abilities

#### 1.1 SegmentationAgent

Create `abilities/segmentation_agent.py`:

```python
"""
Segmentation Agent - Clusters users by recommendation similarity
"""
import logging
import json
from typing import List, Tuple, Dict, Any
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import jaccard_score
import numpy as np
from dataclasses import dataclass

from utils.settings import get_setting

logger = logging.getLogger(__name__)

@dataclass
class Segment:
    segment_id: str
    user_ids: List[str]
    top_items: List[str]
    size: int
    label: str
    description: str
    style_tags: List[str]
    avg_order_value: float = 0.0
    created_at: Any = None

class SegmentationAgent:
    def __init__(self):
        self.min_segment_size = get_setting("MIN_SEGMENT_SIZE", 50)
        self.similarity_threshold = get_setting("SIMILARITY_THRESHOLD", 0.3)
        self.max_segments = get_setting("MAX_SEGMENTS", 10)

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """
        Input: List of {'user_id': str, 'items': List[str], 'scores': List[float]}
        Output: List of Segment objects
        """
        logger.info(f"Processing {len(recommendations)} user recommendations")
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(recommendations)
        
        # Perform clustering
        segments = self._cluster_users(recommendations, similarity_matrix)
        
        # Generate semantic labels
        segments = self._generate_labels(segments)
        
        logger.info(f"Created {len(segments)} segments")
        return segments

    def _calculate_similarity_matrix(self, recommendations: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate Jaccard similarity between user recommendation sets"""
        n_users = len(recommendations)
        similarity_matrix = np.zeros((n_users, n_users))
        
        for i in range(n_users):
            for j in range(i + 1, n_users):
                items_i = set(recommendations[i]['items'][:5])  # Top 5 items
                items_j = set(recommendations[j]['items'][:5])
                
                if len(items_i) == 0 and len(items_j) == 0:
                    similarity = 0.0
                else:
                    intersection = len(items_i.intersection(items_j))
                    union = len(items_i.union(items_j))
                    similarity = intersection / union if union > 0 else 0.0
                
                similarity_matrix[i][j] = similarity_matrix[j][i] = similarity
        
        return similarity_matrix

    def _cluster_users(self, recommendations: List[Dict], similarity_matrix: np.ndarray) -> List[Segment]:
        """Cluster users using DBSCAN based on similarity"""
        # Convert similarity to distance matrix
        distance_matrix = 1 - similarity_matrix
        
        # Apply DBSCAN clustering
        clustering = DBSCAN(
            eps=1 - self.similarity_threshold,
            min_samples=2,
            metric='precomputed'
        )
        
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Group users by cluster
        segments = []
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # Noise points
                continue
                
            cluster_users = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            
            if len(cluster_users) >= self.min_segment_size:
                segment = self._create_segment(recommendations, cluster_users, cluster_id)
                segments.append(segment)
        
        return segments[:self.max_segments]

    def _create_segment(self, recommendations: List[Dict], user_indices: List[int], segment_id: str) -> Segment:
        """Create segment from clustered users"""
        user_ids = [recommendations[i]['user_id'] for i in user_indices]
        
        # Get top items across segment
        all_items = []
        for i in user_indices:
            all_items.extend(recommendations[i]['items'][:3])  # Top 3 per user
        
        # Count item frequency
        item_counts = {}
        for item in all_items:
            item_counts[item] = item_counts.get(item, 0) + 1
        
        top_items = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:5]
        
        return Segment(
            segment_id=f"seg_{segment_id}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(user_ids),
            label="",  # Will be filled by label generation
            description="",
            style_tags=[]
        )

    def _generate_labels(self, segments: List[Segment]) -> List[Segment]:
        """Generate semantic labels for segments using LLM"""
        from abilities.text_completion import text_completion_ability
        
        for segment in segments:
            prompt = f"""Given these top recommended fashion items: {', '.join(segment.top_items[:3])}

Generate a concise, marketing-friendly segment name (max 4 words) that a fashion brand would use. Consider:
- Style aesthetics (minimalist, bohemian, preppy, etc.)
- Occasion (workwear, casual, party, etc.)
- Demographics (young professionals, students, etc.)

Respond with only the segment name."""
            
            try:
                response = text_completion_ability(
                    prompt,
                    role="executor",
                    return_usage=True
                )
                
                if isinstance(response, tuple):
                    response, usage = response
                
                segment.label = response.strip()
                logger.debug(f"Generated label '{segment.label}' for segment {segment.segment_id}")
                
            except Exception as e:
                logger.error(f"Failed to generate label for segment {segment.segment_id}: {e}")
                segment.label = f"Segment {segment.segment_id}"
        
        return segments

def segmentation_ability(recommendations_json: str) -> str:
    """
    ReasonLoop ability wrapper for segmentation
    Input: JSON string of recommendations
    Output: JSON string of segments
    """
    try:
        recommendations = json.loads(recommendations_json)
        agent = SegmentationAgent()
        segments = agent.process_recommendations(recommendations)
        
        # Convert to JSON
        segments_data = []
        for segment in segments:
            segments_data.append({
                "segment_id": segment.segment_id,
                "user_ids": segment.user_ids,
                "top_items": segment.top_items,
                "size": segment.size,
                "label": segment.label,
                "description": segment.description,
                "style_tags": segment.style_tags
            })
        
        return json.dumps({
            "segments": segments_data,
            "total_segments": len(segments),
            "total_users": sum(seg.size for seg in segments)
        })
        
    except Exception as e:
        logger.error(f"Segmentation failed: {e}")
        return json.dumps({"error": str(e), "segments": []})
```

#### 1.2 JudgmentAgent

Create `abilities/judgment_agent.py`:

```python
"""
Judgment Agent - LLM-as-a-Judge for recommendation quality validation
"""
import logging
import json
from typing import List, Dict, Any
from dataclasses import dataclass

from abilities.text_completion import text_completion_ability
from utils.settings import get_setting

logger = logging.getLogger(__name__)

@dataclass
class JudgmentResult:
    item_id: str
    rating: float
    reasoning: str
    alternative_suggestions: List[str] = None
    confidence: float = 0.0

class JudgmentAgent:
    def __init__(self):
        self.min_rating = get_setting("JUDGMENT_MIN_RATING", 3.0)
        self.include_reasoning = get_setting("JUDGMENT_INCLUDE_REASONING", True)
        self.suggest_alternatives = get_setting("JUDGMENT_SUGGEST_ALTERNATIVES", True)

    def evaluate_recommendations(self, user_profile: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate recommendation quality using LLM-as-a-Judge
        Input: user_profile and list of item dictionaries
        Output: filtered items with ratings and reasoning
        """
        logger.info(f"Evaluating {len(items)} items for user {user_profile.get('user_id')}")
        
        evaluated_items = []
        
        for item in items:
            try:
                result = self._evaluate_single_item(user_profile, item)
                if result.rating >= self.min_rating:
                    evaluated_items.append({
                        **item,
                        "judgment_rating": result.rating,
                        "judgment_reasoning": result.reasoning,
                        "alternatives": result.alternative_suggestions or []
                    })
                    
            except Exception as e:
                logger.error(f"Failed to evaluate item {item.get('item_id')}: {e}")
                continue
        
        logger.info(f"Kept {len(evaluated_items)}/{len(items)} items after judgment")
        return evaluated_items

    def _evaluate_single_item(self, user_profile: Dict[str, Any], item: Dict[str, Any]) -> JudgmentResult:
        """Evaluate a single item using LLM reasoning"""
        
        prompt = f"""Evaluate this fashion recommendation for the user profile.

USER PROFILE:
- Past purchases: {user_profile.get('past_purchases', [])}
- Style preferences: {user_profile.get('style_tags', [])}
- Size: {user_profile.get('size', 'Unknown')}
- Budget range: ${user_profile.get('budget_min', 0)}-${user_profile.get('budget_max', 1000)}
- Age group: {user_profile.get('age_group', 'Unknown')}

ITEM TO EVALUATE:
- Name: {item.get('name', 'Unknown')}
- Category: {item.get('category', 'Unknown')}
- Price: ${item.get('price', 0)}
- Brand: {item.get('brand', 'Unknown')}
- Style tags: {item.get('style_tags', [])}
- Seasonal relevance: {item.get('seasonal_tags', [])}

Evaluate on a scale of 1-5 where:
1 = Completely inappropriate
2 = Poor fit, unlikely to appeal
3 = Decent match, some concerns
4 = Good fit, likely to appeal
5 = Excellent match, high confidence

Respond in JSON format:
{{
    "rating": <number 1-5>,
    "reasoning": "<brief explanation>",
    "confidence": <number 0-1>,
    "alternatives": ["suggestion1", "suggestion2"] (only if rating < 3)
}}"""

        try:
            response = text_completion_ability(
                prompt,
                role="reasoning_critic",
                return_usage=True
            )
            
            if isinstance(response, tuple):
                response, usage = response
            
            # Parse JSON response
            try:
                result_data = json.loads(response)
                return JudgmentResult(
                    item_id=item.get('item_id'),
                    rating=result_data.get('rating', 1.0),
                    reasoning=result_data.get('reasoning', ''),
                    alternative_suggestions=result_data.get('alternatives', []),
                    confidence=result_data.get('confidence', 0.5)
                )
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response for item {item.get('item_id')}")
                return JudgmentResult(
                    item_id=item.get('item_id'),
                    rating=1.0,
                    reasoning="Unable to parse evaluation",
                    confidence=0.0
                )
                
        except Exception as e:
            logger.error(f"LLM evaluation failed for item {item.get('item_id')}: {e}")
            return JudgmentResult(
                item_id=item.get('item_id'),
                rating=1.0,
                reasoning=f"Evaluation failed: {str(e)}",
                confidence=0.0
            )

def judgment_ability(user_profile_json: str, items_json: str) -> str:
    """
    ReasonLoop ability wrapper for judgment
    Input: JSON strings of user_profile and items
    Output: JSON string of evaluated items
    """
    try:
        user_profile = json.loads(user_profile_json)
        items = json.loads(items_json)
        
        agent = JudgmentAgent()
        evaluated_items = agent.evaluate_recommendations(user_profile, items)
        
        return json.dumps({
            "evaluated_items": evaluated_items,
            "total_evaluated": len(items),
            "items_kept": len(evaluated_items),
            "filter_rate": len(evaluated_items) / len(items) if items else 0
        })
        
    except Exception as e:
        logger.error(f"Judgment evaluation failed: {e}")
        return json.dumps({"error": str(e), "evaluated_items": []})
```

#### 1.3 CampaignWriter

Create `abilities/campaign_writer.py`:

```python
"""
Campaign Writer - Generates brand-consistent email content
"""
import logging
import json
from typing import Dict, Any, List
from dataclasses import dataclass
from jinja2 import Template

from abilities.text_completion import text_completion_ability
from utils.settings import get_setting

logger = logging.getLogger(__name__)

@dataclass
class EmailCopy:
    subject_line: str
    preview_text: str
    body_html: str
    cta_text: str
    utm_parameters: Dict[str, str]

class CampaignWriter:
    def __init__(self):
        self.max_subject_length = get_setting("EMAIL_SUBJECT_MAX_LENGTH", 50)
        self.template_dir = get_setting("EMAIL_TEMPLATE_DIR", "/var/campaign/templates")
        self.brand_voice_templates = {
            "friendly": "warm, approachable, conversational",
            "professional": "polished, informative, authoritative", 
            "casual": "relaxed, trendy, youthful",
            "luxury": "sophisticated, exclusive, refined"
        }

    def generate_email_copy(self, segment: Dict[str, Any], refined_items: List[Dict[str, Any]], brand_voice: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete email campaign for a segment
        """
        logger.info(f"Generating email copy for segment {segment.get('segment_id')} with {len(refined_items)} items")
        
        try:
            # Generate subject line
            subject_line = self._generate_subject_line(segment, refined_items, brand_voice)
            
            # Generate preview text
            preview_text = self._generate_preview_text(segment, refined_items, brand_voice)
            
            # Generate email body
            body_html = self._generate_email_body(segment, refined_items, brand_voice)
            
            # Generate CTA
            cta_text = self._generate_cta(segment, brand_voice)
            
            # Create UTM parameters
            utm_parameters = self._create_utm_parameters(segment)
            
            return {
                "subject_line": subject_line,
                "preview_text": preview_text,
                "body_html": body_html,
                "cta_text": cta_text,
                "utm_parameters": utm_parameters,
                "word_count": len(subject_line.split()) + len(preview_text.split())
            }
            
        except Exception as e:
            logger.error(f"Failed to generate email copy: {e}")
            raise

    def _generate_subject_line(self, segment: Dict[str, Any], items: List[Dict], brand_voice: Dict[str, Any]) -> str:
        """Generate compelling subject line"""
        
        prompt = f"""Generate an email subject line for this fashion segment.

SEGMENT: {segment.get('label', 'Fashion Lovers')}
TOP ITEMS: {', '.join([item.get('name', '') for item in items[:3]])}
BRAND VOICE: {brand_voice.get('tone', 'friendly')}
AVOID: {', '.join(brand_voice.get('avoid_phrases', []))}

Requirements:
- Max {self.max_subject_length} characters
- Include urgency or personalization
- Match brand voice
- Avoid spam trigger words
- Include 1-2 key product categories

Generate only the subject line, nothing else."""

        try:
            response = text_completion_ability(
                prompt,
                role="copywriter",
                return_usage=True
            )
            
            if isinstance(response, tuple):
                response, usage = response
            
            subject_line = response.strip()
            
            # Ensure length constraint
            if len(subject_line) > self.max_subject_length:
                subject_line = subject_line[:self.max_subject_length-3] + "..."
            
            return subject_line
            
        except Exception as e:
            logger.error(f"Subject line generation failed: {e}")
            return f"New Collection for {segment.get('label', 'You')}"

    def _generate_preview_text(self, segment: Dict[str, Any], items: List[Dict], brand_voice: Dict[str, Any]) -> str:
        """Generate email preview text"""
        
        prompt = f"""Generate preview text (also called preheader) for this fashion email.

SEGMENT: {segment.get('label', 'Fashion Lovers')}
BRAND VOICE: {brand_voice.get('tone', 'friendly')}
KEY ITEMS: {', '.join([item.get('name', '') for item in items[:2]])}

Requirements:
- 80-120 characters
- Complements the subject line
- Creates curiosity
- Matches brand voice
- Avoids repetition with subject

Generate only the preview text."""

        try:
            response = text_completion_ability(
                prompt, role="copywriter", return_usage=True)
            if isinstance(response, tuple):
                response, usage = response
            return response.strip()
        except Exception as e:
            logger.error(f"Preview text generation failed: {e}")
            return f"Curated styles just for you..."

    def _generate_email_body(self, segment: Dict[str, Any], items: List[Dict], brand_voice: Dict[str, Any]) -> str:
        """Generate HTML email body"""
        
        # Load template
        template_path = f"{self.template_dir}/{brand_voice.get('template_id', 'default')}/email.j2"
        
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            # Prepare template variables
            template_vars = {
                'segment_label': segment.get('label', 'Fashion Lovers'),
                'items': items[:6],  # Max 6 items in email
                'brand_voice': brand_voice,
                'utm_base': self._create_utm_parameters(segment),
                'current_year': 2026
            }
            
            return template.render(**template_vars)
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return self._generate_fallback_email(segment, items, brand_voice)

    def _generate_fallback_email(self, segment: Dict[str, Any], items: List[Dict], brand_voice: Dict[str, Any]) -> str:
        """Fallback HTML email when template fails"""
        
        items_html = ""
        for item in items[:6]:
            items_html += f"""
            <div class="product-card">
                <img src="{item.get('image_url', '')}" alt="{item.get('name', '')}" style="width: 200px; height: 200px; object-fit: cover;">
                <h3>{item.get('name', '')}</h3>
                <p>${item.get('price', 0)}</p>
                <a href="{item.get('product_url', '#')}">Shop Now</a>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{segment.get('label', 'Fashion Collection')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .header {{ text-align: center; padding: 20px 0; }}
                .products {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
                .product-card {{ border: 1px solid #ddd; padding: 15px; text-align: center; width: 200px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Curated for {segment.get('label', 'You')}</h1>
                <p>Handpicked styles we think you'll love</p>
            </div>
            <div class="products">
                {items_html}
            </div>
        </body>
        </html>
        """

    def _generate_cta(self, segment: Dict[str, Any], brand_voice: Dict[str, Any]) -> str:
        """Generate call-to-action text"""
        
        cta_templates = {
            "friendly": ["Shop Your Styles", "Explore Collection", "Find Your Look"],
            "professional": ["View Collection", "Browse Selection", "Shop Now"],
            "casual": ["Check It Out", "See What's Hot", "Get Yours"],
            "luxury": ["Discover", "Explore Collection", "View Selection"]
        }
        
        tone = brand_voice.get('tone', 'friendly')
        options = cta_templates.get(tone, cta_templates['friendly'])
        
        return options[0]  # Return first option

    def _create_utm_parameters(self, segment: Dict[str, Any]) -> Dict[str, str]:
        """Create UTM tracking parameters"""
        return {
            'utm_source': 'email',
            'utm_medium': 'campaign',
            'utm_campaign': f"segment_{segment.get('segment_id', 'general')}",
            'utm_content': segment.get('label', 'general').lower().replace(' ', '_')
        }

def campaign_writer_ability(segment_json: str, items_json: str, brand_voice_json: str) -> str:
    """
    ReasonLoop ability wrapper for campaign writing
    Input: JSON strings of segment, refined_items, and brand_voice
    Output: JSON string of email copy
    """
    try:
        segment = json.loads(segment_json)
        items = json.loads(items_json)
        brand_voice = json.loads(brand_voice_json)
        
        writer = CampaignWriter()
        email_copy = writer.generate_email_copy(segment, items, brand_voice)
        
        return json.dumps({
            "email_copy": email_copy,
            "segment_id": segment.get('segment_id'),
            "items_count": len(items)
        })
        
    except Exception as e:
        logger.error(f"Campaign writing failed: {e}")
        return json.dumps({"error": str(e), "email_copy": {}})
```

### Step 2: Register New Abilities

Update `abilities/ability_registry.py`:

```python
# Add these imports at the top
from abilities.segmentation_agent import segmentation_ability
from abilities.judgment_agent import judgment_ability  
from abilities.campaign_writer import campaign_writer_ability

# Register new abilities in the register function
def register_abilities():
    # ... existing abilities ...
    
    # Register fashion campaign abilities
    register_ability("segmentation", segmentation_ability)
    register_ability("judgment", judgment_ability)
    register_ability("campaign-writing", campaign_writer_ability)
```

### Step 3: Add New Model Roles

Update `config/settings.py` to support the new roles:

```python
# Add to the settings loading
self._load_env_var("XAI_MODEL_REASONING_CRITIC")
self._load_env_var("XAI_MODEL_COPYWRITER")

# Add to model selection function
def get_model_for_provider(provider: str, role: str = None) -> str:
    # ... existing code ...
    
    if role == "reasoning_critic":
        role_key = f"{provider.upper()}_MODEL_REASONING_CRITIC"
        model = _settings.get(role_key)
        if model and model.strip():
            return model
    elif role == "copywriter":
        role_key = f"{provider.upper()}_MODEL_COPYWRITER"
        model = _settings.get(role_key)
        if model and model.strip():
            return model
    
    # ... rest of existing function ...
```

### Step 4: Create Campaign Templates

Create email templates:

```html
<!-- /var/campaign/templates/default/email.j2 -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ segment_label }}</title>
    <style>
        body {
            font-family: {{ brand_voice.get('font_family', 'Arial, sans-serif') }};
            margin: 0;
            padding: 0;
            background-color: {{ brand_voice.get('background_color', '#f5f5f5') }};
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
        }
        .header {
            text-align: center;
            padding: 30px 20px;
            background: linear-gradient(135deg, {{ brand_voice.get('primary_color', '#000' }} 0%, {{ brand_voice.get('secondary_color', '#333' }} 100%);
            color: white;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 16px;
        }
        .products {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            padding: 30px 20px;
        }
        .product {
            width: 48%;
            margin-bottom: 30px;
            text-align: center;
        }
        .product img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .product h3 {
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }
        .product .price {
            font-size: 18px;
            font-weight: bold;
            color: {{ brand_voice.get('primary_color', '#000') }};
            margin-bottom: 15px;
        }
        .cta-button {
            display: inline-block;
            background-color: {{ brand_voice.get('primary_color', '#000') }};
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: opacity 0.3s;
        }
        .cta-button:hover {
            opacity: 0.8;
        }
        .footer {
            background-color: #f8f8f8;
            padding: 30px 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }
        @media (max-width: 480px) {
            .product {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Curated for {{ segment_label }}</h1>
            <p>Handpicked styles we think you'll love</p>
        </div>
        
        <div class="products">
            {% for item in items %}
            <div class="product">
                <img src="{{ item.image_url }}" alt="{{ item.name }}">
                <h3>{{ item.name }}</h3>
                <div class="price">${{ "%.2f"|format(item.price) }}</div>
                <a href="{{ item.product_url }}?{{ utm_base|urlencode }}" class="cta-button">
                    Shop Now
                </a>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>You're receiving this because you're part of our {{ segment_label }} community.</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> | <a href="{{ preferences_url }}">Update Preferences</a></p>
            <p>&copy; {{ current_year }} Your Brand Name. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

### Step 5: Create Integration Script

Create `fashion_campaign_pipeline.py`:

```python
"""
Fashion Campaign Pipeline - Orchestrates the complete campaign generation process
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from abilities.segmentation_agent import SegmentationAgent
from abilities.judgment_agent import JudgmentAgent
from abilities.campaign_writer import CampaignWriter

logger = logging.getLogger(__name__)

class FashionCampaignPipeline:
    def __init__(self):
        self.segmentation_agent = SegmentationAgent()
        self.judgment_agent = JudgmentAgent()
        self.campaign_writer = CampaignWriter()
        
    def generate_campaign(self, recommendations: List[Dict], tenant_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete campaign generation pipeline
        """
        logger.info("Starting fashion campaign generation")
        start_time = datetime.now()
        
        try:
            # Step 1: Create user segments
            logger.info("Step 1: Creating user segments")
            segments_data = self.segmentation_agent.process_recommendations(recommendations)
            
            # Convert segments to dictionaries for processing
            segments = []
            for seg in segments_data:
                segments.append({
                    "segment_id": seg.segment_id,
                    "user_ids": seg.user_ids,
                    "top_items": seg.top_items,
                    "size": seg.size,
                    "label": seg.label,
                    "description": seg.description,
                    "style_tags": seg.style_tags
                })
            
            # Step 2: Generate campaign for each segment
            campaign_segments = []
            total_cost = 0
            
            for segment in segments:
                logger.info(f"Processing segment: {segment['label']} ({segment['size']} users)")
                
                # Get user profiles for this segment
                segment_users = self._get_user_profiles(segment['user_ids'], tenant_config)
                
                # Evaluate recommendations for each user
                evaluated_items = []
                for user_profile in segment_users:
                    user_recommendations = self._get_user_recommendations(user_profile['user_id'], recommendations)
                    user_items = self.judgment_agent.evaluate_recommendations(user_profile, user_recommendations)
                    evaluated_items.extend(user_items)
                
                # Remove duplicates and get top items
                unique_items = self._deduplicate_items(evaluated_items)
                top_items = unique_items[:6]  # Top 6 items
                
                # Generate email copy
                email_copy = self.campaign_writer.generate_email_copy(
                    segment, top_items, tenant_config['brand_voice']
                )
                
                campaign_segments.append({
                    "segment": segment,
                    "email_copy": email_copy,
                    "refined_items": top_items,
                    "recipient_count": segment['size']
                })
                
                # Log segment processing
                logger.info(f"Segment {segment['label']}: {len(top_items)} items, {segment['size']} recipients")
            
            # Create final campaign structure
            campaign = {
                "campaign_id": f"camp_{int(datetime.now().timestamp())}",
                "tenant_id": tenant_config['tenant_id'],
                "created_at": start_time.isoformat(),
                "segments": campaign_segments,
                "total_recipients": sum(seg['recipient_count'] for seg in campaign_segments),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds()
            }
            
            # Save campaign to file
            self._save_campaign_log(campaign, tenant_config)
            
            logger.info(f"Campaign generation completed: {len(campaign_segments)} segments, {campaign['total_recipients']} recipients")
            return campaign
            
        except Exception as e:
            logger.error(f"Campaign generation failed: {e}")
            raise

    def _get_user_profiles(self, user_ids: List[str], tenant_config: Dict) -> List[Dict]:
        """Get user profiles from database or external API"""
        # This would integrate with your user database
        # For now, return mock data
        return [
            {
                "user_id": user_id,
                "past_purchases": ["dress_123", "shoes_456"],
                "style_tags": ["casual", "modern"],
                "size": "M",
                "budget_min": 50,
                "budget_max": 200,
                "age_group": "25-34"
            }
            for user_id in user_ids[:10]  # Mock first 10 users
        ]

    def _get_user_recommendations(self, user_id: str, all_recommendations: List[Dict]) -> List[Dict]:
        """Get recommendations for a specific user"""
        user_recs = [r for r in all_recommendations if r['user_id'] == user_id]
        return user_recs[0]['items'] if user_recs else []

    def _deduplicate_items(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate items based on item_id"""
        seen = set()
        unique_items = []
        
        for item in items:
            item_id = item.get('item_id')
            if item_id and item_id not in seen:
                seen.add(item_id)
                unique_items.append(item)
        
        return unique_items

    def _save_campaign_log(self, campaign: Dict, tenant_config: Dict):
        """Save campaign generation log"""
        log_data = {
            "campaign": campaign,
            "tenant_config": {
                "tenant_id": tenant_config['tenant_id'],
                "brand_voice": tenant_config['brand_voice']
            },
            "input_summary": {
                "total_users": len(tenant_config.get('recommendations', [])),
                "total_segments": len(campaign['segments'])
            }
        }
        
        log_file = f"/var/campaign/logs/campaign_{campaign['campaign_id']}.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Campaign log saved: {log_file}")

# Usage example
if __name__ == "__main__":
    # Mock input data
    recommendations = [
        {
            "user_id": "user_123",
            "items": ["item_456", "item_789", "item_012"],
            "scores": [0.95, 0.87, 0.76]
        }
        # ... more users
    ]
    
    tenant_config = {
        "tenant_id": "tenant_123",
        "brand_voice": {
            "tone": "friendly",
            "template_id": "default",
            "primary_color": "#000000"
        }
    }
    
    pipeline = FashionCampaignPipeline()
    campaign = pipeline.generate_campaign(recommendations, tenant_config)
    print(json.dumps(campaign, indent=2))
```

## 🧪 Testing Implementation

### Unit Tests

Create `tests/test_fashion_campaign.py`:

```python
import pytest
import json
from unittest.mock import patch, MagicMock

from abilities.segmentation_agent import SegmentationAgent, segmentation_ability
from abilities.judgment_agent import JudgmentAgent, judgment_ability
from abilities.campaign_writer import CampaignWriter, campaign_writer_ability
from fashion_campaign_pipeline import FashionCampaignPipeline

class TestSegmentationAgent:
    def test_process_recommendations(self):
        """Test user segmentation with mock data"""
        agent = SegmentationAgent()
        
        recommendations = [
            {
                "user_id": "user_1",
                "items": ["item_a", "item_b", "item_c"],
                "scores": [0.9, 0.8, 0.7]
            },
            {
                "user_id": "user_2", 
                "items": ["item_a", "item_d", "item_e"],
                "scores": [0.9, 0.6, 0.5]
            }
        ]
        
        segments = agent.process_recommendations(recommendations)
        
        assert len(segments) >= 1
        assert all(hasattr(seg, 'segment_id') for seg in segments)
        assert all(hasattr(seg, 'label') for seg in segments)

    def test_segmentation_ability_wrapper(self):
        """Test ReasonLoop ability wrapper"""
        recommendations = json.dumps([
            {"user_id": "user_1", "items": ["item_a"], "scores": [0.9]}
        ])
        
        result = segmentation_ability(recommendations)
        result_data = json.loads(result)
        
        assert "segments" in result_data
        assert isinstance(result_data["segments"], list)

class TestJudgmentAgent:
    @patch('abilities.text_completion.text_completion_ability')
    def test_evaluate_recommendations(self, mock_llm):
        """Test LLM-as-a-Judge evaluation"""
        mock_llm.return_value = json.dumps({
            "rating": 4,
            "reasoning": "Good style match",
            "confidence": 0.8
        })
        
        agent = JudgmentAgent()
        
        user_profile = {"user_id": "user_1", "style_tags": ["casual"]}
        items = [{"item_id": "item_1", "name": "Casual T-Shirt", "price": 25}]
        
        evaluated = agent.evaluate_recommendations(user_profile, items)
        
        assert len(evaluated) == 1
        assert evaluated[0]["judgment_rating"] == 4

class TestCampaignWriter:
    def test_generate_email_copy(self):
        """Test email content generation"""
        writer = CampaignWriter()
        
        segment = {"segment_id": "seg_1", "label": "Casual Lovers"}
        items = [{"name": "T-Shirt", "price": 25, "image_url": "url"}]
        brand_voice = {"tone": "friendly"}
        
        email_copy = writer.generate_email_copy(segment, items, brand_voice)
        
        assert "subject_line" in email_copy
        assert "body_html" in email_copy
        assert len(email_copy["subject_line"]) <= 50

class TestFashionCampaignPipeline:
    def test_generate_campaign(self):
        """Test complete campaign generation"""
        pipeline = FashionCampaignPipeline()
        
        recommendations = [
            {"user_id": "user_1", "items": ["item_a"], "scores": [0.9]}
        ]
        tenant_config = {
            "tenant_id": "tenant_1",
            "brand_voice": {"tone": "friendly"}
        }
        
        with patch.object(pipeline.segmentation_agent, 'process_recommendations') as mock_seg:
            mock_seg.return_value = [MagicMock(
                segment_id="seg_1",
                user_ids=["user_1"],
                top_items=["item_a"],
                size=1,
                label="Test Segment"
            )]
            
            campaign = pipeline.generate_campaign(recommendations, tenant_config)
            
            assert "campaign_id" in campaign
            assert "segments" in campaign
            assert len(campaign["segments"]) >= 1

# Integration test
def test_full_pipeline_integration():
    """Test complete pipeline with mock data"""
    pipeline = FashionCampaignPipeline()
    
    # Generate mock recommendations for 100 users
    recommendations = []
    for i in range(100):
        recommendations.append({
            "user_id": f"user_{i}",
            "items": [f"item_{i}_{j}" for j in range(5)],
            "scores": [0.9 - j*0.1 for j in range(5)]
        })
    
    tenant_config = {
        "tenant_id": "test_tenant",
        "brand_voice": {
            "tone": "friendly",
            "template_id": "default"
        }
    }
    
    campaign = pipeline.generate_campaign(recommendations, tenant_config)
    
    # Assertions
    assert campaign["total_recipients"] == 100
    assert len(campaign["segments"]) >= 1
    assert all(
        "email_copy" in seg for seg in campaign["segments"]
    )
    
    # Check no PII in logs
    log_data = json.load(open(f"/var/campaign/logs/campaign_{campaign['campaign_id']}.json"))
    assert "user_1" not in str(log_data)  # Ensure no direct user IDs in logs
```

### Performance Tests

Create `tests/test_performance.py`:

```python
import time
import pytest
from fashion_campaign_pipeline import FashionCampaignPipeline

def test_large_scale_segmentation():
    """Test segmentation with 10K users"""
    pipeline = FashionCampaignPipeline()
    
    # Generate 10K mock users
    recommendations = []
    for i in range(10000):
        recommendations.append({
            "user_id": f"user_{i}",
            "items": [f"item_{j}" for j in range(5)],
            "scores": [0.9 - j*0.1 for j in range(5)]
        })
    
    start_time = time.time()
    campaign = pipeline.generate_campaign(recommendations, {"tenant_id": "perf_test"})
    end_time = time.time()
    
    processing_time = end_time - start_time
    
    # Performance assertions
    assert processing_time < 300  # Should complete in under 5 minutes
    assert campaign["processing_time_seconds"] < 300
    assert len(campaign["segments"]) >= 3  # Should create multiple segments
    
    print(f"Processed 10K users in {processing_time:.2f} seconds")
```

## 🚀 Deployment

### Environment Configuration

Add to `.env`:

```bash
# Fashion Campaign Settings
MIN_SEGMENT_SIZE=50
SIMILARITY_THRESHOLD=0.3
MAX_SEGMENTS=10

JUDGMENT_MIN_RATING=3.0
JUDGMENT_INCLUDE_REASONING=true
JUDGMENT_SUGGEST_ALTERNATIVES=true

EMAIL_SUBJECT_MAX_LENGTH=50
EMAIL_TEMPLATE_DIR=/var/campaign/templates

# LLM Model Configuration
XAI_MODEL_REASONING_CRITIC=grok-4-1-fast-non-reasoning
XAI_MODEL_COPYWRITER=grok-4-1-fast-non-reasoning
```

### Database Migration

Create migration script:

```sql
-- Create fashion campaign tables
CREATE TABLE fashion_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    label VARCHAR(128) NOT NULL,
    description TEXT,
    size INTEGER NOT NULL,
    style_tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_segment (tenant_id, segment_id)
);

CREATE TABLE fashion_campaigns (
    campaign_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    status ENUM('draft', 'generating', 'ready', 'sent', 'failed'),
    total_recipients INTEGER,
    segments_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_status (tenant_id, status)
);

CREATE TABLE campaign_performance (
    campaign_id VARCHAR(64) PRIMARY KEY,
    segment_id VARCHAR(64),
    open_rate DECIMAL(5,4),
    click_rate DECIMAL(5,4),
    conversion_rate DECIMAL(5,4),
    revenue_generated DECIMAL(10,2),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Docker Deployment

Create `Dockerfile.fashion`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy fashion campaign code
COPY fashion_campaign_pipeline.py .
COPY abilities/ ./abilities/
COPY templates/ /var/campaign/templates/

# Create directories
RUN mkdir -p /var/campaign/logs /var/campaign/outputs

EXPOSE 8000

CMD ["uvicorn", "fashion_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Monitoring

### Metrics Dashboard

Create monitoring script:

```python
# monitoring/fashion_metrics.py
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

def get_campaign_metrics(days: int = 7) -> Dict[str, Any]:
    """Get campaign performance metrics"""
    
    # Read campaign logs
    log_dir = "/var/campaign/logs"
    recent_campaigns = []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Process log files
    for log_file in Path(log_dir).glob("campaign_*.json"):
        try:
            with open(log_file) as f:
                data = json.load(f)
                campaign_date = datetime.fromisoformat(data["campaign"]["created_at"])
                
                if campaign_date >= cutoff_date:
                    recent_campaigns.append(data["campaign"])
        except Exception as e:
            logging.error(f"Failed to process {log_file}: {e}")
    
    # Calculate metrics
    total_campaigns = len(recent_campaigns)
    total_recipients = sum(c["total_recipients"] for c in recent_campaigns)
    avg_processing_time = sum(c["processing_time_seconds"] for c in recent_campaigns) / max(total_campaigns, 1)
    
    return {
        "period_days": days,
        "total_campaigns": total_campaigns,
        "total_recipients": total_recipients,
        "avg_processing_time_seconds": avg_processing_time,
        "campaigns_per_day": total_campaigns / days,
        "recipients_per_campaign": total_recipients / max(total_campaigns, 1)
    }

if __name__ == "__main__":
    metrics = get_campaign_metrics()
    print(json.dumps(metrics, indent=2))
```

## 🎯 Success Criteria

After implementation, verify:

1. **Functionality**: All agents work independently and together
2. **Performance**: 100K users processed in <5 minutes  
3. **Quality**: Generated content passes brand guidelines
4. **Scalability**: Handles 1M+ users with horizontal scaling
5. **Monitoring**: Comprehensive metrics and alerting

## 📝 Next Steps

1. **Deploy MVP**: Start with basic segmentation and campaign generation
2. **Iterate**: Add advanced features based on user feedback
3. **Scale**: Optimize for larger datasets and faster processing
4. **Enhance**: Add real-time personalization and A/B testing
5. **Integrate**: Connect with existing email service providers

This implementation guide provides everything needed to build the Fashion Email Campaign Generator using ReasonLoop's architecture. The modular design allows for incremental development and testing at each stage.