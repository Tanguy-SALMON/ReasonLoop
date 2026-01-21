"""
Comprehensive tests for SegmentationAgent

This module tests all functionality of the SegmentationAgent including:
- Initialization and configuration
- Recommendation processing and validation
- Similarity matrix calculation
- User clustering
- Semantic label generation
- ReasonLoop ability wrapper
- Error handling and edge cases
"""

import pytest
import json
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the modules we're testing
from abilities.segmentation_agent import SegmentationAgent, Segment, segmentation_ability, create_segments
from config.settings import update_setting


class TestSegmentationAgent:
    """Test the SegmentationAgent class"""

    def setup_method(self):
        """Set up test environment before each test"""
        # Reset any settings to defaults
        update_setting("MIN_SEGMENT_SIZE", "50")
        update_setting("SIMILARITY_THRESHOLD", "0.3")
        update_setting("MAX_SEGMENTS", "10")
        update_setting("ITEMS_PER_USER", "5")
        update_setting("CLUSTERING_METHOD", "hierarchical")

    def test_initialization(self):
        """Test agent initialization with default settings"""
        agent = SegmentationAgent()

        assert agent.min_segment_size == 50
        assert agent.similarity_threshold == 0.3
        assert agent.max_segments == 10
        assert agent.items_per_user == 5
        assert agent.clustering_method == "hierarchical"

    def test_initialization_custom_config(self):
        """Test agent initialization with custom settings"""
        # Set custom values
        update_setting("MIN_SEGMENT_SIZE", "25")
        update_setting("SIMILARITY_THRESHOLD", "0.5")
        update_setting("MAX_SEGMENTS", "5")

        agent = SegmentationAgent()

        assert agent.min_segment_size == 25
        assert agent.similarity_threshold == 0.5
        assert agent.max_segments == 5

    def test_validate_recommendations_valid(self):
        """Test validation with valid recommendations"""
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2"], "scores": [0.9, 0.8]},
            {"user_id": "user2", "items": ["item2", "item3"], "scores": [0.7, 0.6]}
        ]

        cleaned = agent._validate_recommendations(recommendations)

        assert len(cleaned) == 2
        assert cleaned[0]["user_id"] == "user1"
        assert cleaned[1]["user_id"] == "user2"
        assert cleaned[0]["items"] == ["item1", "item2"]
        assert cleaned[0]["scores"] == [0.9, 0.8]

    def test_validate_recommendations_invalid(self):
        """Test validation filters out invalid recommendations"""
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2"]},  # Valid
            {"user_id": "", "items": ["item3"]},  # Invalid - empty user_id
            {"items": ["item4"]},  # Invalid - missing user_id
            {"user_id": "user2", "items": []},  # Invalid - empty items
            {"user_id": "user3", "items": ["item5", "item6"], "scores": [0.9]}  # Valid but mismatched scores
        ]

        cleaned = agent._validate_recommendations(recommendations)

        # Should only keep the valid recommendations
        assert len(cleaned) == 1
        assert cleaned[0]["user_id"] == "user1"

    def test_validate_recommendations_scores_handling(self):
        """Test validation handles scores correctly"""
        agent = SegmentationAgent()
        recommendations = [
            {
                "user_id": "user1",
                "items": ["item1", "item2", "item3"],
                "scores": [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # More scores than items
            }
        ]

        cleaned = agent._validate_recommendations(recommendations)

        assert len(cleaned[0]["scores"]) == 3  # Should be truncated to match items
        assert len(cleaned[0]["items"]) == 3

    def test_calculate_similarity_matrix(self):
        """Test similarity matrix calculation"""
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2", "item3"]},
            {"user_id": "user2", "items": ["item2", "item3", "item4"]},
            {"user_id": "user3", "items": ["item5", "item6"]}
        ]

        matrix = agent._calculate_similarity_matrix(recommendations)

        # Should be 3x3 matrix
        assert matrix.shape == (3, 3)

        # Diagonal should be 1 (self-similarity)
        np.testing.assert_array_almost_equal(np.diag(matrix), [1.0, 1.0, 1.0])

        # Symmetric matrix
        assert np.allclose(matrix, matrix.T)

        # Similarity between user1 and user2 should be 2/4 = 0.5 (item2, item3 in common)
        assert matrix[0, 1] == 0.5

    def test_calculate_similarity_matrix_empty_sets(self):
        """Test similarity matrix with empty item sets"""
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": []},
            {"user_id": "user2", "items": []}
        ]

        matrix = agent._calculate_similarity_matrix(recommendations)

        # Should handle empty sets gracefully
        assert matrix.shape == (2, 2)
        assert matrix[0, 1] == 0.0  # No similarity for empty sets

    @patch('abilities.text_completion.text_completion_ability')
    def test_create_segment_basic(self, mock_llm):
        """Test basic segment creation"""
        agent = SegmentationAgent()
        mock_llm.return_value = "Minimalist Professionals"

        recommendations = [
            {"user_id": "user1", "items": ["blazer", "trousers"]},
            {"user_id": "user2", "items": ["blazer", "shirt"]},
            {"user_id": "user3", "items": ["blazer", "skirt"]}
        ]

        # Create a segment manually for testing
        segment = agent._create_segment(recommendations, [0, 1, 2], 0)

        assert segment.segment_id.startswith("seg_0_")
        assert len(segment.user_ids) == 3
        assert "blazer" in segment.top_items
        assert segment.size == 3
        assert segment.label == "Minimalist Professionals"

    def test_create_segment_fallback_label(self):
        """Test segment creation with LLM failure"""
        agent = SegmentationAgent()
        recommendations = [
            {"user_id": "user1", "items": ["item1"]},
            {"user_id": "user2", "items": ["item2"]}
        ]

        with patch('abilities.text_completion.text_completion_ability') as mock_llm:
            # Mock LLM failure
            mock_llm.side_effect = Exception("API Error")

            # The _create_segment method doesn't call LLM, so this test checks the fallback
            segment = agent._create_segment(recommendations, [0, 1], 0)

            assert segment.label == ""  # Will be filled by semantic labeling
            assert len(segment.user_ids) == 2

    @patch('abilities.text_completion.text_completion_ability')
    def test_generate_segment_label_success(self, mock_llm):
        """Test successful label generation"""
        agent = SegmentationAgent()
        mock_llm.return_value = "Bohemian Dreamers"

        segment = Segment(
            segment_id="seg_test",
            user_ids=["user1", "user2"],
            top_items=["flowing_dress", "boho_top"],
            size=2,
            label="",
            description="",
            style_tags=[]
        )

        recommendations = [
            {"user_id": "user1", "items": ["flowing_dress"]},
            {"user_id": "user2", items: ["boho_top"]}
        ]

        label = agent._generate_segment_label(segment, recommendations)

        assert label == "Bohemian Dreamers"
        mock_llm.assert_called_once()

    @patch('abilities.text_completion.text_completion_ability')
    def test_generate_segment_label_fallback(self, mock_llm):
        """Test fallback label generation on LLM failure"""
        agent = SegmentationAgent()
        mock_llm.side_effect = Exception("API Error")

        segment = Segment(
            segment_id="seg_test_12345678",
            user_ids=["user1"],
            top_items=["item1"],
            size=1,
            label="",
            description="",
            style_tags=[]
        )

        recommendations = [{"user_id": "user1", "items": ["item1"]}]

        label = agent._generate_segment_label(segment, recommendations)

        # Should use fallback label
        assert "Style Group" in label
        assert label.endswith("5678")  # Last 4 chars of segment_id

    def test_extract_style_tags(self):
        """Test style tag extraction"""
        agent = SegmentationAgent()

        segment = Segment(
            segment_id="seg_test",
            user_ids=["user1"],
            top_items=["midi_dress", "blazer", "sneakers"],
            size=1,
            label="",
            description="",
            style_tags=[]
        )

        recommendations = [{"user_id": "user1", "items": ["midi_dress", "blazer", "sneakers"]}]

        tags = agent._extract_style_tags(segment, recommendations)

        assert "dresses" in tags
        assert "professional" in tags
        assert "footwear" in tags
        assert "casual" in tags

    @patch('abilities.text_completion.text_completion_ability')
    def test_process_recommendations_success(self, mock_llm):
        """Test complete recommendation processing"""
        agent = SegmentationAgent()
        mock_llm.return_value = "Casual Fashion Lovers"

        recommendations = [
            {"user_id": "user1", "items": ["t-shirt", "jeans"]},
            {"user_id": "user2", "items": ["t-shirt", "sneakers"]},
            {"user_id": "user3", "items": ["hoodie", "jeans"]},
            {"user_id": "user4", "items": ["formal_shirt", "suit"]}  # This might form a separate cluster
        ]

        segments = agent.process_recommendations(recommendations)

        # Should create at least one segment
        assert len(segments) >= 1

        # Check segment properties
        for segment in segments:
            assert isinstance(segment, Segment)
            assert segment.segment_id
            assert len(segment.user_ids) > 0
            assert segment.label
            assert segment.size > 0

    def test_process_recommendations_empty(self):
        """Test processing empty recommendations"""
        agent = SegmentationAgent()

        segments = agent.process_recommendations([])

        assert segments == []

    def test_process_recommendations_invalid_data(self):
        """Test processing with invalid data"""
        agent = SegmentationAgent()

        recommendations = [
            {"invalid": "data"},  # Missing required fields
            {"user_id": "", "items": []}  # Invalid user
        ]

        segments = agent.process_recommendations(recommendations)

        # Should handle gracefully and return empty
        assert segments == []

    @patch('abilities.text_completion.text_completion_ability')
    def test_semantic_labeling_integration(self, mock_llm):
        """Test semantic labeling as part of complete workflow"""
        agent = SegmentationAgent()
        mock_llm.return_value = "Street Style Enthusiasts"

        recommendations = [
            {"user_id": "user1", "items": ["graphic_tee", "cargo_pants"]},
            {"user_id": "user2", "items": ["hoodie", "cargo_pants"]},
            {"user_id": "user3", "items": ["sneakers", "graphic_tee"]},
            {"user_id": "user4", "items": ["suit", "dress_shoes"]}  # Different cluster
        ]

        segments = agent.process_recommendations(recommendations)

        # Check that semantic labeling was applied
        for segment in segments:
            if len(segment.user_ids) >= 3:  # Should be clustered
                assert segment.label
                assert len(segment.label) > 0
                assert len(segment.description) > 0


