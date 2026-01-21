"""
Production-Ready SegmentationAgent for ReasonLoop Fashion Email Campaigns
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Segment:
    """User segment with characteristics"""
    segment_id: str
    user_ids: List[str]
    top_items: List[str]
    size: int
    label: str
    description: str
    style_tags: List[str]
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class SegmentationAgent:
    """Production-ready segmentation agent with reasonable defaults"""

    def __init__(self, min_size: int = 3, threshold: float = 0.2):
        self.min_cluster_size = min_size
        self.similarity_threshold = threshold

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create user segments from recommendations"""
        if not recommendations:
            return []

        # Clean data
        clean_data = self._validate_recommendations(recommendations)
        if not clean_data:
            return []

        # Create segments
        segments = self._create_segments(clean_data)

        # Generate labels
        segments = self._generate_labels(segments)

        return [seg for seg in segments if seg.size >= self.min_cluster_size]

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate recommendation data"""
        cleaned = []
        for rec in recommendations:
            # Skip invalid entries
            if not rec.get('user_id') or not rec.get('items'):
                continue

            user_id = str(rec['user_id']).strip()
            items = [str(item).strip() for item in rec.get('items', []) if str(item).strip()]

            if user_id and items:
                cleaned.append({
                    'user_id': user_id,
                    'items': items[:8],  # Limit items
                    'scores': rec.get('scores', [])[:8]
                })

        return cleaned

    def _create_segments(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create segments using simple similarity clustering"""
        segments = []
        processed = set()

        for i, rec in enumerate(recommendations):
            if rec['user_id'] in processed:
                continue

            # Start new cluster
            cluster_users = [rec['user_id']]
            cluster_items = set(rec['items'][:5])  # Top 5 items

            # Find similar users
            for other_rec in recommendations[i+1:]:
                if other_rec['user_id'] in processed:
                    continue

                other_items = set(other_rec['items'][:5])

                # Calculate similarity
                if self._calculate_similarity(cluster_items, other_items) >= self.similarity_threshold:
                    cluster_users.append(other_rec['user_id'])
                    cluster_items.update(other_items)
                    processed.add(other_rec['user_id'])

            # Create segment if enough users
            if len(cluster_users) >= 2:
                segment = self._build_segment(cluster_users, recommendations)
                segments.append(segment)
                processed.update(cluster_users)

        return segments

    def _calculate_similarity(self, items1: set, items2: set) -> float:
        """Calculate Jaccard similarity between two item sets"""
        if not items1 or not items2:
            return 0.0

        intersection = len(items1 & items2)
        union = len(items1 | items2)
        return intersection / union if union > 0 else 0.0

    def _build_segment(self, user_ids: List[str], recommendations: List[Dict[str, Any]]) -> Segment:
        """Build segment from user cluster"""
        # Count item frequency
        item_counts = {}
        for user_rec in recommendations:
            if user_rec['user_id'] in user_ids:
                for item in user_rec['items'][:5]:
                    item_counts[item] = item_counts.get(item, 0) + 1

        # Get top items
        top_items = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:5]

        # Generate label
        label = self._generate_label(top_items)
        description = f"Segment of {len(user_ids)} users with shared preferences: {', '.join(top_items[:3])}"
        style_tags = self._extract_tags(top_items)

        return Segment(
            segment_id=f"seg_{uuid.uuid4().hex[:8]}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(user_ids),
            label=label,
            description=description,
            style_tags=style_tags
        )

    def _generate_label(self, items: List[str]) -> str:
        """Generate marketing-friendly label"""
        items_text = ' '.join(items).lower()

        if any(word in items_text for word in ['blazer', 'suit', 'trousers']):
            return "Business Professionals"
        elif any(word in items_text for word in ['dress', 'skirt', 'heels']):
            return "Feminine Style"
        elif any(word in items_text for word in ['t-shirt', 'jeans', 'sneakers']):
            return "Casual Fashion"
        elif any(word in items_text for word in ['crop', 'wide', 'platform']):
            return "Trendy Styles"
        else:
            return "Fashion Lovers"

    def _extract_tags(self, items: List[str]) -> List[str]:
        """Extract style tags"""
        tags = ['fashion', 'style']
        items_text = ' '.join(items).lower()

        if any(word in items_text for word in ['blazer', 'suit']):
            tags.extend(['professional', 'workwear'])
        if any(word in items_text for word in ['dress', 'skirt']):
            tags.extend(['elegant', 'feminine'])
        if any(word in items_text for word in ['t-shirt', 'jeans']):
            tags.extend(['casual', 'comfortable'])

        return list(set(tags))[:5]

    def _generate_labels(self, segments: List[Segment]) -> List[Segment]:
        """Generate labels for segments"""
        # Labels already generated in _build_segment
        return segments

def segmentation_ability(recommendations_json: str) -> str:
    """ReasonLoop ability wrapper"""
    try:
        recommendations = json.loads(recommendations_json)
        if not isinstance(recommendations, list):
            raise ValueError("Recommendations must be a list")

        agent = SegmentationAgent()
        segments = agent.process_recommendations(recommendations)

        # Format response
        segments_data = []
        for segment in segments:
            segments_data.append({
                "segment_id": segment.segment_id,
                "user_ids": segment.user_ids,
                "top_items": segment.top_items,
                "size": segment.size,
                "label": segment.label,
                "description": segment.description,
                "style_tags": segment.style_tags,
                "created_at": segment.created_at
            })

        return json.dumps({
            "segments": segments_data,
            "total_segments": len(segments),
            "total_users": sum(seg.size for seg in segments),
            "metadata": {
                "agent_version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "segments": [],
            "total_segments": 0
        })

def test_segmentation():
    """Test the segmentation agent"""
    print("Testing SegmentationAgent...")

    # Test data
    recommendations = [
        # Business cluster
        {"user_id": "biz1", "items": ["blazer", "trousers", "dress_shoes"]},
        {"user_id": "biz2", "items": ["blazer", "shirt", "briefcase"]},
        {"user_id": "biz3", "items": ["blazer", "slacks", "oxford_shoes"]},

        # Casual cluster
        {"user_id": "cas1", "items": ["t-shirt", "jeans", "sneakers"]},
        {"user_id": "cas2", "items": ["hoodie", "sweatpants", "running_shoes"]},
        {"user_id": "cas3", "items": ["casual_shirt", "shorts", "flip_flops"]},

        # Trendy cluster
        {"user_id": "trend1", "items": ["crop_top", "wide_leg_pants", "platform_shoes"]},
        {"user_id": "trend2", "items": ["bucket_hat", "oversized_blazer", "chunky_boots"]}
    ]

    # Test
    agent = SegmentationAgent()
    segments = agent.process_recommendations(recommendations)

    print(f"Created {len(segments)} segments:")
    for segment in segments:
        print(f"- {segment.label}: {segment.size} users")
        print(f"  Items: {', '.join(segment.top_items[:3])}")

    return len(segments) >= 2

if __name__ == "__main__":
    success = test_segmentation()
    if success:
        print("\n✅ SegmentationAgent working correctly!")
    else:
        print("\n❌ SegmentationAgent test failed!")
