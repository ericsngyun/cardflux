#!/usr/bin/env python3
"""
CardFlux Professional Shop Scanner
Professional GUI with card stack, running total, and optimized UX
"""
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import json
import threading
import queue
from pathlib import Path
from PIL import Image, ImageTk
import time
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from production_card_identifier import ProductionCardIdentifier

# ============== CONFIGURATION ==============
CAMERA_INDEX = 1
TCG_GAME = "one-piece"
# ===========================================

class CardStackItem:
    """Represents a scanned card in the stack."""
    def __init__(self, card_data, price, confidence):
        self.name = card_data['name']
        self.number = card_data.get('number', 'N/A')
        self.rarity = card_data.get('rarity', 'N/A')
        self.price = price
        self.confidence = confidence
        self.timestamp = time.strftime("%H:%M:%S")

class ShopScannerPro:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CardFlux Professional Shop Scanner - One Piece TCG")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a1a')

        # State
        self.card_stack = []
        self.running_total = 0.0
        self.is_processing = False
        self.identifier = None
        self.cap = None
        self.camera_thread = None
        self.stop_camera = False
        self.result_queue = queue.Queue()

        # Setup UI
        self.setup_ui()

        # Initialize system in background
        threading.Thread(target=self.initialize_system, daemon=True).start()

        # Start camera
        self.start_camera()

        # Bind keys
        self.root.bind('<space>', lambda e: self.capture_card())
        self.root.bind('<Escape>', lambda e: self.on_closing())

        # Update loop
        self.update_frame()

    def setup_ui(self):
        """Create the professional UI layout."""
        # ========== TOP BAR ==========
        top_bar = tk.Frame(self.root, bg='#2d2d2d', height=60)
        top_bar.pack(fill=tk.X, padx=0, pady=0)
        top_bar.pack_propagate(False)

        # Title
        title_label = tk.Label(
            top_bar,
            text="🃏 CardFlux Professional Scanner",
            font=('Segoe UI', 20, 'bold'),
            bg='#2d2d2d',
            fg='#4CAF50'
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # System status
        self.status_label = tk.Label(
            top_bar,
            text="⚙️ Initializing...",
            font=('Segoe UI', 10),
            bg='#2d2d2d',
            fg='#FFA726'
        )
        self.status_label.pack(side=tk.RIGHT, padx=20, pady=10)

        # ========== MAIN CONTENT ==========
        main_container = tk.Frame(self.root, bg='#1a1a1a')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel - Camera + Controls
        left_panel = tk.Frame(main_container, bg='#2d2d2d', width=700)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_panel.pack_propagate(False)

        # Camera view
        camera_frame = tk.Frame(left_panel, bg='#000000')
        camera_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.camera_label = tk.Label(camera_frame, bg='#000000')
        self.camera_label.pack(fill=tk.BOTH, expand=True)

        # Controls
        controls_frame = tk.Frame(left_panel, bg='#2d2d2d', height=120)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        controls_frame.pack_propagate(False)

        # Capture button
        self.capture_btn = tk.Button(
            controls_frame,
            text="📸 CAPTURE CARD\n(Press SPACE)",
            font=('Segoe UI', 14, 'bold'),
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049',
            command=self.capture_card,
            height=3,
            cursor='hand2'
        )
        self.capture_btn.pack(fill=tk.X, pady=(10, 5))

        # Processing indicator
        self.processing_label = tk.Label(
            controls_frame,
            text="",
            font=('Segoe UI', 10),
            bg='#2d2d2d',
            fg='#FFA726'
        )
        self.processing_label.pack()

        # Right Panel - Card Stack + Totals
        right_panel = tk.Frame(main_container, bg='#2d2d2d')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Stack header
        stack_header = tk.Frame(right_panel, bg='#3d3d3d', height=60)
        stack_header.pack(fill=tk.X)
        stack_header.pack_propagate(False)

        stack_title = tk.Label(
            stack_header,
            text="📚 SCANNED CARDS",
            font=('Segoe UI', 16, 'bold'),
            bg='#3d3d3d',
            fg='white'
        )
        stack_title.pack(side=tk.LEFT, padx=20, pady=15)

        self.stack_count_label = tk.Label(
            stack_header,
            text="0 cards",
            font=('Segoe UI', 12),
            bg='#3d3d3d',
            fg='#90CAF9'
        )
        self.stack_count_label.pack(side=tk.LEFT, padx=10)

        # Clear button
        clear_btn = tk.Button(
            stack_header,
            text="🗑️ CLEAR STACK",
            font=('Segoe UI', 10, 'bold'),
            bg='#F44336',
            fg='white',
            activebackground='#d32f2f',
            command=self.clear_stack,
            cursor='hand2',
            padx=15,
            pady=5
        )
        clear_btn.pack(side=tk.RIGHT, padx=20)

        # Stack list (with scrollbar)
        stack_container = tk.Frame(right_panel, bg='#2d2d2d')
        stack_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(stack_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview for card stack
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Stack.Treeview",
            background="#1a1a1a",
            foreground="white",
            fieldbackground="#1a1a1a",
            borderwidth=0,
            font=('Segoe UI', 10),
            rowheight=30
        )
        style.configure(
            "Stack.Treeview.Heading",
            background="#3d3d3d",
            foreground="white",
            font=('Segoe UI', 10, 'bold'),
            borderwidth=0
        )
        style.map('Stack.Treeview', background=[('selected', '#4CAF50')])

        self.stack_tree = ttk.Treeview(
            stack_container,
            columns=('card', 'number', 'rarity', 'price', 'conf', 'time'),
            show='headings',
            style="Stack.Treeview",
            yscrollcommand=scrollbar.set
        )

        # Column headers
        self.stack_tree.heading('card', text='Card Name')
        self.stack_tree.heading('number', text='Number')
        self.stack_tree.heading('rarity', text='Rarity')
        self.stack_tree.heading('price', text='Price')
        self.stack_tree.heading('conf', text='Confidence')
        self.stack_tree.heading('time', text='Time')

        # Column widths
        self.stack_tree.column('card', width=250)
        self.stack_tree.column('number', width=100)
        self.stack_tree.column('rarity', width=60)
        self.stack_tree.column('price', width=80)
        self.stack_tree.column('conf', width=90)
        self.stack_tree.column('time', width=80)

        self.stack_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.stack_tree.yview)

        # Totals footer
        totals_frame = tk.Frame(right_panel, bg='#3d3d3d', height=100)
        totals_frame.pack(fill=tk.X)
        totals_frame.pack_propagate(False)

        # Running total
        total_label = tk.Label(
            totals_frame,
            text="💰 TOTAL VALUE:",
            font=('Segoe UI', 14, 'bold'),
            bg='#3d3d3d',
            fg='white'
        )
        total_label.pack(side=tk.LEFT, padx=20, pady=20)

        self.total_value_label = tk.Label(
            totals_frame,
            text="$0.00",
            font=('Segoe UI', 24, 'bold'),
            bg='#3d3d3d',
            fg='#4CAF50'
        )
        self.total_value_label.pack(side=tk.LEFT, padx=10)

        # Export button
        export_btn = tk.Button(
            totals_frame,
            text="📊 EXPORT TO CSV",
            font=('Segoe UI', 10, 'bold'),
            bg='#2196F3',
            fg='white',
            activebackground='#1976D2',
            command=self.export_stack,
            cursor='hand2',
            padx=15,
            pady=8
        )
        export_btn.pack(side=tk.RIGHT, padx=20)

        # Bottom bar - Help
        bottom_bar = tk.Frame(self.root, bg='#2d2d2d', height=40)
        bottom_bar.pack(fill=tk.X)
        bottom_bar.pack_propagate(False)

        help_text = tk.Label(
            bottom_bar,
            text="⌨️ SPACE: Capture Card  |  🗑️ Clear Stack: Reset All  |  ESC: Exit  |  💡 High Confidence Only Added to Stack",
            font=('Segoe UI', 9),
            bg='#2d2d2d',
            fg='#90CAF9'
        )
        help_text.pack(pady=10)

    def initialize_system(self):
        """Initialize card identification system in background."""
        try:
            self.root.after(0, lambda: self.status_label.config(
                text="⚙️ Loading AI models..."
            ))

            self.identifier = ProductionCardIdentifier(
                game=TCG_GAME,
                verbose=False
            )

            self.root.after(0, lambda: self.status_label.config(
                text="✅ Ready",
                fg='#4CAF50'
            ))

            self.root.after(0, lambda: self.capture_btn.config(state=tk.NORMAL))

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text=f"❌ Error: {str(e)}",
                fg='#F44336'
            ))
            messagebox.showerror("Initialization Error", f"Failed to load system:\n{e}")

    def start_camera(self):
        """Start camera in background thread."""
        def camera_loop():
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
            if not self.cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror(
                    "Camera Error",
                    f"Cannot open camera {CAMERA_INDEX}\nTry changing CAMERA_INDEX to 0"
                ))
                return

            while not self.stop_camera:
                ret, frame = self.cap.read()
                if ret:
                    # Store frame for capture
                    self.current_frame = frame.copy()

                    # Convert for display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_pil = Image.fromarray(frame_rgb)

                    # Resize to fit
                    display_size = (660, 495)  # 4:3 aspect ratio
                    frame_pil = frame_pil.resize(display_size, Image.Resampling.LANCZOS)

                    frame_tk = ImageTk.PhotoImage(frame_pil)

                    # Update label
                    self.root.after(0, lambda img=frame_tk: self.update_camera_display(img))

                time.sleep(0.03)  # ~30 FPS

            if self.cap:
                self.cap.release()

        self.camera_thread = threading.Thread(target=camera_loop, daemon=True)
        self.camera_thread.start()

    def update_camera_display(self, img):
        """Update camera display (must be called from main thread)."""
        self.camera_label.config(image=img)
        self.camera_label.image = img  # Keep reference

    def update_frame(self):
        """Update loop for processing results."""
        # Check for identification results
        try:
            while not self.result_queue.empty():
                result = self.result_queue.get_nowait()
                self.add_to_stack(result)
                self.is_processing = False
                self.processing_label.config(text="")
        except queue.Empty:
            pass

        # Schedule next update
        self.root.after(50, self.update_frame)

    def capture_card(self):
        """Capture card and identify in background."""
        if self.is_processing:
            return

        if not self.identifier:
            messagebox.showwarning("Not Ready", "System is still initializing...")
            return

        if not hasattr(self, 'current_frame'):
            messagebox.showwarning("No Camera", "Camera not ready")
            return

        # Mark as processing
        self.is_processing = True
        self.processing_label.config(text="🔍 Identifying...")

        # Save frame
        temp_path = "temp_capture.jpg"
        cv2.imwrite(temp_path, self.current_frame)

        # Identify in background thread
        def identify_thread():
            try:
                result = self.identifier.identify(
                    temp_path,
                    top_k=30,
                    tcg_hint=TCG_GAME
                )
                self.result_queue.put(result)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Identification Error",
                    f"Failed to identify card:\n{e}"
                ))
                self.is_processing = False
                self.root.after(0, lambda: self.processing_label.config(text=""))

        threading.Thread(target=identify_thread, daemon=True).start()

    def add_to_stack(self, result):
        """Add identified card to stack."""
        best = result['best_match']
        confidence = result['confidence']

        # Only add HIGH confidence cards
        if confidence != "HIGH":
            messagebox.showwarning(
                "Low Confidence",
                f"Card: {best['name']}\nConfidence: {confidence}\n\n"
                f"Only HIGH confidence cards are added to stack.\n"
                f"Please try again with better lighting/positioning."
            )
            return

        # Get price
        prices = best.get('prices', {})
        price = 0.0

        if 'normal' in prices and prices['normal']:
            price = prices['normal'].get('market', 0.0) or 0.0
        elif 'foil' in prices and prices['foil']:
            price = prices['foil'].get('market', 0.0) or 0.0

        # Create stack item
        item = CardStackItem(best, price, confidence)
        self.card_stack.append(item)

        # Add to tree
        self.stack_tree.insert(
            '',
            0,  # Insert at top
            values=(
                item.name[:35] + '...' if len(item.name) > 35 else item.name,
                item.number,
                item.rarity,
                f"${price:.2f}",
                confidence,
                item.timestamp
            )
        )

        # Update totals
        self.running_total += price
        self.update_totals()

        # Visual feedback
        self.flash_success()

    def update_totals(self):
        """Update stack count and total value."""
        count = len(self.card_stack)
        self.stack_count_label.config(text=f"{count} card{'s' if count != 1 else ''}")
        self.total_value_label.config(text=f"${self.running_total:.2f}")

    def clear_stack(self):
        """Clear the card stack."""
        if not self.card_stack:
            return

        if messagebox.askyesno(
            "Clear Stack",
            f"Clear {len(self.card_stack)} cards totaling ${self.running_total:.2f}?"
        ):
            self.card_stack.clear()
            self.running_total = 0.0

            # Clear tree
            for item in self.stack_tree.get_children():
                self.stack_tree.delete(item)

            self.update_totals()

            messagebox.showinfo("Stack Cleared", "Ready to scan new cards!")

    def export_stack(self):
        """Export stack to CSV."""
        if not self.card_stack:
            messagebox.showinfo("Nothing to Export", "Stack is empty")
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scan_session_{timestamp}.csv"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Card Name,Number,Rarity,Price,Confidence,Time\n")
                for item in self.card_stack:
                    f.write(f'"{item.name}",{item.number},{item.rarity},${item.price:.2f},{item.confidence},{item.timestamp}\n')
                f.write(f"\nTOTAL,,,,${self.running_total:.2f}\n")

            messagebox.showinfo(
                "Export Successful",
                f"Exported {len(self.card_stack)} cards to:\n{filename}\n\n"
                f"Total Value: ${self.running_total:.2f}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")

    def flash_success(self):
        """Visual feedback for successful scan."""
        original_bg = self.capture_btn.cget('bg')
        self.capture_btn.config(bg='#66BB6A')
        self.root.after(200, lambda: self.capture_btn.config(bg=original_bg))

    def on_closing(self):
        """Handle window close."""
        if self.card_stack and messagebox.askyesno(
            "Exit",
            f"You have {len(self.card_stack)} cards in stack.\n"
            f"Total: ${self.running_total:.2f}\n\n"
            f"Exit without exporting?"
        ):
            self.stop_camera = True
            self.root.destroy()
        elif not self.card_stack:
            self.stop_camera = True
            self.root.destroy()

    def run(self):
        """Start the application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    """Entry point."""
    app = ShopScannerPro()
    app.run()

if __name__ == "__main__":
    main()
