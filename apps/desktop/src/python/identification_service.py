#!/usr/bin/env python3
"""
Card Identification Service for Electron
Runs as a background process and communicates via JSON-RPC over stdin/stdout
"""
import sys
import json
import os
from pathlib import Path

# Add scripts directory to path
# Go up from: apps/desktop/src/python -> apps/desktop/src -> apps/desktop -> apps -> root
scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "identification"
sys.path.insert(0, str(scripts_dir))

from production_card_identifier import ProductionCardIdentifier

class IdentificationService:
    """JSON-RPC service for card identification."""

    def __init__(self):
        self.identifier = None
        self.initialized = False

    def _log(self, message: str):
        """Log to stderr (stdout is reserved for JSON-RPC)."""
        print(f"[PY] {message}", file=sys.stderr, flush=True)

    def _respond(self, request_id: int, result=None, error=None):
        """Send JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }

        if error:
            response["error"] = {
                "code": -32000,
                "message": str(error)
            }
        else:
            response["result"] = result

        print(json.dumps(response), flush=True)

    def initialize(self, game: str = "one-piece"):
        """Initialize the identification system."""
        try:
            self._log(f"Initializing identifier for game: {game}")
            self.identifier = ProductionCardIdentifier(game=game, verbose=False)
            self.initialized = True
            self._log("Identifier ready")
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

    def handle_request(self, request: dict):
        """Handle a JSON-RPC request."""
        request_id = request.get("id", 0)
        method = request.get("method")
        params = request.get("params", {})

        try:
            # Route to appropriate method
            if method == "initialize":
                result = self.initialize(**params)
            elif method == "identify":
                result = self.identify_card(**params)
            elif method == "status":
                result = self.get_status()
            else:
                raise ValueError(f"Unknown method: {method}")

            self._respond(request_id, result=result)

        except Exception as e:
            self._respond(request_id, error=str(e))

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
                self._log(f"Invalid JSON: {e}")
            except Exception as e:
                self._log(f"Error handling request: {e}")

if __name__ == "__main__":
    service = IdentificationService()
    service.run()
