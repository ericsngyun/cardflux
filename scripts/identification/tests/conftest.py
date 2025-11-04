"""
Pytest Configuration and Shared Fixtures
Provides common test fixtures for identification tests
"""
import pytest
import sys
from pathlib import Path
import json

# Add core directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

@pytest.fixture(scope="session")
def artifacts_dir():
    """Path to artifacts directory."""
    return Path(__file__).parent.parent.parent.parent / "artifacts"

@pytest.fixture(scope="session")
def data_dir():
    """Path to data directory."""
    return Path(__file__).parent.parent.parent.parent / "data"

@pytest.fixture(scope="session")
def test_images_dir():
    """Path to test images directory."""
    test_images = Path(__file__).parent.parent.parent.parent / "test-images" / "one-piece"
    if not test_images.exists():
        pytest.skip(f"Test images directory not found: {test_images}")
    return test_images

@pytest.fixture(scope="session")
def sample_card_image(data_dir):
    """Path to a sample card image for testing."""
    images_dir = data_dir / "images" / "one-piece"
    if not images_dir.exists():
        pytest.skip("One Piece images not found")

    # Get first available image
    images = list(images_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No card images found")

    return images[0]

@pytest.fixture(scope="session")
def faiss_index_exists(artifacts_dir):
    """Check if FAISS index exists."""
    index_path = artifacts_dir / "faiss" / "one-piece-dinov2" / "index.faiss"
    if not index_path.exists():
        pytest.skip(f"FAISS index not found: {index_path}")
    return True

@pytest.fixture(scope="session")
def keypoints_cache_exists(artifacts_dir):
    """Check if keypoints cache exists."""
    keypoints_path = artifacts_dir / "keypoints" / "one-piece" / "orb_keypoints.npz"
    if not keypoints_path.exists():
        pytest.skip(f"Keypoints cache not found: {keypoints_path}")
    return True

@pytest.fixture(scope="session")
def metadata_exists(artifacts_dir):
    """Check if metadata exists."""
    metadata_path = artifacts_dir / "metadata" / "embeddings" / "one-piece-dinov2" / "metadata.jsonl"
    if not metadata_path.exists():
        pytest.skip(f"Metadata not found: {metadata_path}")
    return True

@pytest.fixture(scope="class")
def fast_identifier(faiss_index_exists, keypoints_cache_exists, metadata_exists):
    """Fast Identifier v2 instance (class-scoped for performance)."""
    from fast_card_identifier import FastCardIdentifier

    identifier = FastCardIdentifier(game="one-piece", verbose=False, use_gpu=False)
    yield identifier
    identifier.cleanup()

@pytest.fixture(scope="class")
def production_identifier(faiss_index_exists, metadata_exists):
    """Production Identifier v1 instance (class-scoped for performance)."""
    from production_card_identifier import ProductionCardIdentifier

    identifier = ProductionCardIdentifier(game="one-piece", verbose=False)
    yield identifier
    # Production identifier doesn't have cleanup method

@pytest.fixture
def ground_truth_dataset():
    """Load ground truth dataset for accuracy testing."""
    # This will be populated with actual test data
    return [
        {
            'image_path': 'test-images/one-piece/luffy.jpg',
            'expected_card_id': 288227,
            'expected_name': 'Monkey.D.Luffy',
            'expected_number': 'ST01-001',
        },
        # Add more ground truth entries as we collect them
    ]

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, requires artifacts)")
    config.addinivalue_line("markers", "performance: Performance/benchmark tests")
    config.addinivalue_line("markers", "slow: Slow tests (> 5 seconds)")
    config.addinivalue_line("markers", "fast_v2: Tests specific to Fast Identifier v2")
    config.addinivalue_line("markers", "production_v1: Tests specific to Production Identifier v1")
    config.addinivalue_line("markers", "requires_gpu: Tests that require GPU")
    config.addinivalue_line("markers", "requires_artifacts: Tests that need FAISS/embeddings/keypoints")
