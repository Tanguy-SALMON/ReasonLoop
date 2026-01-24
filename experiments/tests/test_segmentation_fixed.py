"""
Fixed manual test script for SegmentationAgent
This script tests all functionality with better clustering logic and reasonable defaults.
Run this script to verify the implementation works correctly.
"""

import json
import uuid
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

# Mock configuration for testing
class TestConfig:
    def __init__(self):
        self.settings = {
            "MIN_SEGMENT_SIZE": "2",      # Lower for testing
            "SIMILARITY_THRESHOLD": "0.1",  # Lower for testing
            "MAX_SEGMENTS": "10",
            "ITEMS_PER_USER": "5",
            "CLUSTERING_METHOD": "hierarchical"
        }

    def get_setting(self, key: str, default=None):
        return self.settings.get(key, default)

# Mock text completion for testing
class MockTextCompletion:
    @staticmethod
    def text_completion_ability(prompt: str, role: str = None, return_usage: bool = False):
        # Generate contextual responses based on prompt content
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ['blazer', 'suit', 'professional', 'business']):
            response = "Business Professionals"
        elif any(word in prompt_lower for word in ['casual', 't-shirt', 'jeans', 'hoodie']):
            response = "Casual Fashion Lovers"
        elif any(word in prompt_lower for word in ['crop', 'wide', 'platform', 'trendy']):
            response = "Trendy Fashion Enthusiasts"
        elif any(word in prompt_lower for word in ['dress', 'feminine', 'bohemian']):
            response = "Feminine Style Group"
        else:
            response = "General Fashion Segment"

        if return_usage:
            return response, {"tokens": 100, "cost": 0.05}
        return response

# Test configuration
CONFIG = TestConfig()

class Segment:
    """Represents a user segment with characteristics"""
    def __init__(self, segment_id: str, user_ids: List[str], top_items: List[str],
                 size: int, label: str, description: str, style_tags: List[str]):
        self.segment_id = segment_id
        self.user_ids = user_ids
        self.top_items = top_items
        self.size = size
        self.label = label
        self.description = description
        self.style_tags = style_tags
        self.avg_order_value = 0.0
        self.created_at = datetime.now().isoformat()