class TestSegmentationAbility:
    """Test the ReasonLoop ability wrapper"""

    def setup_method(self):
        """Set up test environment"""
        # Set reasonable defaults
        update_setting("MIN_SEGMENT_SIZE", "2")  # Lower for testing
        update_setting("SIMILARITY_THRESHOLD", "0.1")  # Lower for testing

    @patch('abilities.segmentation_agent.SegmentationAgent')
    def test_segmentation_ability_success(self, mock_agent_class):
        """Test successful ability execution"""
        # Setup mock
        mock_agent = MagicMock()
        mock_segment = Segment(
            segment_id="seg_test",
            user_ids=["user1"],
            top_items=["item1"],
            size=1,
            label="Test Segment",
            description="Test description",
            style_tags=["test"]
        )
        mock_agent.process_recommendations.return_value = [mock_segment]
        mock_agent_class.return_value = mock_agent

        # Test input
        recommendations_json = json.dumps([
            {"user_id": "user1", "items": ["item1"]}
        ])

        # Execute ability
        result = segmentation_ability(recommendations_json)

        # Parse and validate result
        result_data = json.loads(result)

        assert "segments" in result_data
        assert "total_segments" in result_data
        assert "total_users" in result_data
        assert "processing_metadata" in result_data

        assert result_data["total_segments"] == 1
        assert result_data["total_users"] == 1
        assert len(result_data["segments"]) == 1
        assert result_data["segments"][0]["label"] == "Test Segment"

    def test_segmentation_ability_invalid_json(self):
        """Test ability with invalid JSON input"""
        result = segmentation_ability("invalid json")

        result_data = json.loads(result)

        assert "error" in result_data
        assert "segments" in result_data
        assert result_data["total_segments"] == 0
        assert "Invalid JSON" in result_data["error"]

    def test_segmentation_ability_non_list_input(self):
        """Test ability with non-list input"""
        result = segmentation_ability('{"not": "list"}')

        result_data = json.loads(result)

        assert "error" in result_data
        assert result_data["total_segments"] == 0

    @patch('abilities.segmentation_agent.SegmentationAgent')
    def test_segmentation_ability_exception(self, mock_agent_class):
        """Test ability exception handling"""
        # Setup mock to raise exception
        mock_agent = MagicMock()
        mock_agent.process_recommendations.side_effect = Exception("Processing error")
        mock_agent_class.return_value = mock_agent

        recommendations_json = json.dumps([
            {"user_id": "user1", "items": ["item1"]}
        ])

        result = segmentation_ability(recommendations_json)

        result_data = json.loads(result)

        assert "error" in result_data
        assert "Processing error" in result_data["error"]
        assert result_data["total_segments"] == 0


