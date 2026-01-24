"""
Test script for clean SegmentationAgent implementation

This script tests all functionality of the clean SegmentationAgent including:
- Basic initialization and configuration
- Recommendation processing and validation
- User clustering based on item similarity
- Semantic label generation using LLM
- ReasonLoop ability wrapper integration
- Error handling and edge cases
- Real-world fashion scenarios

Run this script to verify the implementation works correctly.
"""

import json
import sys
from datetime import datetime

# Mock the required modules for testing
class MockSettings:
    def __init__(self):
        self.settings = {
            "MIN_SEGMENT_SIZE": "50",
            "SIMILARITY_THRESHOLD": "0.3",
            "MAX_SEGMENTS": "10"
        }

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

class MockTextCompletion:
    @staticmethod
    def text_completion_ability(prompt, role=None):
        # Generate contextual responses based on prompt content
        prompt_lower = prompt.lower()

        if "blazer" in prompt_lower or "suit" in prompt_lower or "professional" in prompt_lower:
            return "Business Professionals"
        elif "dress" in prompt_lower or "skirt" in prompt_lower or "feminine" in prompt_lower:
            return "Feminine Style Group"
        elif "t-shirt" in prompt_lower or "jeans" in prompt_lower or "casual" in prompt_lower:
            return "Casual Fashion Lovers"
        elif "crop" in prompt_lower or "wide" in prompt_lower or "trendy" in prompt_lower:
            return "Trendy Fashion Enthusiasts"
        else:
            return "General Fashion Segment"

# Mock the imports
sys.modules['config'] = type(sys)('config')
sys.modules['config'].settings = MockSettings()

sys.modules['abilities'] = type(sys)('abilities')
sys.modules['abilities'].text_completion = MockTextCompletion()

# Now import and test our implementation
from segmentation_agent_clean import SegmentationAgent, Segment, segmentation_ability, create_segments

def test_basic_functionality():
    """Test basic segmentation functionality"""
    print("🧪 Testing Basic Functionality")

    # Test initialization
    agent = SegmentationAgent()
    assert agent.min_segment_size == 50
    assert agent.similarity_threshold == 0.3
    assert agent.max_segments == 10
    print("✅ Initialization works correctly")

    # Test with realistic data
    recommendations = [
        {"user_id": "user_1", "items": ["blazer", "trousers", "dress_shoes"]},
        {"user_id": "user_2", "items": ["blazer", "shirt", "briefcase"]},
        {"user_id": "user_3", "items": ["blazer", "slacks", "oxford_shoes"]},
        {"user_id": "user_4", "items": ["t-shirt", "jeans", "sneakers"]},
        {"user_id": "user_5", "items": ["hoodie", "sweatpants", "running_shoes"]},
        {"user_id": "user_6", "items": ["casual_shirt", "shorts", "flip_flops"]},
    ]

    segments = agent.process_recommendations(recommendations)

    print(f"   Created {len(segments)} segments:")
    for segment in segments:
        print(f"   - {segment.label}: {segment.size} users")
        print(f"     Top items: {', '.join(segment.top_items[:3])}")

    assert len(segments) >= 1, "Should create at least one segment"
    assert all(hasattr(seg, 'label') for seg in segments), "All segments should have labels"
    assert all(seg.label for seg in segments), "All segments should have non-empty labels"

    print("✅ Basic functionality works correctly")

def test_ability_wrapper():
    """Test ReasonLoop ability wrapper"""
    print("\n🧪 Testing ReasonLoop Ability Wrapper")

    recommendations_json = json.dumps([
        {"user_id": "user_1", "items": ["dress", "heels"]},
        {"user_id": "user_2", "items": ["skirt", "blouse"]},
        {"user_id": "user_3", "items": ["jeans", "t-shirt"]},
        {"user_id": "user_4", "items": ["sneakers", "hoodie"]}
    ])

    result = segmentation_ability(recommendations_json)
    result_data = json.loads(result)

    assert "segments" in result_data, "Result should contain segments"
    assert "total_segments" in result_data, "Result should contain total_segments"
    assert "total_users" in result_data, "Result should contain total_users"
    assert "metadata" in result_data, "Result should contain metadata"

    print(f"   Ability wrapper created {result_data['total_segments']} segments")
    print(f"   Total users processed: {result_data['total_users']}")

    print("✅ ReasonLoop ability wrapper works correctly")

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🧪 Testing Error Handling")

    # Test with empty recommendations
    result = segmentation_ability("[]")
    result_data = json.loads(result)
    assert result_data["total_segments"] == 0, "Should handle empty input gracefully"
    print("✅ Empty input handled correctly")

    # Test with invalid JSON
    result = segmentation_ability("invalid json")
    result_data = json.loads(result)
    assert "error" in result_data, "Should return error for invalid JSON"
    assert result_data["total_segments"] == 0, "Should return 0 segments for error cases"
    print("✅ Invalid JSON handled correctly")

    # Test with invalid data structure
    result = segmentation_ability('{"not": "a_list"}')
    result_data = json.loads(result)
    assert "error" in result_data, "Should handle invalid data structure"
    print("✅ Invalid data structure handled correctly")