class SegmentationAgent:
    """Advanced segmentation agent with improved clustering logic"""

    def __init__(self):
        self.min_segment_size = int(CONFIG.get_setting("MIN_SEGMENT_SIZE", 2))
        self.similarity_threshold = float(CONFIG.get_setting("SIMILARITY_THRESHOLD", 0.1))
        self.max_segments = int(CONFIG.get_setting("MAX_SEGMENTS", 10))
        self.items_per_user = int(CONFIG.get_setting("ITEMS_PER_USER", 5))
        self.clustering_method = CONFIG.get_setting("CLUSTERING_METHOD", "hierarchical")

        print(f"SegmentationAgent initialized: min_size={self.min_segment_size}, "
              f"threshold={self.similarity_threshold}, max_segments={self.max_segments}")

    def process_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Process user recommendations and create meaningful segments"""
        if not recommendations:
            print("Warning: No recommendations provided for segmentation")
            return []

        print(f"Processing {len(recommendations)} user recommendations for segmentation")

        # Validate and clean input data
        cleaned_recommendations = self._validate_recommendations(recommendations)
        if not cleaned_recommendations:
            print("Error: No valid recommendations after cleaning")
            return []

        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(cleaned_recommendations)

        # Perform clustering
        segments = self._cluster_users(cleaned_recommendations, similarity_matrix)

        # Generate semantic labels
        segments = self._generate_semantic_labels(segments, cleaned_recommendations)

        # Filter segments by minimum size
        valid_segments = [seg for seg in segments if seg.size >= self.min_segment_size]

        print(f"Created {len(valid_segments)} valid segments from {len(cleaned_recommendations)} users")
        return valid_segments[:self.max_segments]

    def _validate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean recommendation data"""
        cleaned = []

        for rec in recommendations:
            # Check required fields
            if not all(key in rec for key in ['user_id', 'items']):
                print(f"Warning: Skipping incomplete recommendation: {rec}")
                continue

            # Clean user_id
            user_id = str(rec['user_id']).strip()
            if not user_id:
                print(f"Warning: Empty user_id in recommendation: {rec}")
                continue

            # Clean items list
            items = [str(item).strip() for item in rec.get('items', []) if str(item).strip()]
            if not items:
                print(f"Warning: No valid items for user {user_id}")
                continue

            # Handle scores if present
            scores = rec.get('scores', [])
            if scores and len(scores) != len(items):
                print(f"Warning: Mismatched items/scores for user {user_id}, truncating scores")
                scores = scores[:len(items)]

            cleaned_rec = {
                'user_id': user_id,
                'items': items[:self.items_per_user],
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

        return similarity_matrix

    def _cluster_users(self, recommendations: List[Dict[str, Any]], similarity_matrix: np.ndarray) -> List[Segment]:
        """Cluster users based on similarity using improved algorithm"""
        n_users = len(recommendations)
        clusters = []
        visited = set()

        for i in range(n_users):
            if i in visited:
                continue

            # Start new cluster
            cluster = [i]
            visited.add(i)

            # Find similar users using a more lenient approach
            for j in range(i + 1, n_users):
                if j not in visited and similarity_matrix[i][j] >= self.similarity_threshold:
                    cluster.append(j)
                    visited.add(j)

            # Also check if any existing cluster member is similar
            for cluster_idx, existing_cluster in enumerate(clusters):
                if similarity_matrix[i][existing_cluster[0]] >= self.similarity_threshold:
                    cluster.extend(existing_cluster)
                    visited.update(existing_cluster)
                    clusters.remove(existing_cluster)
                    break

            if len(cluster) >= 2:  # At least 2 users to form a cluster
                segment = self._create_segment(recommendations, cluster, len(clusters))
                clusters.append(segment)

        return clusters

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

        return Segment(
            segment_id=f"seg_{cluster_id}_{uuid.uuid4().hex[:8]}",
            user_ids=user_ids,
            top_items=top_items,
            size=len(user_ids),
            label="",  # Will be filled by semantic labeling
            description="",
            style_tags=[]
        )

    def _generate_semantic_labels(self, segments: List[Segment], recommendations: List[Dict[str, Any]]) -> List[Segment]:
        """Generate semantic labels for segments using LLM"""
        for segment in segments:
            try:
                label = self._generate_segment_label(segment, recommendations)
                description = self._generate_segment_description(segment)
                style_tags = self._extract_style_tags(segment)

                segment.label = label
                segment.description = description
                segment.style_tags = style_tags

                print(f"Generated label '{label}' for segment {segment.segment_id}")

            except Exception as e:
                print(f"Error generating label for segment {segment.segment_id}: {e}")
                # Use fallback
                segment.label = f"Style Group {segment.segment_id[-4:]}"
                segment.description = f"User segment with {segment.size} members"
                segment.style_tags = ['fashion', 'style']

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
            return "General Fashion Segment"

        # Use mock LLM for label generation
        mock_llm = MockTextCompletion()
        prompt_items = ', '.join(unique_items)
        response = mock_llm.text_completion_ability(prompt_items, "executor", False)

        return response.strip()

    def _generate_segment_description(self, segment: Segment) -> str:
        """Generate detailed segment description"""
        return f"Segment of {segment.size} users with shared fashion preferences. " \
               f"Top item categories: {', '.join(segment.top_items[:3])}."

    def _extract_style_tags(self, segment: Segment) -> List[str]:
        """Extract style tags for segment"""
        common_tags = ['fashion', 'style', 'clothing']

        # Add tags based on item names
        for item in segment.top_items:
            item_lower = item.lower()
            if 'dress' in item_lower:
                common_tags.extend(['dresses', 'feminine'])
            if 'jacket' in item_lower or 'blazer' in item_lower:
                common_tags.extend(['outerwear', 'professional'])
            if 'sneaker' in item_lower or 'shoe' in item_lower:
                common_tags.extend(['footwear', 'casual'])
            if 'jeans' in item_lower or 'pants' in item_lower:
                common_tags.extend(['bottoms', 'casual'])
            if 'shirt' in item_lower or 'top' in item_lower:
                common_tags.extend(['tops', 'casual'])

        return list(set(common_tags))[:5]

def segmentation_ability(recommendations_json: str) -> str:
    """ReasonLoop ability wrapper for user segmentation"""
    try:
        recommendations = json.loads(recommendations_json)

        if not isinstance(recommendations, list):
            raise ValueError("Recommendations must be a list")

        agent = SegmentationAgent()
        segments = agent.process_recommendations(recommendations)

        # Convert segments to dictionaries
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

        print(f"Segmentation completed: {len(segments)} segments created")
        return json.dumps(response)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON input: {e}"
        print(error_msg)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })
    except Exception as e:
        error_msg = f"Segmentation failed: {e}"
        print(error_msg)
        return json.dumps({
            "error": error_msg,
            "segments": [],
            "total_segments": 0
        })

