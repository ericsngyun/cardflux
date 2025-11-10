#!/usr/bin/env python3
"""
Optimized Card Identification Service for Electron

Key Optimizations:
1. Model Preloading - Load DINOv2 and FAISS on startup
2. Warmup Inference - Run dummy inference to warm up GPU/CPU
3. Persistent Process - No restart overhead
4. Response Streaming - Handle large JSON payloads
5. Better Error Recovery - Graceful degradation

Performance Targets:
- Cold Start: <5s (vs 10.5s baseline)
- First Identification: <200ms (vs 986ms baseline)
- Warm Identification: <100ms (vs 92ms baseline)
"""
import sys
import json
import os
import base64
import traceback
import time
import io
from pathlib import Path
import cv2
import numpy as np
from typing import Dict, Any, Optional

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "identification"
services_dir = Path(__file__).parent.parent.parent.parent.parent / "services"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(services_dir))

from core.fast_card_identifier import FastCardIdentifier
from core.polished_card_detector import PolishedCardDetector, CardDetectionStatus

class OptimizedIdentificationService:
    """
    Optimized JSON-RPC service with model preloading and warmup.
    """

    def __init__(self):
        self.identifier = None
        self.card_detector = None
        self.initialized = False
        self.game = None

        # Performance tracking
        self.stats = {
            'total_identifications': 0,
            'total_time_ms': 0,
            'avg_time_ms': 0,
            'fastest_ms': float('inf'),
            'slowest_ms': 0,
        }

    def _log(self, message: str):
        """Log to stderr (stdout is reserved for JSON-RPC)."""
        print(f"[PY-OPT] {message}", file=sys.stderr, flush=True)

    def _respond(self, request_id: int, result=None, error=None, error_code=-32000):
        """Send JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }

        if error:
            response["error"] = {
                "code": error_code,
                "message": str(error)
            }
        else:
            response["result"] = result

        # Write response as single line
        print(json.dumps(response), flush=True)

    def initialize(self, game: str = "one-piece") -> Dict[str, Any]:
        """
        Initialize with aggressive preloading and warmup.

        Returns:
            Initialization result with timing breakdown
        """
        try:
            total_start = time.time()
            self._log(f"=== OPTIMIZED INITIALIZATION START ===")
            self._log(f"Game: {game}")

            self.game = game
            timings = {}

            # Step 1: Load Fast Identifier (DINOv2 + FAISS)
            self._log("Step 1/3: Loading Fast Identifier v2...")
            step1_start = time.time()

            self.identifier = FastCardIdentifier(
                game=game,
                verbose=False,
                use_gpu=False  # CPU for consistency
            )

            timings['load_identifier_ms'] = int((time.time() - step1_start) * 1000)
            self._log(f"  ✓ Identifier loaded in {timings['load_identifier_ms']}ms")

            # Step 2: Load Card Detector
            self._log("Step 2/3: Loading Card Detector...")
            step2_start = time.time()

            self.card_detector = PolishedCardDetector(verbose=False)

            timings['load_detector_ms'] = int((time.time() - step2_start) * 1000)
            self._log(f"  ✓ Detector loaded in {timings['load_detector_ms']}ms")

            # Step 3: WARMUP - Run dummy inference to warm up model
            self._log("Step 3/3: Warming up models...")
            step3_start = time.time()

            warmup_result = self._warmup_models()

            timings['warmup_ms'] = int((time.time() - step3_start) * 1000)
            self._log(f"  ✓ Warmup complete in {timings['warmup_ms']}ms")
            self._log(f"    - Dummy inferences: {warmup_result['num_warmup_inferences']}")
            self._log(f"    - Warmup time per inference: {warmup_result['avg_warmup_time_ms']:.1f}ms")

            total_time_ms = int((time.time() - total_start) * 1000)
            timings['total_ms'] = total_time_ms

            self.initialized = True

            self._log(f"=== INITIALIZATION COMPLETE: {total_time_ms}ms ===")

            return {
                "success": True,
                "game": game,
                "version": "v2-optimized",
                "timing": timings,
                "warmup": warmup_result
            }

        except Exception as e:
            self._log(f"Initialization failed: {e}")
            self._log(traceback.format_exc())
            raise

    def _warmup_models(self) -> Dict[str, Any]:
        """
        Warm up models with dummy inferences to eliminate first-run overhead.

        This is critical for eliminating the 10x slowdown on first identification.
        """
        # Create a dummy 600x600 RGB image (typical card image size)
        dummy_image = np.random.randint(0, 255, (600, 600, 3), dtype=np.uint8)

        # Save to temp file
        temp_dir = Path(__file__).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        dummy_path = temp_dir / "warmup_dummy.jpg"
        cv2.imwrite(str(dummy_path), dummy_image)

        warmup_times = []
        num_warmup = 2  # Run 2 warmup inferences

        try:
            for i in range(num_warmup):
                start = time.time()

                # Run full identification pipeline (triggers all lazy loading)
                result = self.identifier.identify(
                    str(dummy_path),
                    top_k=10,  # Smaller K for warmup speed
                    use_geometric=True  # Must warm up geometric too
                )

                elapsed_ms = (time.time() - start) * 1000
                warmup_times.append(elapsed_ms)

                self._log(f"    Warmup {i+1}/{num_warmup}: {elapsed_ms:.1f}ms")

            # Clean up
            dummy_path.unlink()

            return {
                'num_warmup_inferences': num_warmup,
                'warmup_times_ms': warmup_times,
                'avg_warmup_time_ms': sum(warmup_times) / len(warmup_times),
                'first_warmup_ms': warmup_times[0],
                'second_warmup_ms': warmup_times[1] if len(warmup_times) > 1 else None,
            }

        except Exception as e:
            self._log(f"Warmup failed (non-fatal): {e}")
            return {
                'num_warmup_inferences': 0,
                'error': str(e)
            }

    def identify_card(
        self,
        image_path: str,
        top_k: int = 50,
        use_geometric: bool = True,
        skip_ocr: bool = True,
        skip_foil: bool = True
    ) -> Dict[str, Any]:
        """
        Identify a card with performance tracking.
        """
        if not self.initialized:
            raise RuntimeError("Service not initialized")

        start_time = time.time()

        try:
            # Run identification
            result = self.identifier.identify(
                image_path,
                top_k=top_k,
                use_geometric=use_geometric
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Update stats
            self.stats['total_identifications'] += 1
            self.stats['total_time_ms'] += elapsed_ms
            self.stats['avg_time_ms'] = self.stats['total_time_ms'] / self.stats['total_identifications']
            self.stats['fastest_ms'] = min(self.stats['fastest_ms'], elapsed_ms)
            self.stats['slowest_ms'] = max(self.stats['slowest_ms'], elapsed_ms)

            # Return simplified result for UI
            return {
                "success": True,
                "card": {
                    "name": result['best_match']['name'],
                    "productId": result['best_match']['product_id'],
                    "number": result['best_match']['number'],
                    "set": result['best_match']['set'],
                    "rarity": result['best_match'].get('rarity', 'Unknown'),
                    "imageUrl": result['best_match'].get('image_url', ''),
                    "url": result['best_match'].get('url', ''),
                    "prices": result['best_match'].get('prices', {}),
                },
                "confidence": result['confidence'],
                "scores": {
                    "final": result['best_match']['final_score'],
                    "visual": result['best_match']['visual_score'],
                    "geometric": result['best_match'].get('geometric_score', 0),
                },
                "timing": {
                    "total_ms": elapsed_ms,
                    "feature_extraction_ms": result.get('timing', {}).get('feature_extraction', 0) * 1000,
                    "visual_search_ms": result.get('timing', {}).get('visual_search', 0) * 1000,
                    "geometric_verify_ms": result.get('timing', {}).get('geometric_verify', 0) * 1000,
                },
                "topMatches": [
                    {
                        "name": m['name'],
                        "number": m['number'],
                        "score": m['final_score'],
                        "rarity": m.get('rarity', 'Unknown'),
                    }
                    for m in result.get('top_matches', [])[:5]
                ],
                "stats": self.stats,  # Include service stats for monitoring
            }

        except Exception as e:
            self._log(f"Identification error: {e}")
            self._log(traceback.format_exc())
            raise

    def detect_card(self, image_data: str) -> Dict[str, Any]:
        """
        Detect card in base64-encoded image (for camera feed).

        This is optimized for real-time camera detection.
        """
        if not self.initialized:
            raise RuntimeError("Service not initialized")

        try:
            # Decode base64 image
            img_bytes = base64.b64decode(image_data)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if image is None:
                raise ValueError("Failed to decode image")

            # Save to temp file (detector requires file path)
            temp_dir = Path(__file__).parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / "detect_temp.jpg"
            cv2.imwrite(str(temp_path), image)

            # Run detection
            result = self.card_detector.detect_and_crop(str(temp_path))

            # Clean up temp file
            temp_path.unlink()

            # Parse detection result (ensure all types are JSON-serializable)
            # Convert numpy types to native Python types
            bbox = result['bounding_box']
            if bbox is not None:
                bbox = {str(k): int(v) for k, v in bbox.items()}

            return {
                "status": str(result['status'].value),
                "confidence": float(result['confidence']),
                "qualityScore": float(result['quality_score']),
                "warnings": [str(w) for w in result['warnings']],
                "isReady": True if result['is_acceptable'] else False,
                "bbox": bbox,
            }

        except Exception as e:
            self._log(f"Detection error: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get service status and stats."""
        return {
            "initialized": self.initialized,
            "ready": self.initialized,
            "running": True,
            "game": self.game,
            "version": "v2-optimized",
            "stats": self.stats,
        }

    def handle_request(self, request: Dict[str, Any]):
        """Handle incoming JSON-RPC request."""
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        try:
            if method == 'initialize':
                result = self.initialize(**params)
            elif method == 'identify':
                result = self.identify_card(**params)
            elif method == 'detect_card':
                result = self.detect_card(**params)
            elif method == 'status':
                result = self.get_status()
            else:
                raise ValueError(f"Unknown method: {method}")

            self._respond(request_id, result=result)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self._log(f"Request error: {error_msg}")
            self._log(traceback.format_exc())
            self._respond(request_id, error=error_msg)

    def run(self):
        """Main service loop - read JSON-RPC requests from stdin."""
        self._log("Optimized Card Identification Service started")
        self._log("Waiting for requests...")

        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    self.handle_request(request)
                except json.JSONDecodeError as e:
                    self._log(f"Invalid JSON: {e}")
                except Exception as e:
                    self._log(f"Request handling error: {e}")
                    self._log(traceback.format_exc())

        except KeyboardInterrupt:
            self._log("Service terminated by user")
        except Exception as e:
            self._log(f"Fatal error: {e}")
            self._log(traceback.format_exc())
            sys.exit(1)


if __name__ == "__main__":
    service = OptimizedIdentificationService()
    service.run()
