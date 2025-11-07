#!/usr/bin/env python3
"""
Historical Price Backfill using py7zr (Python 7z library)

Downloads and processes historical price data from tcgcsv.com archives.
Uses py7zr for cross-platform 7z extraction without external dependencies.

Usage:
    # Test with one week
    python backfill_prices_py7zr.py --start 2024-02-08 --end 2024-02-14

    # Full backfill (Feb 2024 → yesterday)
    python backfill_prices_py7zr.py

    # Resume from specific date
    python backfill_prices_py7zr.py --start 2024-06-01
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request
import py7zr
from typing import Dict, List, Optional, Set
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Directories
TEMP_DIR = PROJECT_ROOT / ".temp" / "price-archives"
PRICES_DIR = PROJECT_ROOT / "data" / "prices" / "historical"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
STATE_DIR = PROJECT_ROOT / "data" / "state"

# Archive configuration
ARCHIVE_BASE_URL = "https://tcgcsv.com/archive/tcgplayer"
ARCHIVE_START_DATE = datetime(2024, 2, 8)  # Feb 8, 2024

# One Piece Card Game
CATEGORY_ID = 68  # TCGPlayer category ID for One Piece


def ensure_dirs():
    """Create required directories."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_curated_cards(game: str) -> List[Dict]:
    """Load curated cards to get product IDs and group IDs."""
    curated_file = CURATED_DIR / f"{game}.jsonl"

    if not curated_file.exists():
        print(f"[ERROR] Curated data not found: {curated_file}")
        print("   Run: git lfs pull")
        sys.exit(1)

    cards = []
    with open(curated_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cards.append(json.loads(line))

    print(f"[OK] Loaded {len(cards)} cards from {curated_file.name}")
    return cards


def get_unique_group_ids(cards: List[Dict]) -> Set[int]:
    """Extract unique group IDs from cards."""
    group_ids = set()
    for card in cards:
        if 'groupId' in card:
            group_ids.add(int(card['groupId']))
    return group_ids


def download_archive(date_str: str) -> Optional[Path]:
    """Download archive for a specific date."""
    filename = f"prices-{date_str}.ppmd.7z"
    url = f"{ARCHIVE_BASE_URL}/{filename}"
    local_path = TEMP_DIR / filename

    # Skip if already downloaded
    if local_path.exists():
        print(f"  [OK] Already downloaded: {filename}")
        return local_path

    print(f"  Downloading {filename}...", end=" ", flush=True)

    try:
        urllib.request.urlretrieve(url, local_path)
        size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"OK ({size_mb:.1f} MB)")
        return local_path
    except Exception as e:
        print(f"FAIL ({e})")
        return None


def extract_archive(archive_path: Path, date_str: str) -> Optional[Path]:
    """Extract archive using py7zr."""
    extract_path = TEMP_DIR / date_str

    # Skip if already extracted
    inner_path = extract_path / date_str
    if inner_path.exists():
        print(f"  [OK] Already extracted: {date_str}")
        return inner_path

    print(f"  Extracting {date_str}...", end=" ", flush=True)

    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            archive.extractall(path=extract_path)
        print("OK")
        # Archive contains a date subdirectory, return the inner path
        return extract_path / date_str
    except Exception as e:
        print(f"FAIL ({e})")
        return None


def load_group_prices(extract_path: Path, group_id: int) -> Optional[Dict]:
    """Load price data for a specific group."""
    # Path: {date}/{categoryId}/{groupId}/prices
    prices_file = extract_path / str(CATEGORY_ID) / str(group_id) / "prices"

    if not prices_file.exists():
        return None

    try:
        with open(prices_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"    [WARN] Failed to load group {group_id}: {e}")
        return None


def process_date(date_str: str, cards: List[Dict], group_ids: Set[int], game: str) -> int:
    """Process prices for one date."""
    print(f"\n[DATE] Processing {date_str}")

    # Download archive
    archive_path = download_archive(date_str)
    if not archive_path:
        return 0

    # Extract archive
    extract_path = extract_archive(archive_path, date_str)
    if not extract_path:
        return 0

    # Build productId → card mapping
    product_map = {str(card.get('productId')): card for card in cards if 'productId' in card}

    # Collect prices from all groups
    snapshots = []
    matched_count = 0

    for group_id in sorted(group_ids):
        group_data = load_group_prices(extract_path, group_id)
        if not group_data:
            continue

        # Extract results array from response
        if not group_data.get('success'):
            continue

        price_results = group_data.get('results', [])
        if not price_results:
            continue

        # Match prices with our cards
        for price_data in price_results:
            product_id = price_data.get('productId')
            if not product_id:
                continue

            product_id_str = str(product_id)
            if product_id_str not in product_map:
                continue

            card = product_map[product_id_str]
            matched_count += 1

            # Create price snapshot
            snapshot = {
                "productId": product_id_str,
                "game": game,
                "cardName": card.get('name', ''),
                "setName": card.get('set'),
                "number": card.get('number'),
                "date": date_str,

                # Prices in cents (convert dollars to cents)
                "marketPrice": int(price_data.get('marketPrice') * 100) if price_data.get('marketPrice') else None,
                "lowPrice": int(price_data.get('lowPrice') * 100) if price_data.get('lowPrice') else None,
                "midPrice": int(price_data.get('midPrice') * 100) if price_data.get('midPrice') else None,
                "highPrice": int(price_data.get('highPrice') * 100) if price_data.get('highPrice') else None,
                "directLowPrice": int(price_data.get('directLowPrice') * 100) if price_data.get('directLowPrice') else None,

                # Variant
                "isFoil": price_data.get('subTypeName', '').lower() == 'foil',
                "source": "tcgcsv-archive"
            }

            snapshots.append(snapshot)

    # Save to JSONL
    output_dir = PRICES_DIR / game
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{date_str}.jsonl"

    with open(output_file, 'w', encoding='utf-8') as f:
        for snapshot in snapshots:
            f.write(json.dumps(snapshot) + '\n')

    size_kb = output_file.stat().st_size / 1024
    print(f"  [SAVED] {len(snapshots)} price snapshots ({matched_count} products matched)")
    print(f"     {output_file.relative_to(PROJECT_ROOT)} ({size_kb:.1f} KB)")

    # Cleanup extracted files to save space (keep archive for resume)
    try:
        import shutil
        shutil.rmtree(extract_path)
    except:
        pass

    return matched_count


