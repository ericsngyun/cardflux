#!/usr/bin/env python3
"""
Build a reprint mapping for cards with the same name but different product IDs.
This allows the identification system to show all reprints/alternate versions.
"""
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "metadata"
GAME = "one-piece-dinov2"

def build_reprint_map():
    """Build a mapping of card names to all their product IDs (reprints)"""

    metadata_file = ARTIFACTS_DIR / "embeddings" / GAME / "metadata.jsonl"

    if not metadata_file.exists():
        print(f"ERROR: Metadata file not found at {metadata_file}")
        return

    # Group cards by normalized name
    name_to_products: Dict[str, List[dict]] = defaultdict(list)

    print(f"Loading metadata from {metadata_file}...")
    with open(metadata_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                card = json.loads(line)

                # Normalize the name (remove parenthetical info for grouping)
                raw_name = card.get("name", "")

                # Remove variant indicators but keep the core name
                # Example: "Luffy (Parallel)" -> "Luffy"
                # Example: "Zoro - OP01-001 (Alternate Art)" -> "Zoro"
                normalized_name = raw_name

                # Remove common variant suffixes
                for suffix in [" (Parallel)", " (Alternate Art)", " (Championship", " (Promo)",
                              " (Super Pre-Release)", " (Pre-Release)", " (Winner)", " (Finalist)"]:
                    if suffix in normalized_name:
                        normalized_name = normalized_name.split(suffix)[0]

                # Remove card numbers like "- OP01-001"
                if " - " in normalized_name and "OP" in normalized_name:
                    parts = normalized_name.split(" - ")
                    if len(parts) > 1 and any(c.isdigit() for c in parts[-1]):
                        normalized_name = " - ".join(parts[:-1])

                normalized_name = normalized_name.strip()

                name_to_products[normalized_name].append({
                    "productId": card.get("productId"),
                    "id": card.get("id"),
                    "name": card.get("name"),
                    "set": card.get("set"),
                    "rarity": card.get("rarity"),
                    "imageUrl": card.get("imageUrl"),
                })

    # Filter to only names with multiple printings
    reprints = {
        name: products
        for name, products in name_to_products.items()
        if len(products) > 1
    }

    # Build ID-to-reprints mapping (for fast lookup during identification)
    id_to_reprints = {}
    for name, products in reprints.items():
        product_ids = [str(p["productId"] or p["id"]) for p in products]
        for product in products:
            card_id = str(product["productId"] or product["id"])
            # Store all OTHER versions (excluding itself)
            id_to_reprints[card_id] = {
                "baseName": name,
                "variants": [
                    p for p in products
                    if str(p["productId"] or p["id"]) != card_id
                ]
            }

    # Save the reprint map
    output_file = ARTIFACTS_DIR / "embeddings" / GAME / "reprints.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(id_to_reprints, f, indent=2)

    # Print statistics
    total_cards = sum(len(products) for products in name_to_products.values())
    cards_with_reprints = sum(len(products) for products in reprints.values())
    unique_names_with_reprints = len(reprints)

    print(f"\n=== Reprint Map Built ===")
    print(f"Total cards: {total_cards}")
    print(f"Cards with reprints: {cards_with_reprints}")
    print(f"Unique names with multiple versions: {unique_names_with_reprints}")
    print(f"\nSaved to: {output_file}")

    # Show some examples
    print(f"\n=== Sample Reprints ===")
    for name, products in list(reprints.items())[:5]:
        print(f"\n'{name}' has {len(products)} versions:")
        for p in products[:3]:  # Show first 3
            print(f"  - {p['name']} ({p['set']}) [ID: {p['productId'] or p['id']}]")

if __name__ == "__main__":
    build_reprint_map()