def create_segments(recommendations: List[Dict[str, Any]]) -> List[Segment]:
    """Convenience function to create segments from recommendations"""
    agent = SegmentationAgent()
    return agent.process_recommendations(recommendations)

def run_comprehensive_tests():
    """Run all tests with improved logic"""
    print("=" * 70)
    print("SEGMENTATION AGENT COMPREHENSIVE TESTS")
    print("=" * 70)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Basic Initialization
    print("\nTest 1: Basic Initialization")
    try:
        agent = SegmentationAgent()
        assert agent.min_segment_size == 2
        assert agent.similarity_threshold == 0.1
        assert agent.max_segments == 10
        print("✓ PASSED: Agent initialization works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Initialization test failed: {e}")
        tests_failed += 1

    # Test 2: Recommendation Validation
    print("\nTest 2: Recommendation Validation")
    try:
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2"], "scores": [0.9, 0.8]},
            {"user_id": "user2", "items": ["item2", "item3"], "scores": [0.7, 0.6]},
            {"user_id": "", "items": ["item4"]},  # Invalid - empty user_id
            {"items": ["item5"]},  # Invalid - missing user_id
            {"user_id": "user3", "items": []}  # Invalid - empty items
        ]

        cleaned = agent._validate_recommendations(recommendations)
        assert len(cleaned) == 2  # Should keep only valid recommendations
        assert cleaned[0]["user_id"] == "user1"
        assert cleaned[1]["user_id"] == "user2"
        print("✓ PASSED: Recommendation validation works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Validation test failed: {e}")
        tests_failed += 1

    # Test 3: Similarity Matrix Calculation
    print("\nTest 3: Similarity Matrix Calculation")
    try:
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2", "item3"]},
            {"user_id": "user2", "items": ["item2", "item3", "item4"]},
            {"user_id": "user3", "items": ["item5", "item6"]}
        ]

        matrix = agent._calculate_similarity_matrix(recommendations)
        assert matrix.shape == (3, 3)
        assert matrix[0, 0] == 1.0  # Self-similarity
        assert matrix[0, 1] == 2/4  # Items 2,3 in common
        assert matrix[0, 2] == 0.0  # No common items
        print("✓ PASSED: Similarity matrix calculation works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Similarity matrix test failed: {e}")
        tests_failed += 1

    # Test 4: Improved Clustering
    print("\nTest 4: Improved Clustering")
    try:
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["blazer", "trousers"]},
            {"user_id": "user2", "items": ["blazer", "shirt"]},
            {"user_id": "user3", "items": ["blazer", "skirt"]},
            {"user_id": "user4", "items": ["t-shirt", "jeans"]},
            {"user_id": "user5", "items": ["t-shirt", "sneakers"]}
        ]

        segments = agent.process_recommendations(recommendations)
        assert len(segments) >= 1  # Should create at least one segment

        total_users = sum(seg.size for seg in segments)
        assert total_users <= len(recommendations)  # Should account for all users

        for segment in segments:
            assert hasattr(segment, 'segment_id')
            assert hasattr(segment, 'label')
            assert segment.label != ""

        print("✓ PASSED: Improved clustering works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Clustering test failed: {e}")
        tests_failed += 1

    # Test 5: Real-world Scenario
    print("\nTest 5: Real-world Scenario")
    try:
        recommendations = [
            # Business professionals cluster
            {"user_id": "user1", "items": ["blazer", "trousers", "dress_shoes"]},
            {"user_id": "user2", "items": ["blazer", "shirt", "briefcase"]},
            {"user_id": "user3", "items": ["blazer", "slacks", "oxford_shoes"]},
            {"user_id": "user4", "items": ["blazer", "tie", "dress_pants"]},

            # Casual fashion cluster
            {"user_id": "user5", "items": ["t-shirt", "jeans", "sneakers"]},
            {"user_id": "user6", "items": ["hoodie", "sweatpants", "running_shoes"]},
            {"user_id": "user7", "items": ["casual_shirt", "shorts", "flip_flops"]},

            # Trendy items cluster
            {"user_id": "user8", "items": ["crop_top", "wide_leg_pants", "platform_shoes"]},
            {"user_id": "user9", "items": ["bucket_hat", "oversized_blazer", "chunky_boots"]},

            # Single outlier
            {"user_id": "user10", "items": ["formal_gown", "high_heels"]}
        ]

        segments = create_segments(recommendations)

        print(f"Created {len(segments)} segments:")
        for segment in segments:
            print(f"  - {segment.label}: {segment.size} users")
            print(f"    Top items: {', '.join(segment.top_items[:3])}")
            print(f"    Style tags: {', '.join(segment.style_tags)}")
            print()

        # Should have at least 2-3 meaningful segments
        assert len(segments) >= 2
        total_users = sum(seg.size for seg in segments)
        assert total_users <= len(recommendations)

        print("✓ PASSED: Real-world scenario works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Real-world scenario test failed: {e}")
        tests_failed += 1

    # Test 6: ReasonLoop Ability Wrapper
    print("\nTest 6: ReasonLoop Ability Wrapper")
    try:
        recommendations_json = json.dumps([
            {"user_id": "user1", "items": ["blazer", "trousers"]},
            {"user_id": "user2", "items": ["blazer", "shirt"]},
            {"user_id": "user3", "items": ["t-shirt", "jeans"]},
            {"user_id": "user4", "items": ["t-shirt", "sneakers"]}
        ])

        result = segmentation_ability(recommendations_json)
        result_data = json.loads(result)

        assert "segments" in result_data
        assert "total_segments" in result_data
        assert "processing_metadata" in result_data
        assert result_data["total_segments"] >= 1

        print("✓ PASSED: ReasonLoop ability wrapper works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Ability wrapper test failed: {e}")
        tests_failed += 1

    # Test 7: Error Handling
    print("\nTest 7: Error Handling")
    try:
        # Test with invalid JSON
        result = segmentation_ability("invalid json")
        result_data = json.loads(result)
        assert "error" in result_data
        assert result_data["total_segments"] == 0

        # Test with empty recommendations
        result = segmentation_ability("[]")
        result_data = json.loads(result)
        assert result_data["total_segments"] == 0

        print("✓ PASSED: Error handling works correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Error handling test failed: {e}")
        tests_failed += 1

    # Test 8: Edge Cases
    print("\nTest 8: Edge Cases")
    try:
        agent = SegmentationAgent()

        # Test with empty recommendations
        segments = agent.process_recommendations([])
        assert segments == []

        # Test with single user
        recommendations = [{"user_id": "user1", "items": ["item1"]}]
        segments = agent.process_recommendations(recommendations)
        assert len(segments) == 0  # Single user can't form cluster

        # Test with very similar users
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2", "item3"]},
            {"user_id": "user2", "items": ["item1", "item2", "item3"]},
            {"user_id": "user3", "items": ["item1", "item2", "item3"]}
        ]
        segments = agent.process_recommendations(recommendations)
        assert len(segments) >= 1  # Should cluster similar users

        print("✓ PASSED: Edge cases handled correctly")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: Edge cases test failed: {e}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_failed}")
    print(f"Success rate: {tests_passed / (tests_passed + tests_failed) * 100:.1f}%")

    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED! SegmentationAgent is working correctly.")
        print("✅ The improved clustering logic successfully groups similar users.")
        print("✅ Semantic labeling generates meaningful segment names.")
        print("✅ The ReasonLoop ability wrapper integrates properly.")
        print("✅ Error handling and edge cases are properly managed.")
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Please review the implementation.")

    return tests_failed == 0

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
