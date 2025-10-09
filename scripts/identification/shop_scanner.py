#!/usr/bin/env python3
"""
Shop Card Scanner - Simple workflow for document camera
Press SPACE to capture, ESC to exit
"""
import cv2
import sys
import subprocess
from pathlib import Path
import time

# ============== CONFIGURATION ==============
CAMERA_INDEX = 1  # Change to 0 if document camera doesn't work
TCG_GAME = "one-piece"
# ===========================================

def main():
    print("=" * 70)
    print("SHOP CARD SCANNER - One Piece TCG")
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
        print("  1. Open shop_scanner.py in text editor")
        print("  2. Change line: CAMERA_INDEX = 1")
        print("  3. Try: CAMERA_INDEX = 0")
        return

    print(f"[OK] Camera {CAMERA_INDEX} ready")
    print()
    print("=" * 70)
    print("CONTROLS:")
    print("  SPACE - Capture and identify card")
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

            # Run identification
            start = time.time()
            result = subprocess.run([
                sys.executable,
                "production_card_identifier.py",
                output_path,
                "--tcg", TCG_GAME
            ], capture_output=False)
            elapsed = time.time() - start

            print(f"\nIdentification took {elapsed:.1f} seconds")
            print("\n" + "=" * 70)
            print("Place next card and press SPACE")
            print("=" * 70)
            print()

            # Reopen preview window
            cv2.imshow('Shop Card Scanner (SPACE=capture, ESC=exit)', frame)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal cards scanned: {card_count}")

if __name__ == "__main__":
    main()
