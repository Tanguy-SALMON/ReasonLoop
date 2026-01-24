"""
SegmentationAgent - Working Implementation for Fashion Email Campaigns

This module provides user segmentation capabilities for fashion email campaigns,
integrating with ReasonLoop's multi-agent architecture.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Segment:
    """Represents a user segment with characteristics"""
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
    """Segments users based on recommendation similarity"""

    def __init__(self, min_size: int = 50, threshold: float = 0.3):
        self.min_segment_size = min_size
        self.similarity_threshold = threshold

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create user segments from recommendations"""
        if not recommendations:
            return []

        # Clean data
        clean_data = self._validate_recommendations(recommendations)
        if not clean_data:
            return []

        # Cluster users
        segments = self._cluster_users(clean_data)

        # Generate labels
        segments = self._generate_labels(segments)

        # Filter by minimum size
        return [seg for seg in segments if seg.size >= self.min_segment_size]

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
                    'items': items[:10],  # Limit items
                    'scores': rec.get('scores', [])[:10]
                })

        return cleaned

    def _cluster_users(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Group users into segments based on item similarity"""
        segments = []
        processed_users = set()

        for i, rec in enumerate(recommendations):
            if rec['user_id'] in processed_users:
                continue

            # Find similar users
            similar_users = [rec['user_id']]
            cluster_items = set(rec['items'][:5])  # Top 5 items

            for other_rec in recommendations[i+1:]:
                if other_rec['user_id'] in processed_users:
                    continue

                other_items = set(other_rec['items'][:5])

                # Calculate Jaccard similarity
                if len(cluster_items) > 0 and len(other_items) > 0:
                    intersection = len(cluster_items & other_items)
                    union = len(cluster_items | other_items)
                    similarity = intersection / union if union > 0 else 0

                    if similarity >= self.similarity_threshold:
                        similar_users.append(other_rec['user_id'])
                        cluster_items.update(other_items)

            # Create segment if we have enough users
            if len(similar_users) >= 2:
                # Count item frequency
                item_counts = {}
                for user_rec in recommendations:
                    if user_rec['user_id'] in similar_users:
                        for item in user_rec['items'][:5]:
                            item_counts[item] = item_counts.get(item, 0) + 1

                # Get top items
                top_items = sorted(item_counts.keys(),
                              key=lambda x: item_counts[x],
                              reverse=True)[:5]

                segment = Segment(
                    segment_id=f"seg_{uuid.uuid4().hex[:8]}",
                    user_ids=similar_users,
                    top_items=top_items,
                    size=len(similar_users),
                    label="",  # Will be filled by label generation
                    description="",
                    style_tags=[]
                )
                segments.append(segment)
                processed_users.update(similar_users)

        return segments

    def _generate_labels(self, segments: List[Segment]) -> List[Segment]:
        """Generate semantic labels for segments"""
        for segment in segments:
            try:
                # Generate label based on top items
                label = self._generate_segment_label(segment.top_items)
                description = self._generate_description(segment)
                style_tags = self._extract_style_tags(segment.top_items)

                segment.label = label
                segment.description = description
                segment.style_tags = style_tags

            except Exception as e:
                # Fallback
                segment.label = f"Style Group {segment.segment_id[-4:]}"
                segment.description = f"Segment with {segment.size} users"
                segment.style_tags = ['fashion', 'style']

        return segments

    def _generate_segment_label(self, items: List[str]) -> str:
        """Generate marketing-friendly segment label"""
        items_text = ' '.join(items).lower()

        # Rule-based labeling
        if any(word in items_text for word in ['blazer', 'suit', 'professional']):
            return "Business Professionals"
        elif any(word in items_text for word in ['dress', 'skirt', 'heels']):
            return "Feminine Style Group"
        elif any(word in items_text for word in ['t-shirt', 'jeans', 'casual']):
            return "Casual Fashion Lovers"
        elif any(word in items_text for word in ['crop', 'wide', 'trendy']):
            return "Trendy Fashionistas"
        else:
            return "General Fashion Segment"

    def _generate_description(self, segment: Segment) -> str:
        """Generate segment description"""
        return f"Segment of {segment.size} users with shared fashion preferences. Top items: {', '.join(segment.top_items[:3])}"

    def _extract_style_tags(self, items: List[str]) -> List[str]:
        """Extract style tags from items"""
        tags = ['fashion', 'style']
        items_text = ' '.join(items).lower()

        if any(word in items_text for word in ['dress', 'skirt']):
            tags.extend(['feminine', 'elegant'])
        if any(word in items_text for word in ['blazer', 'suit']):
            tags.extend(['professional', 'business'])
        if any(word in items_text for word in ['t-shirt', 'jeans']):
            tags.extend(['casual', 'comfortable'])
        if any(word in items_text for word in ['sneakers', 'shoes']):
            tags.extend(['footwear', 'active'])

        return list(set(tags))[:5]  # Unique tags, max 5


def segmentation_ability(recommendations_json: str) -> str:
    """
    ReasonLoop ability wrapper for user segmentation

    Args:
        recommendations_json: JSON string with recommendations data

    Returns:
        JSON string with segmentation results
    """
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
            "total_users": sum(seg.size for seg in segments),
            "metadata": {
                "agent_version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "min_segment_size": agent.min_segment_size,
                    "similarity_threshold": agent.similarity_threshold
                }
            }
        })

    except json.JSONDecodeError:
        return json.dumps({
            "error": "Invalid JSON input",
            "segments": [],
            "total_segments": 0
        })
    except Exception as e:
        return json.dumps({
            "error": f"Segmentation failed: {str(e)}",
            "segments": [],
            "total_segments": 0
        })


def create_segments(recommendations: List[Dict[str, Any]]) -> List[Segment]:
    """Convenience function to create segments"""
    agent = SegmentationAgent()
    return agent.process_recommendations(recommendations)


# Test function
def test_segmentation():
    """Test the segmentation functionality"""
    print("Testing SegmentationAgent...")

    # Test data
    recommendations = [
        {"user_id": "user1", "items": ["blazer", "trousers", "dress_shoes"]},
        {"user_id": "user2", "items": ["blazer", "shirt", "briefcase"]},
        {"user_id": "user3", "items": ["blazer", "slacks", "oxford_shoes"]},
        {"user_id": "user4", "items": ["t-shirt", "jeans", "sneakers"]},
        {"user_id": "user5", "items": ["hoodie", "sweatpants", "running_shoes"]},
        {"user_id": "user6", "items": ["casual_shirt", "shorts", "flip_flops"]},
    ]

    # Test the ability wrapper
    result = segmentation_ability(json.dumps(recommendations))
    data = json.loads(result)

    print(f"Created {data['total_segments']} segments:")
    for segment in data['segments']:
        print(f"  - {segment['label']}: {segment['size']} users")
        print(f"    Items: {', '.join(segment['top_items'][:3])}")

    return data['total_segments'] > 0


if __name__ == "__main__":
    # Run test
    success = test_segmentation()
    if success:
        print("✅ SegmentationAgent working correctly!")
    else:
        print("❌ SegmentationAgent test failed!")
