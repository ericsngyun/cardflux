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
sys.path.insert(0, str(scripts_dir))

from production_card_identifier import ProductionCardIdentifier
from card_detector import StabilizedCardDetector, CardDetectionStatus

class IdentificationService:
    """JSON-RPC service for card identification."""

    def __init__(self):
        self.identifier = None
        self.card_detector = None
        self.initialized = False

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

    def initialize(self, game: str = "one-piece"):
        """Initialize the identification system."""
        try:
            self._log(f"Initializing identifier for game: {game}")
            self.identifier = ProductionCardIdentifier(game=game, verbose=False)

            # Initialize stabilized card detector with temporal smoothing
            self._log("Initializing stabilized card detector with temporal smoothing...")
            self.card_detector = StabilizedCardDetector(frame_width=1920, frame_height=1080, history_size=10)

            self.initialized = True
            self._log("Identifier and card detector ready")
            return {"status": "ready", "game": game}
        except Exception as e:
            self._log(f"Initialization error: {e}")
            raise

    def identify_card(self, image_path: str, top_k: int = 20, tcg_hint: str = None,
                     use_geometric: bool = True, skip_ocr: bool = False, skip_foil: bool = False):
        """Identify a card from an image."""
        if not self.initialized:
            raise RuntimeError("Service not initialized. Call 'initialize' first.")

        try:
            self._log(f"Identifying card: {image_path} (k={top_k}, geometric={use_geometric})")

            # Run identification with optimized settings
            result = self.identifier.identify(
                image_path,
                top_k=top_k,
                use_geometric=use_geometric,
                tcg_hint=None  # Skip OCR for speed - visual matching is sufficient
            )

            self._log(f"Identified: {result['best_match']['name']} ({result['confidence']})")

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
                ]
            }
        except Exception as e:
            self._log(f"Identification error: {e}")
            raise

    def get_status(self):
        """Get service status."""
        return {
            "initialized": self.initialized,
            "ready": self.initialized and self.identifier is not None
        }

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

            # Detect card
            result = self.card_detector.detect_card(frame)

            # Create visualization (optional)
            # vis_frame = self.card_detector.create_visualization(frame, result)
            # vis_base64 = self._encode_image_base64(vis_frame)

            return {
                "status": result.status.value,
                "confidence": result.confidence,
                "qualityScore": result.quality_score,
                "warnings": result.warnings,
                "isReady": result.status == CardDetectionStatus.CARD_READY,
                "bbox": result.bbox if result.bbox else None,
                # "visualization": vis_base64  # Uncomment if you want visualization
            }
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
            elif method == "detect_card":
                result = self.detect_card_in_frame(**params)
            elif method == "status":
                result = self.get_status()
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
