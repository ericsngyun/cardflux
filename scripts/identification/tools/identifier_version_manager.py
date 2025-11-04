#!/usr/bin/env python3
"""
Identifier Version Manager

Manages multiple versions of card identification systems with fallback support.
Allows A/B testing and safe rollback if new version underperforms.

Usage:
    from identifier_version_manager import IdentifierVersionManager

    manager = IdentifierVersionManager()
    result = manager.identify(image_path, version='v2', fallback_on_low_confidence=True)

Author: Senior Principal Engineer
Date: 2025-10-21
"""
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict

def _log(message: str):
    """Log to stderr to avoid interfering with JSON-RPC on stdout."""
    print(f"[VersionManager] {message}", file=sys.stderr, flush=True)


class IdentifierVersion(Enum):
    """Available identifier versions."""
    V1_BASELINE = "v1"  # Current production version
    V2_ENHANCED = "v2"  # New enhanced version with multi-frame fusion


@dataclass
class IdentificationMetrics:
    """Performance metrics for comparison."""
    version: str
    accuracy: float  # Correct identifications / total
    avg_time_ms: float
    high_confidence_rate: float  # % of HIGH confidence results
    success_rate: float  # % of successful identifications
    fallback_rate: float = 0.0  # % of times fallback was used


class IdentifierVersionManager:
    """
    Manages multiple identifier versions with automatic fallback.

    Features:
    - Version selection (v1 baseline, v2 enhanced)
    - Automatic fallback if confidence too low
    - Performance tracking for A/B testing
    - Safe rollback mechanism
    """

    def __init__(self, default_version: str = "v2", enable_fallback: bool = False):
        """
        Initialize version manager.

        Args:
            default_version: Default version to use ("v1" or "v2")
            enable_fallback: Enable automatic fallback to v1 if v2 has low confidence
                            (DEFAULT: False - v2 Fast identifier is superior, no fallback needed)
        """
        self.default_version = default_version
        self.enable_fallback = enable_fallback

        # Lazy-load identifiers (only load when needed)
        self._v1_identifier = None
        self._v2_identifier = None

        # Metrics tracking
        self.metrics = {
            'v1': {'calls': 0, 'total_time': 0, 'high_conf': 0, 'fallbacks': 0},
            'v2': {'calls': 0, 'total_time': 0, 'high_conf': 0, 'fallbacks': 0}
        }

        # Fallback thresholds (rarely used - v2 is superior)
        self.FALLBACK_THRESHOLD = 0.65  # If v2 score < 0.65, try v1
        self.CONFIDENCE_THRESHOLD = "MODERATE"  # Minimum acceptable confidence

        _log(f"Initialized (default: {default_version}, fallback: {enable_fallback})")

    def get_identifier(self, version: str = None):
        """
        Get identifier instance for specified version.

        Args:
            version: "v1" or "v2" (defaults to default_version)

        Returns:
            Identifier instance
        """
        if version is None:
            version = self.default_version

        if version == "v1":
            if self._v1_identifier is None:
                _log("Loading v1 (baseline) identifier...")
                from core.production_card_identifier import ProductionCardIdentifier
                self._v1_identifier = ProductionCardIdentifier(
                    game='one-piece',
                    verbose=False,
                    enable_variant_classifier=True
                )
            return self._v1_identifier

        elif version == "v2":
            if self._v2_identifier is None:
                _log("Loading v2 (fast) identifier...")
                # V2 is now the FAST identifier (92% faster, 100% accuracy)
                # Benchmark: 111ms avg (vs 1377ms production), 100% accuracy (vs 83%)
                try:
                    from core.fast_card_identifier import FastCardIdentifier
                    self._v2_identifier = FastCardIdentifier(
                        game='one-piece',
                        verbose=False,
                        use_gpu=True  # Auto-detects GPU, falls back to CPU
                    )
                    _log("✓ Fast identifier loaded (12x speedup, 100% accuracy)")
                except ImportError as e:
                    _log(f"Warning: Fast identifier not available ({e}), falling back to production")
                    from core.production_card_identifier import ProductionCardIdentifier
                    self._v2_identifier = ProductionCardIdentifier(
                        game='one-piece',
                        verbose=False,
                        enable_variant_classifier=True
                    )
                except Exception as e:
                    _log(f"Error loading fast identifier ({e}), falling back to production")
                    from core.production_card_identifier import ProductionCardIdentifier
                    self._v2_identifier = ProductionCardIdentifier(
                        game='one-piece',
                        verbose=False,
                        enable_variant_classifier=True
                    )
            return self._v2_identifier

        else:
            raise ValueError(f"Unknown version: {version}. Use 'v1' or 'v2'")

    def identify(
        self,
        image_path: str,
        version: str = None,
        fallback_on_low_confidence: bool = None,
        **kwargs
    ) -> Dict:
        """
        Identify card using specified version with optional fallback.

        Args:
            image_path: Path to card image
            version: Version to use ("v1" or "v2", defaults to default_version)
            fallback_on_low_confidence: Override fallback setting
            **kwargs: Additional arguments for identifier

        Returns:
            Identification result with version metadata
        """
        if version is None:
            version = self.default_version

        if fallback_on_low_confidence is None:
            fallback_on_low_confidence = self.enable_fallback

        # Try primary version
        start_time = time.time()
        identifier = self.get_identifier(version)
        result = identifier.identify(image_path, **kwargs)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Track metrics
        self.metrics[version]['calls'] += 1
        self.metrics[version]['total_time'] += elapsed_ms
        if result['confidence'] == 'HIGH':
            self.metrics[version]['high_conf'] += 1

        # Add version metadata
        result['version'] = version
        result['fallback_used'] = False

        # Check if fallback needed
        should_fallback = (
            fallback_on_low_confidence and
            version == "v2" and
            (result['best_match']['final_score'] < self.FALLBACK_THRESHOLD or
             result['confidence'] == 'LOW')
        )

        if should_fallback:
            _log(f"V2 low confidence ({result['confidence']}, score: {result['best_match']['final_score']:.3f}), trying V1 fallback...")

            # Try v1 fallback
            fallback_start = time.time()
            v1_identifier = self.get_identifier("v1")
            v1_result = v1_identifier.identify(image_path, **kwargs)
            fallback_elapsed = int((time.time() - fallback_start) * 1000)

            # Track fallback metrics
            self.metrics['v1']['calls'] += 1
            self.metrics['v1']['total_time'] += fallback_elapsed
            self.metrics['v2']['fallbacks'] += 1

            if v1_result['confidence'] == 'HIGH':
                self.metrics['v1']['high_conf'] += 1

            # Use v1 result if better
            if self._is_better_result(v1_result, result):
                _log(f"V1 fallback better ({v1_result['confidence']}, score: {v1_result['best_match']['final_score']:.3f}), using V1 result")
                v1_result['version'] = 'v1'
                v1_result['fallback_used'] = True
                v1_result['original_version'] = 'v2'
                v1_result['fallback_reason'] = f"V2 low confidence ({result['confidence']})"
                return v1_result
            else:
                _log("V2 result still better, keeping V2")

        return result

    def identify_multi_frame(
        self,
        image_paths: List[str],
        version: str = None,
        **kwargs
    ) -> Dict:
        """
        Identify card using multiple frames (v2 only feature).

        Args:
            image_paths: List of image paths (3-5 frames)
            version: Version to use (must be "v2")
            **kwargs: Additional arguments

        Returns:
            Fused identification result
        """
        if version is None:
            version = self.default_version

        if version != "v2":
            _log("Multi-frame fusion only available in v2, using v2")
            version = "v2"

        identifier = self.get_identifier(version)

        # V2 has multi-frame fusion capability
        if hasattr(identifier, 'identify_multi_frame'):
            start_time = time.time()
            result = identifier.identify_multi_frame(image_paths, **kwargs)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Track metrics
            self.metrics[version]['calls'] += 1
            self.metrics[version]['total_time'] += elapsed_ms
            if result['confidence'] == 'HIGH':
                self.metrics[version]['high_conf'] += 1

            result['version'] = version
            result['fallback_used'] = False
            return result
        else:
            # Fallback: just use first frame
            _log("Multi-frame not supported, using first frame")
            return self.identify(image_paths[0], version=version, **kwargs)

    def _is_better_result(self, result_a: Dict, result_b: Dict) -> bool:
        """
        Compare two results and determine if A is better than B.

        Priority:
        1. Confidence level (HIGH > MODERATE > LOW)
        2. Final score
        3. Margin (distance to 2nd place)
        """
        conf_order = {'HIGH': 3, 'MODERATE': 2, 'LOW': 1}

        conf_a = conf_order.get(result_a['confidence'], 0)
        conf_b = conf_order.get(result_b['confidence'], 0)

        if conf_a != conf_b:
            return conf_a > conf_b

        # Same confidence, compare scores
        score_a = result_a['best_match']['final_score']
        score_b = result_b['best_match']['final_score']

        return score_a > score_b

    def get_metrics(self) -> Dict:
        """
        Get performance metrics for all versions.

        Returns:
            Dictionary with metrics for each version
        """
        summary = {}

        for version in ['v1', 'v2']:
            metrics = self.metrics[version]
            calls = metrics['calls']

            if calls > 0:
                summary[version] = {
                    'calls': calls,
                    'avg_time_ms': metrics['total_time'] / calls,
                    'high_confidence_rate': metrics['high_conf'] / calls,
                    'fallback_rate': metrics.get('fallbacks', 0) / calls if version == 'v2' else 0.0
                }
            else:
                summary[version] = {
                    'calls': 0,
                    'avg_time_ms': 0,
                    'high_confidence_rate': 0,
                    'fallback_rate': 0
                }

        return summary

    def print_metrics(self):
        """Print performance metrics summary."""
        metrics = self.get_metrics()

        print("\n" + "="*70)
        print("IDENTIFIER VERSION PERFORMANCE METRICS")
        print("="*70)

        for version in ['v1', 'v2']:
            m = metrics[version]
            print(f"\n{version.upper()} {'(Baseline)' if version == 'v1' else '(Enhanced)'}:")
            print(f"  Total Calls:        {m['calls']}")
            print(f"  Avg Time:           {m['avg_time_ms']:.0f}ms")
            print(f"  HIGH Confidence:    {m['high_confidence_rate']*100:.1f}%")
            if version == 'v2':
                print(f"  Fallback Rate:      {m['fallback_rate']*100:.1f}%")

        print("\n" + "="*70)

    def save_metrics(self, filepath: str):
        """Save metrics to JSON file."""
        metrics = self.get_metrics()
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        _log(f"Metrics saved to {filepath}")

    def reset_metrics(self):
        """Reset all metrics."""
        for version in ['v1', 'v2']:
            self.metrics[version] = {
                'calls': 0,
                'total_time': 0,
                'high_conf': 0,
                'fallbacks': 0
            }
        _log("Metrics reset")


# Convenience function for easy imports
def create_identifier(version: str = "v2", enable_fallback: bool = False):
    """
    Create identifier with version management.

    Args:
        version: "v1" or "v2" (default: "v2" = Fast identifier)
        enable_fallback: Enable automatic fallback (default: False - Fast v2 is superior)

    Returns:
        IdentifierVersionManager instance
    """
    return IdentifierVersionManager(default_version=version, enable_fallback=enable_fallback)
