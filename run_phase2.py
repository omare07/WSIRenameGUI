"""Simple launcher for Phase 2 - GUI-based renaming."""

import sys
import os

def main():
    """Launch Phase 2 directly."""
    print("Starting Phase 2: GUI-based slide renaming...")
    
    try:
        import renaming_gui
        renaming_gui.run_phase2()
    except Exception as e:
        print(f"Error starting Phase 2: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()