"""
SegmentationAgent - Clean implementation for ReasonLoop integration

This module provides user segmentation capabilities for fashion email campaigns,
integrating seamlessly with ReasonLoop's multi-agent architecture.
"""

import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import uuid

from config.settings import get_setting
from abilities.text_completion import text_completion_ability

logger = logging.getLogger(__name__)

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
    """Segments users based on recommendation similarity and generates semantic labels"""

    def __init__(self):
        self.min_segment_size = int(get_setting("MIN_SEGMENT_SIZE", 50))
        self.similarity_threshold = float(get_setting("SIMILARITY_THRESHOLD", 0.3))
        self.max_segments = int(get_setting("MAX_SEGMENTS", 10))

        logger.info(f"SegmentationAgent initialized: min_size={self.min_segment_size}, "
                   f"threshold={self.similarity_threshold}, max_segments={self.max_segments}")

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create user segments from recommendation data"""
        if not recommendations:
            logger.warning("No recommendations provided for segmentation")
            return []

        logger.info(f"Processing {len(recommendations)} user recommendations")

        # Clean and validate data
        cleaned_recs = self._validate_recommendations(recommendations)
        if not cleaned_recs:
            logger.error("No valid recommendations after cleaning")
            return []

        # Group users by similarity
        segments = self._cluster_users(cleaned_recs)

        # Generate semantic labels
        segments = self._generate_labels(segments, cleaned_recs)

        # Filter by minimum size
        valid_segments = [seg for seg in segments if seg.size >= self.min_segment_size]

        logger.info(f"Created {len(valid_segments)} segments from {len(cleaned_recs)} users")
        return valid_segments[:self.max_segments]

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
                    'items': items[:10],  # Limit items per user
                    'scores': rec.get('scores', [])[:10]
                })

        return cleaned

    def _cluster_users(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Group users into segments based on item similarity"""
        segments = []

        # Simple clustering: group users with common items
        processed_users = set()

        for i, rec in enumerate(recommendations):
            if rec['user_id'] in processed_users:
                continue

            # Find similar users
            similar_users = [rec['user_id']]
            cluster_items = set(rec['items'])

            # Look for users with similar items
            for other_rec in recommendations[i+1:]:
                if (other_rec['user_id'] not in processed_users and
                    other_rec['user_id'] not in similar_users):

                    other_items = set(other_rec['items'])

                    # Calculate Jaccard similarity
                    if len(cluster_items) > 0 and len(other_items) > 0:
                        intersection = len(cluster_items & other_items)
                        union = len(cluster_items | other_items)
                        similarity = intersection / union if union > 0 else 0

                        if similarity >= self.similarity_threshold:
                            similar_users.append(other_rec['user_id'])
                            cluster_items.update(other_rec['items'])

            # Create segment if we have enough users
            if len(similar_users) >= 2:
                # Get top items for this cluster
                item_counts = {}
                for user_rec in recommendations:
                    if user_rec['user_id'] in similar_users:
                        for item in user_rec['items']:
                            item_counts[item] = item_counts.get(item, 0) + 1

                top_items = sorted(item_counts.keys(),
                              key=lambda x: item_counts[x], reverse=True)[:5]

                segment = Segment(
                    segment_id=f"seg_{uuid.uuid4().hex[:8]}",
                    user_ids=similar_users,
                    top_items=top_items,
                    size=len(similar_users),
                    label="",
                    description="",
                    style_tags=[]
                )
                segments.append(segment)

                # Mark users as processed
                processed_users.update(similar_users)

        return segments

    def _generate_labels(self, segments: List[Segment], recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Generate semantic labels for segments using LLM"""
        for segment in segments:
            try:
                # Prepare items for LLM
                top_items = segment.top_items[:6]
                items_text = ", ".join(top_items)

                # Generate label using ReasonLoop's text completion
                prompt = f"""Generate a concise, marketing-friendly segment name for these fashion items:

{items_text}

Consider style, occasion, and target demographic. Return only the segment name (2-4 words)."""

                response = text_completion_ability(prompt, role="executor")
                if isinstance(response, tuple):
                    response = response[0]

                label = response.strip()

                # Create description
                description = f"Segment of {segment.size} users with preferences for: {', '.join(top_items[:3])}"

                # Extract style tags
                style_tags = self._extract_style_tags(top_items)

                segment.label = label[:50]  # Limit length
                segment.description = description
                segment.style_tags = style_tags

                logger.debug(f"Generated label '{label}' for segment {segment.segment_id}")

            except Exception as e:
                logger.error(f"Failed to generate label for segment {segment.segment_id}: {e}")
                # Fallback label
                segment.label = f"Style Group {segment.segment_id[-4:]}"
                segment.description = f"User segment with {segment.size} members"
                segment.style_tags = ['fashion', 'style']

        return segments

    def _extract_style_tags(self, items: List[str]) -> List[str]:
        """Extract style tags from item names"""
        tags = ['fashion', 'style']

        items_text = " ".join(items).lower()

        # Simple rule-based tagging
        if any(word in items_text for word in ['dress', 'skirt', 'heels']):
            tags.extend(['feminine', 'elegant'])
        if any(word in items_text for word in ['blazer', 'suit', 'shirt']):
            tags.extend(['professional', 'business'])
        if any(word in items_text for word in ['t-shirt', 'jeans', 'sneakers']):
            tags.extend(['casual', 'comfortable'])
        if any(word in items_text for word in ['crop', 'wide', 'platform']):
            tags.extend(['trendy', 'fashion-forward'])

        return list(set(tags))[:5]  # Limit unique tags

# ReasonLoop Ability Wrapper
def segmentation_ability(recommendations_json: str) -> str:
    """
    ReasonLoop ability for user segmentation

    Args:
        recommendations_json: JSON string with recommendations data

    Returns:
        JSON string with segmentation results
    """
    try:
        recommendations = json.loads(recommendations_json)

        if not isinstance(recommendations, list):
            raise ValueError("Recommendations must be a list")

        # Process recommendations
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

        response = {
            "segments": segments_data,
            "total_segments": len(segments),
            "total_users": sum(seg.size for seg in segments),
            "metadata": {
                "agent_version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "min_segment_size": agent.min_segment_size,
                    "similarity_threshold": agent.similarity_threshold,
                    "max_segments": agent.max_segments
                }
            }
        }

        logger.info(f"Segmentation completed: {len(segments)} segments")
        return json.dumps(response)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON: {e}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })
    except Exception as e:
        error_msg = f"Segmentation failed: {e}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })

# Convenience function
def create_segments(recommendations: List[Dict[str, Any]]) -> List[Segment]:
    """Create segments from recommendation data"""
    agent = SegmentationAgent()
    return agent.process_recommendations(recommendations)