class TestCreateSegments:
    """Test the convenience function"""

    @patch('abilities.segmentation_agent.SegmentationAgent')
    def test_create_segments_success(self, mock_agent_class):
        """Test convenience function"""
        mock_agent = MagicMock()
        mock_segment = Segment(
            segment_id="seg_test",
            user_ids=["user1"],
            top_items=["item1"],
            size=1,
            label="Test Segment",
            description="Test description",
            style_tags=["test"]
        )
        mock_agent.process_recommendations.return_value = [mock_segment]
        mock_agent_class.return_value = mock_agent

        recommendations = [{"user_id": "user1", "items": ["item1"]}]
        segments = create_segments(recommendations)

        assert len(segments) == 1
        assert isinstance(segments[0], Segment)
        assert segments[0].label == "Test Segment"


class TestSegmentDataClass:
    """Test the Segment dataclass"""

    def test_segment_creation(self):
        """Test basic segment creation"""
        segment = Segment(
            segment_id="seg_test",
            user_ids=["user1", "user2"],
            top_items=["item1", "item2"],
            size=2,
            label="Test Segment",
            description="Test description",
            style_tags=["tag1", "tag2"]
        )

        assert segment.segment_id == "seg_test"
        assert segment.user_ids == ["user1", "user2"]
        assert segment.top_items == ["item1", "item2"]
        assert segment.size == 2
        assert segment.label == "Test Segment"
        assert segment.description == "Test description"
        assert segment.style_tags == ["tag1", "tag2"]
        assert segment.avg_order_value == 0.0
        assert segment.created_at is not None  # Should be auto-generated

    def test_segment_auto_timestamp(self):
        """Test automatic timestamp generation"""
        before_time = datetime.now()
        segment = Segment(
            segment_id="seg_test",
            user_ids=["user1"],
            top_items=["item1"],
            size=1,
            label="Test",
            description="Test",
            style_tags=[]
        )
        after_time = datetime.now()

        # Should auto-generate timestamp
        segment_time = datetime.fromisoformat(segment.created_at)

        assert before_time <= segment_time <= after_time

    def test_segment_custom_timestamp(self):
        """Test custom timestamp"""
        custom_time = "2023-01-01T00:00:00"
        segment = Segment(
            segment_id="seg_test",
            user_ids=["user1"],
            top_items=["item1"],
            size=1,
            label="Test",
            description="Test",
            style_tags=[],
            created_at=custom_time
        )

        assert segment.created_at == custom_time


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_process_recommendations_minimum_size_filter(self):
        """Test minimum segment size filtering"""
        agent = SegmentationAgent()
        # Set high minimum size
        update_setting("MIN_SEGMENT_SIZE", "100")

        recommendations = [
            {"user_id": f"user{i}", "items": [f"item{i}"]}
            for i in range(10)  # Only 10 users, but min size is 100
        ]

        segments = agent.process_recommendations(recommendations)

        # Should return empty list due to filtering
        assert segments == []

    def test_max_segments_limit(self):
        """Test maximum segments limit"""
        agent = SegmentationAgent()
        # Set low max segments
        update_setting("MAX_SEGMENTS", "2")

        # Create many small segments
        recommendations = [
            {"user_id": f"user{i}", "items": [f"item{i}"]}
            for i in range(20)
        ]

        segments = agent.process_recommendations(recommendations)

        # Should be limited to max_segments
        assert len(segments) <= 2

    @patch('abilities.text_completion.text_completion_ability')
    def test_llm_partial_failure(self, mock_llm):
        """Test handling when some LLM calls fail"""
        agent = SegmentationAgent()

        # Mock some calls to succeed, some to fail
        def side_effect(*args, **kwargs):
            if "blazer" in str(args[0]):  # First call succeeds
                return "Professional Style"
            else:  # Second call fails
                raise Exception("API Error")

        mock_llm.side_effect = side_effect

        recommendations = [
            {"user_id": "user1", "items": ["blazer", "trousers"]},
            {"user_id": "user2", "items": ["casual_shirt", "jeans"]},
            {"user_id": "user3", "items": ["dress_shirt", "suit"]}
        ]

        # Should complete with fallback labels for failed calls
        segments = agent.process_recommendations(recommendations)

        # Should have created segments with labels (some may be fallback)
        for segment in segments:
            assert segment.label  # Should have some label
            assert segment.segment_id

    def test_similarity_matrix_edge_cases(self):
        """Test similarity matrix with various edge cases"""
        agent = SegmentationAgent()

        # Test with single user
        recommendations = [{"user_id": "user1", "items": ["item1"]}]
        matrix = agent._calculate_similarity_matrix(recommendations)
        assert matrix.shape == (1, 1)
        assert matrix[0, 0] == 1.0

        # Test with identical users
        recommendations = [
            {"user_id": "user1", "items": ["item1", "item2"]},
            {"user_id": "user2", "items": ["item1", "item2"]}
        ]
        matrix = agent._calculate_similarity_matrix(recommendations)
        assert matrix[0, 1] == 1.0  # Perfect similarity

        # Test with no common items
        recommendations = [
            {"user_id": "user1", "items": ["item1"]},
            {"user_id": "user2", "items": ["item2"]}
        ]
        matrix = agent._calculate_similarity_matrix(recommendations)
        assert matrix[0, 1] == 0.0  # No similarity