def generate_date_range(start_date: datetime, end_date: datetime) -> List[str]:
    """Generate list of dates (YYYY-MM-DD format)."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates


def load_state(game: str) -> Optional[Dict]:
    """Load backfill state."""
    state_file = STATE_DIR / f"backfill-{game}.json"
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return None


def save_state(game: str, last_date: str, total_matched: int):
    """Save backfill state for resume support."""
    state_file = STATE_DIR / f"backfill-{game}.json"
    state = {
        "game": game,
        "lastProcessedDate": last_date,
        "totalMatched": total_matched,
        "lastUpdated": datetime.now().isoformat()
    }
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Backfill historical prices from tcgcsv.com")
    parser.add_argument('--game', default='one-piece', help='Game slug (default: one-piece)')
    parser.add_argument('--start', help='Start date (YYYY-MM-DD, default: 2024-02-08)')
    parser.add_argument('--end', help='End date (YYYY-MM-DD, default: yesterday)')
    parser.add_argument('--test', action='store_true', help='Test mode: only process 1 week')

    args = parser.parse_args()

    # Determine date range
    start_date = datetime.strptime(args.start, '%Y-%m-%d') if args.start else ARCHIVE_START_DATE
    end_date = datetime.strptime(args.end, '%Y-%m-%d') if args.end else datetime.now() - timedelta(days=1)

    if args.test:
        # Test mode: only 1 week
        end_date = start_date + timedelta(days=6)
        print("[TEST MODE] Processing 1 week only")

    print("="*70)
    print("HISTORICAL PRICE BACKFILL (py7zr)")
    print("="*70)
    print(f"Game: {args.game}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Create directories
    ensure_dirs()

    # Load curated cards
    cards = load_curated_cards(args.game)
    group_ids = get_unique_group_ids(cards)
    print(f"[OK] Found {len(group_ids)} unique groups")

    # Generate date list
    dates = generate_date_range(start_date, end_date)
    print(f"[OK] Will process {len(dates)} days")
    print()

    # Check for existing state (resume support)
    state = load_state(args.game)
    if state and not args.start:
        last_date = state.get('lastProcessedDate')
        if last_date:
            try:
                resume_date = datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)
                if resume_date > start_date:
                    print(f"[RESUME] Continuing from {resume_date.strftime('%Y-%m-%d')}")
                    start_date = resume_date
                    dates = generate_date_range(start_date, end_date)
            except:
                pass

    # Process each date
    total_matched = 0
    successful_dates = 0

    for i, date_str in enumerate(dates, 1):
        print(f"\n[{i}/{len(dates)}] ", end="")
        matched = process_date(date_str, cards, group_ids, args.game)

        if matched > 0:
            total_matched += matched
            successful_dates += 1
            save_state(args.game, date_str, total_matched)

        # Progress update every 10 dates
        if i % 10 == 0:
            print(f"\n[PROGRESS] {i}/{len(dates)} dates ({i/len(dates)*100:.1f}%)")
            print(f"   Matched: {total_matched} total products")

    # Final summary
    print("\n" + "="*70)
    print("[COMPLETE] BACKFILL FINISHED")
    print("="*70)
    print(f"Dates processed: {successful_dates}/{len(dates)}")
    print(f"Total products matched: {total_matched}")
    print(f"Output directory: {PRICES_DIR / args.game}")
    print()
    print(f"Next steps:")
    print(f"1. Verify output: ls -lh {PRICES_DIR / args.game}")
    print(f"2. Check file count: ls {PRICES_DIR / args.game}/*.jsonl | wc -l")
    print(f"3. Add to Git LFS: git lfs track 'data/prices/**/*.jsonl'")
    print(f"4. Commit: git add data/prices/ && git commit -m 'feat: Add historical prices'")


if __name__ == "__main__":
    main()