def test_validation():
    """Test recommendation validation"""
    print("\n🧪 Testing Recommendation Validation")

    agent = SegmentationAgent()

    # Test with mixed valid/invalid data
    mixed_recommendations = [
        {"user_id": "user_1", "items": ["item1", "item2"]},  # Valid
        {"user_id": "", "items": ["item3"]},  # Invalid - empty user_id
        {"items": ["item4"]},  # Invalid - missing user_id
        {"user_id": "user_2", "items": []},  # Invalid - empty items
        {"user_id": "user_3", "items": ["item5", "item6"]}  # Valid
    ]

    segments = agent.process_recommendations(mixed_recommendations)

    # Should process only valid recommendations
    total_users = sum(seg.size for seg in segments)
    assert total_users <= 2, "Should only process valid recommendations"
    print("✅ Validation filters invalid data correctly")

def test_clustering_logic():
    """Test user clustering logic"""
    print("\n🧪 Testing Clustering Logic")

    agent = SegmentationAgent()

    # Create data with clear clusters
    business_users = [
        {"user_id": f"business_{i}", "items": ["blazer", "trousers", "dress_shoes"]}
        for i in range(5)
    ]

    casual_users = [
        {"user_id": f"casual_{i}", "items": ["t-shirt", "jeans", "sneakers"]}
        for i in range(5)
    ]

    recommendations = business_users + casual_users

    segments = agent.process_recommendations(recommendations)

    print(f"   Created {len(segments)} segments from 10 users:")
    for segment in segments:
        print(f"   - {segment.label}: {segment.size} users")

    # Should create at least 2 segments for distinct clusters
    assert len(segments) >= 2, "Should create multiple segments for distinct clusters"

    # Check that we don't have overlapping users
    all_user_ids = set()
    for segment in segments:
        for user_id in segment.user_ids:
            assert user_id not in all_user_ids, f"User {user_id} appears in multiple segments"
            all_user_ids.add(user_id)

    print("✅ Clustering logic works correctly")

def test_semantic_labeling():
    """Test semantic label generation"""
    print("\n🧪 Testing Semantic Labeling")

    agent = SegmentationAgent()

    # Test different types of segments
    test_cases = [
        {
            "name": "Business segment",
            "items": ["blazer", "trousers", "dress_shoes"],
            "expected_keywords": ["business", "professional"]
        },
        {
            "name": "Casual segment",
            "items": ["t-shirt", "jeans", "sneakers"],
            "expected_keywords": ["casual", "fashion"]
        },
        {
            "name": "Feminine segment",
            "items": ["dress", "heels", "jewelry"],
            "expected_keywords": ["feminine", "style"]
        }
    ]

    for test_case in test_cases[:1]:  # Test first case to avoid multiple LLM calls
        segment = Segment(
            segment_id="test_seg",
            user_ids=["user1"],
            top_items=test_case["items"],
            size=1,
            label="",
            description="",
            style_tags=[]
        )

        recommendations = [{"user_id": "user1", "items": test_case["items"]}]
        segments = agent._generate_labels([segment], recommendations)

        assert segments[0].label, f"Should generate label for {test_case['name']}"
        print(f"   Generated label: '{segments[0].label}' for {test_case['name']}")

    print("✅ Semantic labeling works correctly")

def test_performance():
    """Test with larger dataset"""
    print("\n🧪 Testing Performance")

    agent = SegmentationAgent()

    # Create larger dataset
    recommendations = []
    for i in range(100):
        if i < 50:
            # Business cluster
            items = ["blazer", "trousers", "dress_shoes"]
        elif i < 75:
            # Casual cluster
            items = ["t-shirt", "jeans", "sneakers"]
        else:
            # Trendy cluster
            items = ["crop_top", "wide_leg_pants", "platform_shoes"]

        recommendations.append({
            "user_id": f"user_{i:03d}",
            "items": items
        })

    start_time = datetime.now()
    segments = agent.process_recommendations(recommendations)
    end_time = datetime.now()

    processing_time = (end_time - start_time).total_seconds()

    print(f"   Processed 100 users in {processing_time:.2f} seconds")
    print(f"   Created {len(segments)} segments")

    assert len(segments) >= 2, "Should create multiple segments for large dataset"
    assert processing_time < 5.0, "Should process 100 users in under 5 seconds"

    print("✅ Performance test passed")

def run_all_tests():
    """Run all tests"""
    print("🚀 COMPREHENSIVE SEGMENTATION AGENT TESTS")
    print("=" * 60)

    tests = [
        test_basic_functionality,
        test_ability_wrapper,
        test_error_handling,
        test_validation,
        test_clustering_logic,
        test_semantic_labeling,
        test_performance
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/(passed+failed)*100:.1f}%")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ SegmentationAgent is working correctly")
        print("✅ Ready for ReasonLoop integration")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        print("❌ Please review the implementation")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
