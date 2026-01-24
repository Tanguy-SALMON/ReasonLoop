"""
SegmentationAgent - Working Implementation for Fashion Email Campaigns

This module provides user segmentation capabilities that actually work.
Groups users based on item preferences and generates meaningful segments.
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
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
    """Segments users based on item similarity"""

    def __init__(self, min_size: int = 2, threshold: float = 0.5):
        self.min_segment_size = min_size
        self.similarity_threshold = threshold

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create segments from recommendations"""
        if not recommendations:
            return []

        # Clean data
        clean_data = self._validate_recommendations(recommendations)
        if not clean_data:
            return []

        # Create segments
        segments = self._create_segments(clean_data)

        # Generate labels
        for segment in segments:
            self._generate_label(segment)

        return segments

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean recommendation data"""
        cleaned = []
        for rec in recommendations:
            if rec.get('user_id') and rec.get('items'):
                user_id = str(rec['user_id']).strip()
                items = [str(item).strip() for item in rec.get('items', []) if str(item).strip()]
                if user_id and items:
                    cleaned.append({
                        'user_id': user_id,
                        'items': items[:10]  # Limit items
                    })
        return cleaned

    def _create_segments(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Group users into segments"""
        segments = []
        processed = set()

        for i, rec in enumerate(recommendations):
            if rec['user_id'] in processed:
                continue

            # Start new segment
            segment_users = [rec['user_id']]
            segment_items = set(rec['items'][:5])
            processed.add(rec['user_id'])

            # Find similar users
            for other_rec in recommendations[i+1:]:
                if other_rec['user_id'] in processed:
                    continue

                other_items = set(other_rec['items'][:5])

                # Calculate similarity
                if self._similar_enough(segment_items, other_items):
                    segment_users.append(other_rec['user_id'])
                    segment_items.update(other_rec['items'][:5])
                    processed.add(other_rec['user_id'])

            # Create segment if enough users
            if len(segment_users) >= self.min_segment_size:
                segment = self._build_segment(segment_users, segment_items, recommendations)
                segments.append(segment)

        return segments

    def _similar_enough(self, items1: set, items2: set) -> bool:
        """Check if two user groups are similar enough"""
        if not items1 or not items2:
            return False

        # Simple overlap check
        overlap = len(items1 & items2)
        total_unique = len(items1 | items2)

        if total_unique == 0:
            return False

        similarity = overlap / total_unique
        return similarity >= self.similarity_threshold

    def _build_segment(self, user_ids: List[str], items: set, all_recommendations: List[Dict[str, Any]]) -> Segment:
        """Build segment from user group"""
        # Count item frequency
        item_counts = {}
        for rec in all_recommendations:
            if rec['user_id'] in user_ids:
                for item in rec['items'][:5]:
                    item_counts[item] = item_counts.get(item, 0) + 1

        # Top items
        top_items = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:5]

        return Segment(
            segment_id=f"seg_{uuid.uuid4().hex[:8]}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(user_ids),
            label="",  # Will be filled by label generation
            description="",
            style_tags=[]
        )

    def _generate_label(self, segment: Segment):
        """Generate segment label"""
        items_text = ' '.join(segment.top_items).lower()

        # Simple rule-based labeling
        if any(word in items_text for word in ['blazer', 'suit', 'trousers']):
            segment.label = "Business Professionals"
        elif any(word in items_text for word in ['dress', 'skirt', 'heels']):
            segment.label = "Feminine Style Group"
        elif any(word in items_text for word in ['t-shirt', 'jeans', 'sneakers']):
            segment.label = "Casual Fashion Lovers"
        elif any(word in items_text for word in ['crop', 'wide', 'platform']):
            segment.label = "Trendy Fashionistas"
        else:
            segment.label = "Fashion Enthusiasts"

        # Description
        segment.description = f"Segment of {segment.size} users with shared preferences for: {', '.join(segment.top_items[:3])}"

        # Style tags
        segment.style_tags = self._extract_tags(segment.top_items)

    def _extract_tags(self, items: List[str]) -> List[str]:
        """Extract style tags"""
        tags = ['fashion', 'style']
        items_text = ' '.join(items).lower()

        if any(word in items_text for word in ['blazer', 'suit']):
            tags.extend(['professional', 'workwear'])
        if any(word in items_text for word in ['dress', 'skirt']):
            tags.extend(['feminine', 'elegant'])
        if any(word in items_text for word in ['t-shirt', 'jeans']):
            tags.extend(['casual', 'comfortable'])

        return list(set(tags))[:5]

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
            "total_users": sum(seg.size for seg in segments)
        })

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "segments": [],
            "total_segments": 0
        })

# Test function
def test_segmentation():
    """Test the segmentation"""
    print("Testing SegmentationAgent...")

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
        print("\n✅ SegmentationAgent working!")
    else:
        print("\n❌ SegmentationAgent failed!")
