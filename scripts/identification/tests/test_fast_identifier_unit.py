"""
Unit Tests for Fast Identifier v2
Tests individual components and functions in isolation
"""
import pytest
import sys
import json
from pathlib import Path
import numpy as np

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))


class TestFastIdentifierInitialization:
    """Test Fast Identifier initialization and configuration."""

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_init_default_settings(self, fast_identifier):
        """Test initialization with default settings."""
        assert fast_identifier is not None
        assert fast_identifier.game == "one-piece"
        assert fast_identifier.model is not None
        assert fast_identifier.processor is not None
        assert fast_identifier.index is not None

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_keypoints_cache_loaded(self, fast_identifier):
        """Test that pre-computed keypoints cache is loaded."""
        assert fast_identifier.precomputed_keypoints is not None
        # Should have keypoints data
        assert len(fast_identifier.precomputed_keypoints) > 0

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_metadata_loaded(self, fast_identifier):
        """Test that metadata is properly loaded."""
        assert fast_identifier.metadata is not None
        assert len(fast_identifier.metadata) > 0
        # Should have metadata for ~5000 cards
        assert len(fast_identifier.metadata) > 4000


class TestFastIdentifierIdentification:
    """Test Fast Identifier identification functionality."""

    @pytest.mark.integration
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    @pytest.mark.timeout(30)
    def test_identify_single_card(self, fast_identifier, sample_card_image):
        """Test identification of a single card."""
        result = fast_identifier.identify(str(sample_card_image), top_k=20)

        # Check result structure
        assert 'best_match' in result
        assert 'confidence' in result
        assert 'matches' in result
        assert 'scores' in result
        assert 'timing' in result

        # Check best match structure
        best = result['best_match']
        assert 'card_id' in best
        assert 'name' in best
        assert 'number' in best
        assert 'final_score' in best

        # Check scores
        scores = result['scores']
        assert 'visual' in scores
        assert 'geometric' in scores
        assert 'final' in scores

        # Check timing
        timing = result['timing']
        assert 'total_ms' in timing
        assert 'feature_extraction_ms' in timing
        assert 'visual_search_ms' in timing
        assert 'geometric_verify_ms' in timing

        # Validate confidence levels
        assert result['confidence'] in ['HIGH', 'MODERATE', 'LOW']

    @pytest.mark.integration
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    @pytest.mark.performance
    def test_identification_speed(self, fast_identifier, sample_card_image):
        """Test that identification meets speed requirements (<500ms target)."""
        result = fast_identifier.identify(str(sample_card_image), top_k=20)

        total_time = result['timing']['total_ms']

        # Fast v2 should be under 500ms on average
        # Allow up to 1000ms for slower machines
        assert total_time < 1000, f"Identification took {total_time:.0f}ms (target: <1000ms)"

        # Log performance for monitoring
        print(f"\n  Performance: {total_time:.0f}ms")
        print(f"    Feature extraction: {result['timing']['feature_extraction_ms']:.0f}ms")
        print(f"    Visual search: {result['timing']['visual_search_ms']:.1f}ms")
        print(f"    Geometric verify: {result['timing']['geometric_verify_ms']:.0f}ms")

    @pytest.mark.integration
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_identify_returns_valid_scores(self, fast_identifier, sample_card_image):
        """Test that all scores are within valid ranges."""
        result = fast_identifier.identify(str(sample_card_image), top_k=20)

        # Visual scores should be in [0, 1] range
        assert 0 <= result['scores']['visual'] <= 1

        # Geometric scores should be in [0, 1] range or 0
        assert 0 <= result['scores']['geometric'] <= 1

        # Final scores should be in [0, 1] range
        assert 0 <= result['scores']['final'] <= 1

        # All matches should have valid scores
        for match in result['matches']:
            assert 0 <= match['visual_score'] <= 1
            assert 0 <= match['geometric_score'] <= 1
            assert 0 <= match['final_score'] <= 1

    @pytest.mark.integration
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_top_k_parameter(self, fast_identifier, sample_card_image):
        """Test that top_k parameter works correctly."""
        result_10 = fast_identifier.identify(str(sample_card_image), top_k=10)
        result_20 = fast_identifier.identify(str(sample_card_image), top_k=20)

        # Should return at most top_k matches
        assert len(result_10['matches']) <= 10
        assert len(result_20['matches']) <= 20

        # Best match should be the same regardless of top_k
        assert result_10['best_match']['card_id'] == result_20['best_match']['card_id']

    @pytest.mark.integration
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_geometric_verification_optional(self, fast_identifier, sample_card_image):
        """Test identification with geometric verification disabled."""
        result = fast_identifier.identify(str(sample_card_image), use_geometric=False)

        # Should still return valid result
        assert 'best_match' in result
        assert 'confidence' in result

        # Geometric score should be 0
        assert result['scores']['geometric'] == 0

        # Geometric time should be minimal
        assert result['timing']['geometric_verify_ms'] < 10


class TestFastIdentifierJSON:
    """Test JSON serialization and output format."""

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_json_serializable(self, fast_identifier, sample_card_image):
        """Test that result is JSON serializable."""
        result = fast_identifier.identify(str(sample_card_image), top_k=5)

        # Should be able to serialize to JSON without errors
        try:
            json_str = json.dumps(result, indent=2)
            assert len(json_str) > 0

            # Should be able to deserialize back
            parsed = json.loads(json_str)
            assert parsed['best_match']['card_id'] == result['best_match']['card_id']
        except TypeError as e:
            pytest.fail(f"Result is not JSON serializable: {e}")

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_foil_type_serialization(self, fast_identifier, sample_card_image):
        """Test that foil_type enum is properly serialized to string."""
        result = fast_identifier.identify(str(sample_card_image))

        # foil_type should be None or a string, not an enum
        foil_type = result.get('foil_type')
        assert foil_type is None or isinstance(foil_type, str), \
            f"foil_type should be None or str, got {type(foil_type)}"

        # If foil detected, foil_type should be a valid string
        if result.get('foil_detected'):
            assert isinstance(foil_type, str)
            valid_types = ['none', 'standard_foil', 'rainbow', 'etched', 'reverse_holo',
                         'pattern_foil', 'texture', 'unknown_foil']
            assert foil_type in valid_types


class TestFastIdentifierCleanup:
    """Test resource cleanup and memory management."""

    @pytest.mark.unit
    @pytest.mark.fast_v2
    def test_cleanup(self):
        """Test that cleanup properly releases resources."""
        from fast_card_identifier import FastCardIdentifier

        identifier = FastCardIdentifier(game="one-piece", verbose=False)
        assert identifier.executor is not None

        identifier.cleanup()

        # Executor should be shutdown
        # Note: We can't easily test this without internal access


class TestFastIdentifierErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_invalid_image_path(self, fast_identifier):
        """Test handling of invalid image paths."""
        with pytest.raises(Exception):
            fast_identifier.identify("nonexistent_image.jpg")

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_empty_image_path(self, fast_identifier):
        """Test handling of empty image paths."""
        with pytest.raises(Exception):
            fast_identifier.identify("")

    @pytest.mark.unit
    @pytest.mark.fast_v2
    @pytest.mark.requires_artifacts
    def test_invalid_top_k(self, fast_identifier, sample_card_image):
        """Test handling of invalid top_k values."""
        # top_k should be positive
        with pytest.raises(Exception):
            fast_identifier.identify(str(sample_card_image), top_k=0)

        with pytest.raises(Exception):
            fast_identifier.identify(str(sample_card_image), top_k=-1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
