#!/usr/bin/env python3
"""
Simple Working SegmentationAgent for Fashion Email Campaigns
This implementation creates user segments based on recommendation similarity.
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
    """Simple but effective segmentation agent"""

    def __init__(self, min_size: int = 2, threshold: float = 0.3):
        self.min_cluster_size = min_size
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
        segments = self._cluster_users(clean_data)

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
                        'items': items[:10]
                    })
        return cleaned

    def _cluster_users(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Group users into segments"""
        segments = []
        processed = set()

        for i, rec in enumerate(recommendations):
            if rec['user_id'] in processed:
                continue

            # Start new cluster
            cluster = [rec['user_id']]
            cluster_items = set(rec['items'][:5])
            processed.add(rec['user_id'])

            # Find similar users
            for other_rec in recommendations[i+1:]:
                if other_rec['user_id'] in processed:
                    continue

                other_items = set(other_rec['items'][:5])

                # Calculate similarity
                similarity = self._jaccard_similarity(cluster_items, other_items)

                if similarity >= self.similarity_threshold:
                    cluster.append(other_rec['user_id'])
                    cluster_items.update(other_rec['items'][:5])
                    processed.add(other_rec['user_id'])

            # Create segment if enough users
            if len(cluster) >= self.min_cluster_size:
                segment = self._create_segment(cluster, recommendations)
                segments.append(segment)

        return segments

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 and not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _create_segment(self, user_ids: List[str], recommendations: List[Dict[str, Any]]) -> Segment:
        """Create segment from user cluster"""
        # Count item frequency
        item_counts = {}
        for rec in recommendations:
            if rec['user_id'] in user_ids:
                for item in rec['items'][:5]:
                    item_counts[item] = item_counts.get(item, 0) + 1

        # Top items
        top_items = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:5]

        # Generate label
        label = self._generate_label_from_items(top_items)

        # Description
        description = f"Segment of {len(user_ids)} users with preferences for {', '.join(top_items[:3])}"

        # Style tags
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

    def _generate_label_from_items(self, items: List[str]) -> str:
        """Generate label from top items"""
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

    def _generate_label(self, segment: Segment):
        """Generate label for segment (placeholder for LLM integration)"""
        # For now use simple rule-based labeling
        segment.label = self._generate_label_from_items(segment.top_items)
        segment.description = f"Segment of {segment.size} users with preferences for {', '.join(segment.top_items[:3])}"
        segment.style_tags = self._extract_tags(segment.top_items)


def segmentation_ability(recommendations_json: str) -> str:
    """ReasonLoop ability wrapper"""
    try:
        recommendations = json.loads(recommendations_json)
        if not isinstance(recommendations, list):
            raise ValueError("Recommendations must be a list")

        agent = SegmentationAgent()
        segments = agent.process_recommendations(recommendations)

        # Convert to response format
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
    result = segmentation_ability(json.dumps(recommendations))
    data = json.loads(result)

    print(f"Created {data['total_segments']} segments:")
    for segment in data['segments']:
        print(f"- {segment['label']}: {segment['size']} users")
        print(f"  Items: {', '.join(segment['top_items'][:3])}")

    return data['total_segments'] >= 2


if __name__ == "__main__":
    success = test_segmentation()
    if success:
        print("\n✅ SegmentationAgent working correctly!")
    else:
        print("\n❌ Test failed!")