# Integration test
class TestIntegration:
    """End-to-end integration tests"""

    @patch('abilities.text_completion.text_completion_ability')
    def test_full_workflow(self, mock_llm):
        """Test complete segmentation workflow"""
        mock_llm.return_value = "Fashion Forward"

        # Create realistic test data
        recommendations = []
        for i in range(20):
            if i < 10:
                # Cluster 1: Business professionals
                items = ["blazer", "trousers", "dress_shoes"]
            elif i < 15:
                # Cluster 2: Casual fashion
                items = ["t-shirt", "jeans", "sneakers"]
            else:
                # Cluster 3: Trendy items
                items = ["crop_top", "wide_leg_pants", "platform_shoes"]

            recommendations.append({
                "user_id": f"user_{i}",
                "items": items,
                "scores": [0.9, 0.8, 0.7]
            })

        # Process through complete workflow
        segments = create_segments(recommendations)

        # Validate results
        assert len(segments) >= 1

        total_users = sum(seg.size for seg in segments)
        assert total_users <= 20  # Should account for all users

        for segment in segments:
            assert segment.segment_id
            assert segment.label
            assert segment.size >= 1
            assert len(segment.user_ids) == segment.size

            # Validate data consistency
            assert all(uid in [r["user_id"] for r in recommendations] for uid in segment.user_ids)

    @patch('abilities.text_completion.text_completion_ability')
    def test_ability_wrapper_integration(self, mock_llm):
        """Test ReasonLoop ability wrapper integration"""
        mock_llm.return_value = "Test Segment"

        # Realistic input for ability wrapper
        recommendations_json = json.dumps([
            {
                "user_id": "user_001",
                "items": ["designer_dress", "heels", "clutch"],
                "scores": [0.95, 0.87, 0.82]
            },
            {
                "user_id": "user_002",
                "items": ["evening_gown", "jewelry", "heels"],
                "scores": [0.91, 0.78, 0.85]
            }
        ])

        # Execute ability
        result = segmentation_ability(recommendations_json)

        # Validate response structure
        result_data = json.loads(result)

        assert "segments" in result_data
        assert "processing_metadata" in result_data
        assert "configuration" in result_data["processing_metadata"]

        # Validate metadata
        metadata = result_data["processing_metadata"]
        assert metadata["agent_version"] == "1.0.0"
        assert "timestamp" in metadata
        assert metadata["configuration"]["min_segment_size"] == 50


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
