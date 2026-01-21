"""
SegmentationAgent - Clusters users by recommendation similarity using ReasonLoop integration

This module provides user segmentation capabilities for fashion email campaigns,
integrating with ReasonLoop's multi-agent architecture.
"""

import logging
import json
import uuid
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

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
    avg_order_value: float = 0.0
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class SegmentationAgent:
    """
    Advanced segmentation agent that clusters users based on recommendation similarity
    and generates semantic segment labels using LLM.
    """

    def __init__(self):
        """Initialize segmentation agent with configuration"""
        self.min_segment_size = int(get_setting("MIN_SEGMENT_SIZE", 50))
        self.similarity_threshold = float(get_setting("SIMILARITY_THRESHOLD", 0.3))
        self.max_segments = int(get_setting("MAX_SEGMENTS", 10))
        self.items_per_user = int(get_setting("ITEMS_PER_USER", 5))
        self.clustering_method = get_setting("CLUSTERING_METHOD", "hierarchical")

        logger.info(f"SegmentationAgent initialized: min_size={self.min_segment_size}, "
                   f"threshold={self.similarity_threshold}, max_segments={self.max_segments}")

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """
        Process user recommendations and create meaningful segments

        Args:
            recommendations: List of {'user_id': str, 'items': List[str], 'scores': List[float]}

        Returns:
            List[Segment]: Segmented user groups with semantic labels
        """
        if not recommendations:
            logger.warning("No recommendations provided for segmentation")
            return []

        logger.info(f"Processing {len(recommendations)} user recommendations for segmentation")

        # Validate and clean input data
        cleaned_recommendations = self._validate_recommendations(recommendations)
        if not cleaned_recommendations:
            logger.error("No valid recommendations after cleaning")
            return []

        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(cleaned_recommendations)

        # Perform clustering
        segments = self._cluster_users(cleaned_recommendations, similarity_matrix)

        # Generate semantic labels
        segments = self._generate_semantic_labels(segments, cleaned_recommendations)

        # Filter segments by minimum size
        valid_segments = [seg for seg in segments if seg.size >= self.min_segment_size]

        logger.info(f"Created {len(valid_segments)} valid segments from {len(cleaned_recommendations)} users")
        return valid_segments[:self.max_segments]

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean recommendation data"""
        cleaned = []

        for rec in recommendations:
            # Required fields
            if not all(key in rec for key in ['user_id', 'items']):
                logger.warning(f"Skipping incomplete recommendation: {rec}")
                continue

            # Clean user_id
            user_id = str(rec['user_id']).strip()
            if not user_id:
                logger.warning(f"Empty user_id in recommendation: {rec}")
                continue

            # Clean items list
            items = [str(item).strip() for item in rec.get('items', []) if str(item).strip()]
            if not items:
                logger.warning(f"No valid items for user {user_id}")
                continue

            # Clean scores if present
            scores = rec.get('scores', [])
            if scores and len(scores) != len(items):
                logger.warning(f"Mismatched items/scores for user {user_id}, truncating scores")
                scores = scores[:len(items)]

            cleaned_rec = {
                'user_id': user_id,
                'items': items[:self.items_per_user],  # Limit items per user
                'scores': scores[:self.items_per_user] if scores else []
            }
            cleaned.append(cleaned_rec)

        return cleaned

    def _calculate_similarity_matrix(self, recommendations: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate Jaccard similarity matrix between users"""
        n_users = len(recommendations)
        similarity_matrix = np.zeros((n_users, n_users))

        # Create item sets for each user
        user_item_sets = []
        for rec in recommendations:
            # Use top items based on scores if available, otherwise all items
            items = rec['items']
            if rec['scores']:
                # Sort items by scores and take top items
                scored_items = list(zip(items, rec['scores']))
                scored_items.sort(key=lambda x: x[1], reverse=True)
                top_items = [item for item, score in scored_items[:self.items_per_user]]
            else:
                top_items = items[:self.items_per_user]

            user_item_sets.append(set(top_items))

        # Calculate pairwise Jaccard similarity
        for i in range(n_users):
            for j in range(i + 1, n_users):
                set_i = user_item_sets[i]
                set_j = user_item_sets[j]

                # Calculate Jaccard similarity
                if len(set_i) == 0 and len(set_j) == 0:
                    similarity = 0.0
                else:
                    intersection = len(set_i.intersection(set_j))
                    union = len(set_i.union(set_j))
                    similarity = intersection / union if union > 0 else 0.0

                similarity_matrix[i][j] = similarity_matrix[j][i] = similarity

        logger.debug(f"Calculated similarity matrix: {n_users}x{n_users} with {np.count_nonzero(similarity_matrix)} non-zero similarities")
        return similarity_matrix

    def _cluster_users(self, recommendations: List[Dict[str, Any]], similarity_matrix: np.ndarray) -> List[Segment]:
        """Cluster users based on similarity using DBSCAN"""
        # Convert similarity to distance matrix for DBSCAN
        distance_matrix = 1 - similarity_matrix

        # Apply DBSCAN clustering
        clustering = DBSCAN(
            eps=1 - self.similarity_threshold,
            min_samples=2,
            metric='precomputed'
        )

        try:
            cluster_labels = clustering.fit_predict(distance_matrix)
        except Exception as e:
            logger.error(f"DBSCAN clustering failed: {e}")
            return []

        # Group users by cluster
        segments = []
        unique_labels = set(cluster_labels)

        for cluster_id in unique_labels:
            if cluster_id == -1:  # Noise points
                continue

            cluster_users = [i for i, label in enumerate(cluster_labels) if label == cluster_id]

            if len(cluster_users) >= self.min_segment_size:
                segment = self._create_segment(recommendations, cluster_users, cluster_id)
                segments.append(segment)

        logger.info(f"Created {len(segments)} clusters from {len(recommendations)} users")
        return segments

    def _create_segment(self, recommendations: List[Dict[str, Any]], user_indices: List[int], cluster_id: int) -> Segment:
        """Create segment from clustered users"""
        # Get user IDs
        user_ids = [recommendations[i]['user_id'] for i in user_indices]

        # Aggregate top items across segment
        all_items = []
        for i in user_indices:
            items = recommendations[i]['items'][:3]  # Top 3 items per user
            all_items.extend(items)

        # Count item frequency
        item_counts = {}
        for item in all_items:
            item_counts[item] = item_counts.get(item, 0) + 1

        # Get top items by frequency
        top_items = sorted(item_counts.keys(), key=lambda x: item_counts[x], reverse=True)[:5]

        # Calculate average order value (placeholder - would integrate with actual data)
        avg_order_value = np.random.uniform(50, 200)  # Mock data

        return Segment(
            segment_id=f"seg_{cluster_id}_{uuid.uuid4().hex[:8]}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(user_ids),
            label="",  # Will be filled by semantic labeling
            description="",
            style_tags=[],
            avg_order_value=avg_order_value
        )

    def _generate_semantic_labels(self, segments: List[Segment], recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Generate semantic labels for segments using LLM"""
        for segment in segments:
            try:
                label = self._generate_segment_label(segment, recommendations)
                description = self._generate_segment_description(segment, recommendations)
                style_tags = self._extract_style_tags(segment, recommendations)

                segment.label = label
                segment.description = description
                segment.style_tags = style_tags

                logger.debug(f"Generated label '{label}' for segment {segment.segment_id}")

            except Exception as e:
                logger.error(f"Failed to generate label for segment {segment.segment_id}: {e}")
                # Use fallback label
                segment.label = f"Segment {segment.segment_id[-8:]}"
                segment.description = f"User segment with {segment.size} members"

        return segments

    def _generate_segment_label(self, segment: Segment, recommendations: List[Dict[str, Any]]) -> str:
        """Generate marketing-friendly segment label using LLM"""
        # Collect sample items for the segment
        segment_items = []
        for user_id in segment.user_ids[:10]:  # Sample first 10 users
            user_rec = next((rec for rec in recommendations if rec['user_id'] == user_id), None)
            if user_rec:
                segment_items.extend(user_rec['items'][:2])  # Top 2 items per user

        # Remove duplicates and limit
        unique_items = list(dict.fromkeys(segment_items))[:6]

        if not unique_items:
            return f"General Fashion Segment"

        # Create LLM prompt for label generation
        prompt = f"""Analyze these fashion items and create a concise, marketing-friendly segment name.

Fashion items in this user segment:
{', '.join(unique_items)}

Generate a segment name (2-4 words) that a fashion marketer would use. Consider:
- Style aesthetics (minimalist, bohemian, preppy, etc.)
- Target demographic (young professionals, students, etc.)
- Occasion focus (workwear, casual, party, etc.)
- Price point (luxury, affordable, mid-range, etc.)

Respond with only the segment name, nothing else."""

        try:
            response = text_completion_ability(
                prompt,
                role="executor",
                return_usage=False
            )

            if isinstance(response, tuple):
                response = response[0]

            label = response.strip()

            # Validate label
            if len(label) > 50 or not label:
                raise ValueError("Invalid label generated")

            return label

        except Exception as e:
            logger.warning(f"LLM label generation failed: {e}")
            return self._generate_fallback_label(segment)

    def _generate_segment_description(self, segment: Segment, recommendations: List[Dict[str, Any]]) -> str:
        """Generate detailed segment description"""
        return f"Segment of {segment.size} users with shared fashion preferences. " \
               f"Top item categories: {', '.join(segment.top_items[:3])}. " \
               f"Average order value: ${segment.avg_order_value:.0f}."

    def _extract_style_tags(self, segment: Segment, recommendations: List[Dict[str, Any]]) -> List[str]:
        """Extract style tags for segment"""
        # This would integrate with actual product catalog data
        # For now, return mock tags based on top items
        common_tags = ['fashion', 'style', 'clothing']

        # Add tags based on item names (mock logic)
        for item in segment.top_items:
            item_lower = item.lower()
            if 'dress' in item_lower:
                common_tags.extend(['dresses', 'feminine'])
            if 'jacket' in item_lower or 'blazer' in item_lower:
                common_tags.extend(['outerwear', 'professional'])
            if 'sneaker' in item_lower or 'shoe' in item_lower:
                common_tags.extend(['footwear', 'casual'])

        return list(set(common_tags))[:5]  # Limit to 5 unique tags

    def _generate_fallback_label(self, segment: Segment) -> str:
        """Generate fallback label when LLM fails"""
        return f"Style Group {segment.segment_id[-4:]}"


# ReasonLoop Ability Wrapper
def segmentation_ability(recommendations_json: str) -> str:
    """
    ReasonLoop ability wrapper for user segmentation

    Args:
        recommendations_json: JSON string containing recommendations data

    Returns:
        JSON string with segmentation results
    """
    try:
        # Parse input
        recommendations = json.loads(recommendations_json)

        # Validate input structure
        if not isinstance(recommendations, list):
            raise ValueError("Recommendations must be a list")

        # Initialize agent and process
        agent = SegmentationAgent()
        segments = agent.process_recommendations(recommendations)

        # Convert segments to dictionaries for JSON serialization
        segments_data = []
        for segment in segments:
            segments_data.append(asdict(segment))

        # Prepare response
        response = {
            "segments": segments_data,
            "total_segments": len(segments),
            "total_users": sum(seg.size for seg in segments),
            "processing_metadata": {
                "agent_version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "configuration": {
                    "min_segment_size": agent.min_segment_size,
                    "similarity_threshold": agent.similarity_threshold,
                    "max_segments": agent.max_segments
                }
            }
        }

        logger.info(f"Segmentation completed: {len(segments)} segments created")
        return json.dumps(response)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON input: {e}"
        logger.error(error_msg)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })

    except Exception as e:
        error_msg = f"Segmentation failed: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })


# Module-level convenience function
def create_segments(recommendations: List[Dict[str, Any]]) -> List[Segment]:
    """
    Convenience function to create segments from recommendations

    Args:
        recommendations: List of recommendation dictionaries

    Returns:
        List of Segment objects
    """
    agent = SegmentationAgent()
    return agent.process_recommendations(recommendations)
