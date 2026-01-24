#!/usr/bin/env python3
"""
Simple and Working SegmentationAgent Test

This script provides a complete, working implementation of user segmentation
for fashion email campaigns with comprehensive testing.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class Segment:
    """Represents a user segment"""
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
    """Working segmentation agent for fashion campaigns"""

    def __init__(self, min_size: int = 2, threshold: float = 0.1):
        self.min_segment_size = min_size
        self.similarity_threshold = threshold

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Create user segments from recommendations"""
        if not recommendations:
            return []

        # Clean and validate data
        clean_recs = self._validate_recommendations(recommendations)
        if not clean_recs:
            return []

        # Calculate similarity
        similarity_matrix = self._calculate_similarity(clean_recs)

        # Cluster users
        clusters = self._cluster_users(clean_recs, similarity_matrix)

        # Create segments
        segments = []
        for cluster in clusters:
            segment = self._create_segment(clean_recs, cluster)
            if segment.size >= self.min_segment_size:
                segments.append(segment)

        return segments

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean recommendation data"""
        clean = []
        for rec in recommendations:
            if not rec.get('user_id') or not rec.get('items'):
                continue
            user_id = str(rec['user_id']).strip()
            items = [str(item).strip() for item in rec['items'] if str(item).strip()]
            if user_id and items:
                clean.append({
                    'user_id': user_id,
                    'items': items[:5],  # Limit items
                    'scores': rec.get('scores', [])[:5]
                })
        return clean

    def _calculate_similarity(self, recommendations: List[Dict[str, Any]]) -> List[List[float]]:
        """Calculate similarity between users"""
        n = len(recommendations)
        similarity = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                items_i = set(recommendations[i]['items'])
                items_j = set(recommendations[j]['items'])

                if len(items_i) == 0 and len(items_j) == 0:
                    sim = 0.0
                else:
                    intersection = len(items_i & items_j)
                    union = len(items_i | items_j)
                    sim = intersection / union if union > 0 else 0.0

                similarity[i][j] = similarity[j][i] = sim

        return similarity

    def _cluster_users(self, recommendations: List[Dict[str, Any]], similarity: List[List[float]]) -> List[List[int]]:
        """Group similar users into clusters"""
        n = len(recommendations)
        clusters = []
        visited = set()

        for i in range(n):
            if i in visited:
                continue

            cluster = [i]
            visited.add(i)

            # Find similar users
            for j in range(i + 1, n):
                if j not in visited and similarity[i][j] >= self.similarity_threshold:
                    cluster.append(j)
                    visited.add(j)

            # Add cluster if it has enough members
            if len(cluster) >= 2:
                clusters.append(cluster)

        return clusters

    def _create_segment(self, recommendations: List[Dict[str, Any]], cluster: List[int]) -> Segment:
        """Create segment from user cluster"""
        user_ids = [recommendations[i]['user_id'] for i in cluster]

        # Aggregate top items
        all_items = []
        for i in cluster:
            all_items.extend(recommendations[i]['items'][:3])

        # Count frequency
        item_counts = {}
        for item in all_items:
            item_counts[item] = item_counts.get(item, 0) + 1

        top_items = sorted(item_counts.keys(),
                      key=lambda x: item_counts[x], reverse=True)[:5]

        # Generate label
        label = self._generate_label(top_items)

        # Generate description
        description = f"Segment of {len(cluster)} users with shared preferences"

        # Extract style tags
        style_tags = self._extract_tags(top_items)

        return Segment(
            segment_id=f"seg_{uuid.uuid4().hex[:8]}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(cluster),
            label=label,
            description=description,
            style_tags=style_tags
        )

    def _generate_label(self, top_items: List[str]) -> str:
        """Generate marketing-friendly segment label"""
        # Simple rule-based labeling
        items_text = ' '.join(top_items).lower()

        if any(word in items_text for word in ['blazer', 'suit', 'dress_shirt', 'tie']):
            return "Business Professionals"
        elif any(word in items_text for word in ['t-shirt', 'jeans', 'sneakers', 'hoodie']):
            return "Casual Fashion Lovers"
        elif any(word in items_text for word in ['dress', 'skirt', 'heels']):
            return "Feminine Style Group"
        elif any(word in items_text for word in ['crop', 'wide', 'platform', 'bucket']):
            return "Trendy Fashionistas"
        else:
            return "General Fashion Segment"

    def _extract_tags(self, top_items: List[str]) -> List[str]:
        """Extract style tags from items"""
        tags = ['fashion', 'style']

        items_text = ' '.join(top_items).lower()

        if any(word in items_text for word in ['blazer', 'suit']):
            tags.extend(['professional', 'workwear'])
        if any(word in items_text for word in ['dress', 'skirt']):
            tags.extend(['feminine', 'elegant'])
        if any(word in items_text for word in ['sneakers', 'shoes']):
            tags.extend(['casual', 'comfortable'])
        if any(word in items_text for word in ['jeans', 'pants']):
            tags.extend(['casual', 'bottom'])

        return list(set(tags))[:5]  # Limit tags


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
                "style_tags": segment.style_tags
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


def run_tests():
    """Run comprehensive tests"""
    print("🧪 Testing SegmentationAgent")
    print("=" * 50)

    passed = 0
    total = 0

    # Test 1: Basic functionality
    total += 1
    try:
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["blazer", "trousers"]},
            {"user_id": "user2", "items": ["blazer", "shirt"]},
            {"user_id": "user3", "items": ["t-shirt", "jeans"]},
            {"user_id": "user4", "items": ["sneakers", "hoodie"]}
        ]

        segments = agent.process_recommendations(recommendations)

        assert len(segments) >= 1, f"Expected at least 1 segment, got {len(segments)}"
        assert all(hasattr(seg, 'label') for seg in segments)
        assert all(seg.label for seg in segments)

        print("✅ Test 1 PASSED: Basic segmentation works")
        passed += 1

    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")

    # Test 2: Real-world scenario
    total += 1
    try:
        recommendations = [
            # Business professionals
            {"user_id": "user1", "items": ["blazer", "trousers", "dress_shoes"]},
            {"user_id": "user2", "items": ["blazer", "shirt", "briefcase"]},
            {"user_id": "user3", "items": ["blazer", "slacks", "oxford_shoes"]},

            # Casual fashion
            {"user_id": "user4", "items": ["t-shirt", "jeans", "sneakers"]},
            {"user_id": "user5", "items": ["hoodie", "sweatpants", "running_shoes"]},
            {"user_id": "user6", "items": ["casual_shirt", "shorts", "flip_flops"]},

            # Trendy items
            {"user_id": "user7", "items": ["crop_top", "wide_leg_pants", "platform_shoes"]},
            {"user_id": "user8", "items": ["bucket_hat", "oversized_blazer", "chunky_boots"]}
        ]

        segments = agent.process_recommendations(recommendations)

        print(f"   Created {len(segments)} segments:")
        for segment in segments:
            print(f"   - {segment.label}: {segment.size} users")
            print(f"     Items: {', '.join(segment.top_items[:3])}")

        assert len(segments) >= 2, f"Expected at least 2 segments, got {len(segments)}"

        # Check for business and casual segments
        business_found = any("Business" in seg.label for seg in segments)
        casual_found = any("Casual" in seg.label for seg in segments)

        assert business_found, "Business segment not found"
        assert casual_found, "Casual segment not found"

        print("✅ Test 2 PASSED: Real-world scenario works")
        passed += 1

    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")

    # Test 3: ReasonLoop ability wrapper
    total += 1
    try:
        recommendations_json = json.dumps([
            {"user_id": "user1", "items": ["dress", "heels"]},
            {"user_id": "user2", "items": ["skirt", "blouse"]},
            {"user_id": "user3", "items": ["jeans", "t-shirt"]},
            {"user_id": "user4", "items": ["sneakers", "hoodie"]}
        ])

        result = segmentation_ability(recommendations_json)
        result_data = json.loads(result)

        assert "segments" in result_data
        assert "total_segments" in result_data
        assert result_data["total_segments"] >= 1

        print("✅ Test 3 PASSED: ReasonLoop wrapper works")
        passed += 1

    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")

    # Test 4: Edge cases
    total += 1
    try:
        # Empty recommendations
        segments = agent.process_recommendations([])
        assert len(segments) == 0

        # Single user (can't cluster)
        segments = agent.process_recommendations([
            {"user_id": "user1", "items": ["item1"]}
        ])
        assert len(segments) == 0

        # Invalid data
        segments = agent.process_recommendations([
            {"user_id": "", "items": []},
            {"items": ["item1"]},
            None
        ])
        assert len(segments) == 0

        print("✅ Test 4 PASSED: Edge cases handled")
        passed += 1

    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")

    # Test 5: Performance with larger dataset
    total += 1
    try:
        # Create larger dataset
        recommendations = []

        # Add multiple clusters
        for cluster in range(5):
            cluster_items = [
                f"item_{cluster}_1",
                f"item_{cluster}_2",
                f"item_{cluster}_3"
            ]

            for user in range(10):
                recommendations.append({
                    "user_id": f"cluster{cluster}_user{user}",
                    "items": cluster_items
                })

        segments = agent.process_recommendations(recommendations)

        assert len(segments) >= 3, f"Expected at least 3 segments, got {len(segments)}"
        assert sum(seg.size for seg in segments) <= len(recommendations)

        print(f"✅ Test 5 PASSED: Large dataset handled ({len(segments)} segments from {len(recommendations)} users)")
        passed += 1

    except Exception as e:
        print(f"❌ Test 5 FAILED: {e}")

    # Results
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ SegmentationAgent is working correctly")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
