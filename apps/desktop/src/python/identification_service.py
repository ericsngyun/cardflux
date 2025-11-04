#!/usr/bin/env python3
"""
Card Identification Service for Electron
Runs as a background process and communicates via JSON-RPC over stdin/stdout
"""
import sys
import json
import os
import base64
import traceback
from pathlib import Path
import cv2
import numpy as np

# Add scripts directory to path
# Go up from: apps/desktop/src/python -> apps/desktop/src -> apps/desktop -> apps -> root
scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "identification"
services_dir = Path(__file__).parent.parent.parent.parent.parent / "services"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(services_dir))

from core.production_card_identifier import ProductionCardIdentifier
from core.polished_card_detector import PolishedCardDetector, CardDetectionStatus
from tools.identifier_version_manager import IdentifierVersionManager

# Capture manager import (may not exist - handle gracefully)
try:
    from tools.capture_manager import CaptureManager
except ImportError:
    CaptureManager = None
    print("[PY] Warning: CaptureManager not available (module not found)", file=sys.stderr)

class IdentificationService:
    """JSON-RPC service for card identification with version management."""

    def __init__(self):
        self.version_manager = None
        self.card_detector = None
        self.capture_manager = None
        self.initialized = False
        self.current_version = "v2"  # Default to Fast identifier (v2), 12x faster, 100% accuracy
        self.enable_fallback = False  # Fast v2 is superior to Production v1, no fallback needed
        self.auto_capture = True  # Enable capture by default

    def _log(self, message: str):
        """Log to stderr (stdout is reserved for JSON-RPC)."""
        print(f"[PY] {message}", file=sys.stderr, flush=True)

    def _respond(self, request_id: int, result=None, error=None, error_code=-32000, error_data=None):
        """
        Send JSON-RPC response.

        Args:
            request_id: Request ID to respond to
            result: Result data (if success)
            error: Error message (if error)
            error_code: JSON-RPC error code (default -32000 = server error)
            error_data: Additional error data (traceback, error type, etc.)
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }

        if error:
            error_obj = {
                "code": error_code,
                "message": str(error)
            }
            if error_data:
                error_obj["data"] = error_data
            response["error"] = error_obj
        else:
            response["result"] = result

        print(json.dumps(response), flush=True)

    def initialize(self, game: str = "one-piece", version: str = "v2", enable_fallback: bool = False, auto_capture: bool = True):
        """Initialize the identification system with version management and capture."""
        try:
            self._log(f"Initializing identifier for game: {game} (version: {version}, fallback: {enable_fallback}, auto_capture: {auto_capture})")

            # Initialize version manager
            self.version_manager = IdentifierVersionManager(
                default_version=version,
                enable_fallback=enable_fallback
            )
            self.current_version = version
            self.enable_fallback = enable_fallback
            self.auto_capture = auto_capture

            # Pre-load the default identifier
            self.version_manager.get_identifier(version)

            # Initialize polished card detector
            self._log("Initializing polished card detector...")
            self.card_detector = PolishedCardDetector(verbose=False)

            # Initialize capture manager (if available)
            if CaptureManager is not None:
                self._log("Initializing capture manager...")
                self.capture_manager = CaptureManager(game=game)
            else:
                self._log("Capture manager not available (skipping)")
                self.capture_manager = None
                self.auto_capture = False  # Disable auto-capture if manager not available

            self.initialized = True
            self._log(f"Identifier, card detector, and capture manager ready (version: {version})")
            return {
                "status": "ready",
                "game": game,
                "version": version,
                "fallback_enabled": enable_fallback,
                "auto_capture": auto_capture
            }
        except Exception as e:
            self._log(f"Initialization error: {e}")
            raise

    def identify_card(self, image_path: str, top_k: int = 20, tcg_hint: str = None,
                     use_geometric: bool = True, skip_ocr: bool = False, skip_foil: bool = False,
                     version: str = None, enable_fallback: bool = None):
        """Identify a card from an image with version management."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call 'initialize' first.")

        try:
            # Use defaults if not specified
            if version is None:
                version = self.current_version
            if enable_fallback is None:
                enable_fallback = self.enable_fallback

            self._log(f"Identifying card: {image_path} (version: {version}, k={top_k}, geometric={use_geometric}, fallback: {enable_fallback})")

            # Run identification with version manager
            result = self.version_manager.identify(
                image_path,
                version=version,
                fallback_on_low_confidence=enable_fallback,
                top_k=top_k,
                use_geometric=use_geometric,
                tcg_hint=tcg_hint
            )

            actual_version = result.get('version', version)
            fallback_used = result.get('fallback_used', False)

            log_msg = f"Identified: {result['best_match']['name']} ({result['confidence']})"
            if fallback_used:
                log_msg += f" [FALLBACK: v2→v1]"
            log_msg += f" [version: {actual_version}]"

            self._log(log_msg)

            # AUTO-CAPTURE: Save capture if enabled
            capture_info = None
            if self.auto_capture and self.capture_manager:
                try:
                    capture_info = self.capture_manager.save_capture(
                        image_path=image_path,
                        identification_result=result,
                        save_original=True,
                        save_cropped=True,
                        save_preprocessed=False  # Skip preprocessed to save space
                    )
                    self._log(f"Captured: {capture_info['capture_id']} (confidence: {result['confidence']})")
                except Exception as e:
                    self._log(f"Capture save failed (non-fatal): {e}")

            # Return simplified result for UI
            return {
                "success": True,
                "card": {
                    "name": result['best_match']['name'],
                    "productId": result['best_match']['product_id'],
                    "number": result['best_match']['number'],
                    "set": result['best_match']['set'],
                    "rarity": result['best_match']['rarity'],
                    "imageUrl": result['best_match']['imageUrl'],
                    "url": result['best_match']['url'],
                    "prices": result['best_match']['prices'],
                },
                "confidence": result['confidence'],
                "scores": result['scores'],
                "features": {
                    "foil": result['foil_detected'],
                    "foilType": result.get('foil_type'),
                    "cardNumber": result.get('card_number_extracted'),
                },
                "timing": result['timing'],
                "topMatches": [
                    {
                        "name": m['name'],
                        "score": m['final_score'],
                        "number": m['number'],
                        "rarity": m['rarity'],
                    }
                    for m in result['matches'][:5]
                ],
                "version": actual_version,
                "fallbackUsed": fallback_used,
                "capture": {
                    "captureId": capture_info['capture_id'] if capture_info else None,
                    "saved": capture_info is not None,
                    "paths": capture_info['paths'] if capture_info else None
                } if self.auto_capture else None,
            }
        except Exception as e:
            self._log(f"Identification error: {e}")
            raise

    def identify_card_multi_frame(self, image_paths: list, top_k: int = 50,
                                   use_geometric: bool = True, tcg_hint: str = None):
        """Identify a card using multiple frames with fusion (V2 feature)."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call 'initialize' first.")

        try:
            self._log(f"Multi-frame identification: {len(image_paths)} frames")

            # Multi-frame fusion is a V2 feature
            result = self.version_manager.identify_multi_frame(
                image_paths,
                version="v2",
                top_k=top_k,
                use_geometric=use_geometric,
                tcg_hint=tcg_hint
            )

            self._log(f"Multi-frame result: {result['best_match']['name']} ({result['confidence']}, {result.get('fusion_votes', 0):.1f} votes)")

            # Return simplified result
            return {
                "success": True,
                "card": {
                    "name": result['best_match']['name'],
                    "productId": result['best_match']['product_id'],
                    "number": result['best_match']['number'],
                    "set": result['best_match']['set'],
                    "rarity": result['best_match']['rarity'],
                    "imageUrl": result['best_match']['imageUrl'],
                    "url": result['best_match']['url'],
                    "prices": result['best_match']['prices'],
                },
                "confidence": result['confidence'],
                "scores": result['scores'],
                "features": {
                    "foil": result['foil_detected'],
                    "foilType": result.get('foil_type'),
                    "cardNumber": result.get('card_number_extracted'),
                },
                "timing": result['timing'],
                "topMatches": [
                    {
                        "name": m['name'],
                        "score": m['final_score'],
                        "number": m['number'],
                        "rarity": m['rarity'],
                    }
                    for m in result['matches'][:5]
                ],
                "version": "v2",
                "multiFrame": {
                    "numFrames": result['multi_frame']['num_frames'],
                    "fusionVotes": result.get('fusion_votes', 0),
                    "agreementRate": result.get('fusion_agreement_rate', 0),
                    "confidenceBoost": result.get('fusion_confidence_boost', False),
                }
            }
        except Exception as e:
            self._log(f"Multi-frame identification error: {e}")
            raise

    def get_status(self):
        """Get service status."""
        return {
            "initialized": self.initialized,
            "ready": self.initialized and self.version_manager is not None,
            "version": self.current_version if self.initialized else None,
            "fallback_enabled": self.enable_fallback if self.initialized else None,
            "auto_capture": self.auto_capture if self.initialized else None,
        }

    def get_capture_stats(self):
        """Get capture statistics."""
        if not self.capture_manager:
            raise RuntimeError("Capture manager not initialized")

        return self.capture_manager.get_statistics()

    def set_auto_capture(self, enabled: bool):
        """Enable or disable automatic capture saving."""
        self.auto_capture = enabled
        self._log(f"Auto-capture {'enabled' if enabled else 'disabled'}")
        return {"auto_capture": self.auto_capture}

    def detect_card_in_frame(self, image_data: str):
        """
        Detect card in a frame (base64 encoded image).

        Returns detection status, confidence, and whether card is ready for capture.
        """
        if not self.initialized or self.card_detector is None:
            raise RuntimeError("Service not initialized. Call 'initialize' first.")

        try:
            # Decode base64 image
            img_data = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                raise ValueError("Failed to decode image")

            # Save frame temporarily for detection
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)
                tmp_path = tmp.name

            # Detect card using detect_and_crop (returns Dict)
            result = self.card_detector.detect_and_crop(tmp_path)

            # Clean up temp file
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass

            # The result dict contains enum objects that aren't JSON serializable
            # Convert enum to string value
            status_value = result['status']
            if hasattr(status_value, 'value'):
                status_value = status_value.value

            # Serialize the result for JSON-RPC response
            serialized_result = {
                "status": status_value,
                "confidence": float(result.get('confidence', 0)),
                "qualityScore": float(result.get('quality_score', 0)),
                "warnings": result.get('warnings', []),
                "isReady": status_value in ('perfect', 'good'),
                "bbox": result.get('bounding_box') if result.get('bounding_box') else None,
            }

            return serialized_result
        except Exception as e:
            self._log(f"Card detection error: {e}")
            raise

    def _encode_image_base64(self, image: np.ndarray) -> str:
        """Encode image as base64 JPEG."""
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')

    def handle_request(self, request: dict):
        """Handle a JSON-RPC request."""
        request_id = request.get("id", 0)
        method = request.get("method")
        params = request.get("params", {})

        # Validate JSON-RPC version
        if request.get("jsonrpc") != "2.0":
            self._respond(
                request_id,
                error="Invalid JSON-RPC version",
                error_code=-32600,  # Invalid Request
                error_data={"expected": "2.0", "got": request.get("jsonrpc")}
            )
            return

        try:
            # Route to appropriate method
            if method == "initialize":
                result = self.initialize(**params)
            elif method == "identify":
                result = self.identify_card(**params)
            elif method == "identify_multi_frame":
                result = self.identify_card_multi_frame(**params)
            elif method == "detect_card":
                result = self.detect_card_in_frame(**params)
            elif method == "status":
                result = self.get_status()
            elif method == "get_metrics":
                # Get version manager metrics
                if self.version_manager:
                    result = self.version_manager.get_metrics()
                else:
                    result = {}
            elif method == "get_capture_stats":
                result = self.get_capture_stats()
            elif method == "set_auto_capture":
                result = self.set_auto_capture(**params)
            else:
                raise ValueError(f"Unknown method: {method}")

            self._respond(request_id, result=result)

        except TypeError as e:
            # Invalid parameters
            tb = traceback.format_exc()
            self._log(f"Invalid parameters for {method}: {e}\n{tb}")
            self._respond(
                request_id,
                error=f"Invalid parameters for method '{method}': {e}",
                error_code=-32602,  # Invalid params
                error_data={"type": "TypeError", "traceback": tb}
            )
        except ValueError as e:
            # Application-level validation error
            tb = traceback.format_exc()
            self._log(f"Validation error in {method}: {e}\n{tb}")
            self._respond(
                request_id,
                error=str(e),
                error_code=-32001,  # Application error
                error_data={"type": "ValueError", "traceback": tb}
            )
        except FileNotFoundError as e:
            # File/resource not found
            tb = traceback.format_exc()
            self._log(f"File not found in {method}: {e}\n{tb}")
            self._respond(
                request_id,
                error=f"File not found: {e}",
                error_code=-32002,  # File not found
                error_data={"type": "FileNotFoundError", "traceback": tb}
            )
        except RuntimeError as e:
            # Runtime/state error (e.g., service not initialized)
            tb = traceback.format_exc()
            self._log(f"Runtime error in {method}: {e}\n{tb}")
            self._respond(
                request_id,
                error=str(e),
                error_code=-32003,  # Runtime error
                error_data={"type": "RuntimeError", "traceback": tb}
            )
        except Exception as e:
            # Generic error - preserve stack trace
            tb = traceback.format_exc()
            self._log(f"Unexpected error in {method}: {e}\n{tb}")
            self._respond(
                request_id,
                error=f"{type(e).__name__}: {e}",
                error_code=-32000,  # Server error
                error_data={"type": type(e).__name__, "traceback": tb}
            )

    def run(self):
        """Main service loop - read requests from stdin."""
        self._log("Card Identification Service started")
        self._log("Waiting for requests...")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                self.handle_request(request)
            except json.JSONDecodeError as e:
                # JSON parse error - send error response with request ID if available
                self._log(f"Invalid JSON: {e}\nInput: {line[:100]}...")
                try:
                    # Try to extract request ID from malformed JSON
                    # Look for "id": <number> pattern
                    import re
                    match = re.search(r'"id"\s*:\s*(\d+)', line)
                    request_id = int(match.group(1)) if match else 0
                except:
                    request_id = 0

                self._respond(
                    request_id,
                    error="Invalid JSON",
                    error_code=-32700,  # Parse error
                    error_data={"type": "JSONDecodeError", "message": str(e)}
                )
            except Exception as e:
                # Unexpected error in main loop - try to respond with error
                tb = traceback.format_exc()
                self._log(f"Fatal error in main loop: {e}\n{tb}")

                # Try to extract request ID if we have a request object
                try:
                    request_id = request.get("id", 0) if 'request' in locals() else 0
                except:
                    request_id = 0

                self._respond(
                    request_id,
                    error=f"Fatal service error: {e}",
                    error_code=-32000,  # Server error
                    error_data={"type": type(e).__name__, "traceback": tb}
                )

if __name__ == "__main__":
    service = IdentificationService()
    service.run()
