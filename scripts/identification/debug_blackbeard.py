#!/usr/bin/env python3
"""
Debug script to find where Marshall.D.Teach appears in blackbeard.png matches.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from identify_card_production import ProductionCardIdentifier

def main():
    identifier = ProductionCardIdentifier()

    # Search for blackbeard.png with top 50
    result = identifier.identify("test-images/one-piece/blackbeard.png", top_k=50)

    print("=" * 100)
    print("SEARCHING FOR MARSHALL.D.TEACH IN TOP 50 MATCHES")
    print("=" * 100)

    print(f"\nTest Image: blackbeard.png")
    print(f"Best Match: {result['best_match']['name']} ({result['confidence']})")
    print()

    # Find all Marshall.D.Teach cards
    teach_cards = []
    for i, match in enumerate(result['matches'][:50], 1):
        if 'teach' in match['name'].lower() or 'blackbeard' in match['name'].lower():
            teach_cards.append((i, match))
            print(f"Rank {i}: {match['name']} ({match.get('number', 'N/A')})")
            print(f"  Visual: {match['visual_score']:.4f}, Geometric: {match['geometric_score']:.4f}, Final: {match['final_score']:.4f}")
            print()

    if not teach_cards:
        print("[ERROR] No Marshall.D.Teach or Blackbeard cards found in top 50!")
        print("\nLet's check what Marshall.D.Teach cards exist in database...")

        # Search metadata
        metadata_file = Path("artifacts/metadata/embeddings/one-piece-dinov2/metadata.jsonl")
        teach_in_db = []

        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    meta = json.loads(line)
                    name = meta.get('name', '')
                    if 'teach' in name.lower() or 'blackbeard' in name.lower():
                        teach_in_db.append({
                            'id': meta.get('id'),
                            'name': name,
                            'number': meta.get('number'),
                            'set': meta.get('set')
                        })

        print(f"\nFound {len(teach_in_db)} Marshall.D.Teach cards in database:")
        for card in teach_in_db:
            print(f"  - {card['name']} ({card['number']}) [{card['id']}]")
    else:
        print(f"\n[OK] Found {len(teach_cards)} Marshall.D.Teach cards in top 50")
        print(f"Best ranking: #{teach_cards[0][0]}")

if __name__ == "__main__":
    main()
