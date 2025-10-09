#!/usr/bin/env python3
"""
Shop Card Scanner with Prices - Enhanced version
Press SPACE to capture, ESC to exit
Shows card identification + TCGPlayer prices
"""
import cv2
import sys
import subprocess
import json
from pathlib import Path
import time

# ============== CONFIGURATION ==============
CAMERA_INDEX = 1  # Change to 0 if document camera doesn't work
TCG_GAME = "one-piece"
# ===========================================

def print_card_result(result):
    """Print card result in shop-friendly format."""
    best = result['best_match']
    scores = result['scores']
    confidence = result['confidence']

    print("\n" + "="*70)
    print("  CARD IDENTIFIED")
    print("="*70)

    # Card info
    print(f"\n  Card: {best['name']}")
    print(f"  Number: {best.get('number', 'N/A')}")
    print(f"  Rarity: {best.get('rarity', 'N/A')}")

    # PRICES - Most important for shop!
    prices = best.get('prices', {})
    if prices:
        print(f"\n  === PRICES (TCGPlayer) ===")

        # Foil prices
        if 'foil' in prices and prices['foil']:
            foil_prices = prices['foil']
            market = foil_prices.get('market')
            low = foil_prices.get('low')

            if market:
                print(f"  FOIL Market:  ${market:.2f}")
            if low:
                print(f"  FOIL Low:     ${low:.2f}")

        # Normal prices
        if 'normal' in prices and prices['normal']:
            normal_prices = prices['normal']
            market = normal_prices.get('market')
            low = normal_prices.get('low')
            mid = normal_prices.get('mid')

            if market:
                print(f"  Market Price: ${market:.2f}  <-- USE THIS")
            if low and mid:
                print(f"  Low-Mid:      ${low:.2f} - ${mid:.2f}")

        # If only one type of price, show it prominently
        if not ('normal' in prices and 'foil' in prices):
            if 'foil' in prices:
                print(f"  (Foil card - no normal version)")
            elif 'normal' in prices:
                print(f"  (Normal card - no foil version)")
    else:
        print(f"\n  Prices: NOT AVAILABLE")

    # Confidence indicator
    print(f"\n  Confidence: {confidence}")
    if confidence == "HIGH":
        print(f"  [OK] High confidence - Accept this result")
    elif confidence == "MODERATE":
        print(f"  [?] Moderate - Double-check recommended")
    else:
        print(f"  [!] Low confidence - Manual verification needed")

    # Time
    print(f"\n  Identification time: {result['time_ms']}ms")

    print("="*70 + "\n")

def main():
    print("=" * 70)
    print("SHOP CARD SCANNER WITH PRICES - One Piece TCG")
    print("=" * 70)
    print()
    print("Initializing camera...")

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {CAMERA_INDEX}")
        print("Try changing CAMERA_INDEX in script (0 or 1)")
        print()
        print("Quick fix:")
        print("  1. Open shop_scanner_with_prices.py in text editor")
        print("  2. Change line: CAMERA_INDEX = 1")
        print("  3. Try: CAMERA_INDEX = 0")
        return

    print(f"[OK] Camera {CAMERA_INDEX} ready")
    print()
    print("=" * 70)
    print("CONTROLS:")
    print("  SPACE - Capture and identify card (with prices)")
    print("  ESC   - Exit")
    print("=" * 70)
    print()

    card_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Cannot read from camera")
            break

        # Optional: Uncomment next line if camera feed is upside down
        # frame = cv2.rotate(frame, cv2.ROTATE_180)

        # Display preview
        cv2.imshow('Shop Card Scanner (SPACE=capture, ESC=exit)', frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            print("\nExiting...")
            break

        elif key == 32:  # SPACE
            card_count += 1
            print(f"\n[Card #{card_count}] Captured! Identifying...")

            # Save image
            output_path = "captured_card.jpg"
            cv2.imwrite(output_path, frame)

            # Close preview window temporarily
            cv2.destroyAllWindows()

            # Run identification and save JSON
            json_output = "last_result.json"
            start = time.time()

            result_code = subprocess.run([
                sys.executable,
                "production_card_identifier.py",
                output_path,
                "--tcg", TCG_GAME,
                "--json", json_output,
                "--quiet"  # Suppress verbose output
            ], capture_output=True, text=True)

            elapsed = time.time() - start

            # Load and display result
            try:
                with open(json_output, 'r') as f:
                    result = json.load(f)

                print_card_result(result)

            except Exception as e:
                print(f"\nERROR: Failed to load result: {e}")
                print("Output:", result_code.stdout)
                print("Errors:", result_code.stderr)

            print("="*70)
            print("Place next card and press SPACE (or ESC to exit)")
            print("="*70)
            print()

            # Reopen preview window
            cv2.imshow('Shop Card Scanner (SPACE=capture, ESC=exit)', frame)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal cards scanned: {card_count}")

if __name__ == "__main__":
    main()
