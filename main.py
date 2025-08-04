"""Main application for Histology Slide Renaming Tool.

This application provides an intelligent workflow for histology slide review and renaming:
- Phase 1: Extract label images from whole-slide images
- Phase 2: GUI-based renaming using extracted labels
- Auto-detection: Automatically determines which phase to run based on existing files

Usage:
    python main.py                    # Auto-detect and run appropriate phase (default)
    python main.py <folder>           # Auto-detect for specific folder
    python main.py --phase1 <folder> # Run only Phase 1
    python main.py --phase2           # Run only Phase 2
    python main.py --gui              # Start with GUI selector
"""

import argparse
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import traceback

# Import application modules
import config
import label_extractor
import renaming_gui
import utils


def detect_required_phase(folder_path: str) -> str:
    """
    Automatically detect which phase should be run based on file counts.
    
    Args:
        folder_path: Path to the directory containing WSI files
        
    Returns:
        'phase1' if label extraction is needed
        'phase2' if files are ready for renaming
        'none' if no WSI files found
    """
    if not os.path.exists(folder_path):
        return 'none'
    
    # Count WSI files in the main directory
    wsi_files = utils.get_slide_files(folder_path)
    wsi_count = len(wsi_files)
    
    if wsi_count == 0:
        print("No supported WSI files found in the directory.")
        return 'none'
    
    # Check for label image directory and count jpg files
    label_folder = os.path.join(folder_path, config.LABEL_FOLDER)
    jpg_count = 0
    
    if os.path.exists(label_folder):
        for file in os.listdir(label_folder):
            if file.lower().endswith('.jpg') and not utils.should_skip_file(file):
                jpg_count += 1
    
    print(f"Found {wsi_count} WSI files and {jpg_count} label images")
    
    # Determine which phase to run
    if jpg_count >= wsi_count:
        print("Label images available - starting Phase 2 (Renaming)")
        return 'phase2'
    else:
        print("Need to extract labels - starting Phase 1 (Label extraction)")
        return 'phase1'


class MainSelector:
    """GUI for selecting which phase to run."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Histology Slide Renaming Tool")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        self._setup_gui()
    
    def _setup_gui(self):
        """Setup the main selector GUI."""
        # Title
        title_label = tk.Label(
            self.root, 
            text="Histology Slide Renaming Tool",
            font=("Arial", 16, "bold"),
            pady=20
        )
        title_label.pack()
        
        # Description
        desc_text = """This tool helps with histology slide review and file renaming in two phases:

Phase 1: Label Image Extraction
• Extract label images from whole-slide images (.svs, .ndpi, .scn)
• Manual crop selection for consistent processing
• Rotate and save label images for review

Phase 2: GUI-Based Renaming  
• Display label images with navigation
• Input numeric identifiers for renaming
• Preview and apply systematic file renaming
• Handle duplicates and maintain logs

Auto-Detect & Run (Recommended)
• Automatically detects which phase is needed
• Runs Phase 1 if no label images exist
• Runs Phase 2 if label images are ready

Choose how you'd like to proceed:"""
        
        desc_label = tk.Label(
            self.root, 
            text=desc_text,
            font=("Arial", 10),
            justify=tk.LEFT,
            pady=10
        )
        desc_label.pack(padx=20)
        
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        # Phase buttons
        phase1_btn = tk.Button(
            button_frame,
            text="Phase 1: Extract Labels",
            command=self._run_phase1,
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        phase1_btn.pack(pady=5)
        
        phase2_btn = tk.Button(
            button_frame,
            text="Phase 2: Rename Files",
            command=self._run_phase2,
            font=("Arial", 12),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        phase2_btn.pack(pady=5)
        
        both_btn = tk.Button(
            button_frame,
            text="Run Complete Workflow",
            command=self._run_both_phases,
            font=("Arial", 12),
            bg="#FF9800",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        both_btn.pack(pady=5)
        
        # Auto-detect button
        auto_btn = tk.Button(
            button_frame,
            text="Auto-Detect & Run",
            command=self._run_auto_detect,
            font=("Arial", 12),
            bg="#9C27B0",
            fg="white",
            padx=20,
            pady=10,
            width=20
        )
        auto_btn.pack(pady=5)
        
        # Exit button
        exit_btn = tk.Button(
            button_frame,
            text="Exit",
            command=self.root.quit,
            font=("Arial", 10),
            padx=20,
            pady=5,
            width=20
        )
        exit_btn.pack(pady=(20, 5))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Arial", 9),
            fg="gray",
            anchor=tk.W
        )
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
    
    def _run_phase1(self):
        """Run Phase 1 with folder selection."""
        folder_path = filedialog.askdirectory(
            title="Select Folder with Slide Files",
            initialdir=os.getcwd()
        )
        
        if not folder_path:
            return
        
        # Check for PhotoImage issues and offer solutions
        self.status_var.set("Checking system compatibility...")
        self.root.update()
        
        try:
            # Test PhotoImage functionality
            from PIL import Image, ImageTk
            test_img = Image.new('RGB', (100, 100), color='red')
            test_root = tk.Toplevel(self.root)
            test_root.withdraw()
            test_photo = ImageTk.PhotoImage(test_img)
            test_canvas = tk.Canvas(test_root, width=100, height=100)
            test_canvas.create_image(0, 0, anchor=tk.NW, image=test_photo)
            test_root.destroy()
            photoimage_works = True
            
        except Exception as e:
            photoimage_works = False
            print(f"PhotoImage test failed: {e}")
        
        # Inform user about crop selection method
        if not photoimage_works:
            result = messagebox.askyesno(
                "Crop Selection Method",
                "Visual crop selection may not work with your Python installation.\\n\\n"
                "Would you like to use coordinate-based crop selection instead?\\n\\n"
                "YES: Enter coordinates manually (recommended)\\n"
                "NO: Try visual selection anyway"
            )
            
            if result:
                # Use coordinate-based method
                messagebox.showinfo(
                    "Coordinate Method",
                    "You'll be prompted to enter crop coordinates.\\n\\n"
                    "The first slide's label image size will be shown,\\n"
                    "and you can enter pixel coordinates for the crop region."
                )
        
        self.status_var.set("Running Phase 1: Label extraction...")
        self.root.update()
        
        try:
            success = label_extractor.run_phase1(folder_path)
            
            if success:
                self.status_var.set("Phase 1 completed successfully!")
                messagebox.showinfo(
                    "Success", 
                    f"Label extraction completed!\\n\\nLabel images saved to:\\n{os.path.join(folder_path, config.LABEL_FOLDER)}"
                )
            else:
                self.status_var.set("Phase 1 failed!")
                # Provide more helpful error message
                error_msg = ("Phase 1 failed. This might be due to:\\n\\n"
                           "• No supported slide files found\\n"
                           "• Crop selection was cancelled\\n"
                           "• OpenSlide cannot read the files\\n\\n"
                           "Check the console for detailed error messages.\\n\\n"
                           "Alternative: Try running:\\n"
                           "python launch_phase1.py")
                messagebox.showerror("Error", error_msg)
        
        except Exception as e:
            self.status_var.set("Phase 1 error!")
            error_msg = f"Phase 1 error: {str(e)}\\n\\nFor PhotoImage-related errors, try:\\npython launch_phase1.py"
            messagebox.showerror("Error", error_msg)
            print(f"Phase 1 error: {traceback.format_exc()}")
    
    def _run_phase2(self):
        """Run Phase 2 GUI."""
        self.status_var.set("Starting Phase 2...")
        self.root.update()
        
        try:
            # Close selector window
            self.root.withdraw()
            
            # Run Phase 2 GUI (no folder pre-loading for manual phase selection)
            renaming_gui.run_phase2()
            
            # Show selector again when Phase 2 is closed
            self.root.deiconify()
            self.status_var.set("Phase 2 completed")
        
        except Exception as e:
            self.root.deiconify()
            self.status_var.set("Phase 2 error!")
            messagebox.showerror("Error", f"Phase 2 error: {str(e)}")
            print(f"Phase 2 error: {traceback.format_exc()}")
    
    def _run_auto_detect(self):
        """Auto-detect which phase to run and execute it."""
        folder_path = filedialog.askdirectory(
            title="Select Folder with Slide Files",
            initialdir=os.getcwd()
        )
        
        if not folder_path:
            return
        
        self.status_var.set("Analyzing directory...")
        self.root.update()
        
        try:
            required_phase = detect_required_phase(folder_path)
            
            if required_phase == 'none':
                self.status_var.set("No WSI files found")
                messagebox.showerror("Error", "No supported WSI files found in the selected directory.")
                return
            
            elif required_phase == 'phase1':
                self.status_var.set("Running Phase 1...")
                self.root.update()
                
                # Run Phase 1
                success = label_extractor.run_phase1(folder_path)
                
                if success:
                    self.status_var.set("Phase 1 completed. Starting Phase 2...")
                    self.root.update()
                    
                    # Automatically continue to Phase 2
                    self.root.after(1000, lambda: self._continue_phase2(folder_path))
                else:
                    self.status_var.set("Phase 1 failed!")
                    messagebox.showerror("Error", "Phase 1 failed. Check console for details.")
            
            elif required_phase == 'phase2':
                self.status_var.set("Starting Phase 2...")
                self.root.update()
                
                # Run Phase 2 directly with pre-loaded folder
                self.root.withdraw()
                app = renaming_gui.RenamingGUI(folder_path)
                app.run()
                
                self.root.deiconify()
                self.status_var.set("Phase 2 completed")
        
        except Exception as e:
            self.status_var.set("Auto-detect error!")
            messagebox.showerror("Error", f"Auto-detect error: {str(e)}")
            print(f"Auto-detect error: {traceback.format_exc()}")
    
    def _run_both_phases(self):
        """Run complete workflow."""
        result = messagebox.askyesno(
            "Complete Workflow",
            "This will run both phases in sequence:\\n\\n1. Extract label images from slides\\n2. Open renaming GUI\\n\\nContinue?"
        )
        
        if not result:
            return
        
        # Phase 1
        folder_path = filedialog.askdirectory(
            title="Select Folder with Slide Files",
            initialdir=os.getcwd()
        )
        
        if not folder_path:
            return
        
        self.status_var.set("Running Phase 1...")
        self.root.update()
        
        try:
            success = label_extractor.run_phase1(folder_path)
            
            if not success:
                self.status_var.set("Workflow stopped - Phase 1 failed!")
                messagebox.showerror("Error", "Phase 1 failed. Workflow stopped.")
                return
            
            self.status_var.set("Phase 1 completed. Starting Phase 2...")
            self.root.update()
            
            # Small delay to show status
            self.root.after(1000, lambda: self._continue_phase2(folder_path))
        
        except Exception as e:
            self.status_var.set("Workflow error!")
            messagebox.showerror("Error", f"Workflow error: {str(e)}")
            print(f"Workflow error: {traceback.format_exc()}")
    
    def _continue_phase2(self, folder_path):
        """Continue to Phase 2 after Phase 1 completion."""
        try:
            # Close selector window
            self.root.withdraw()
            
            # Create and run Phase 2 GUI with pre-loaded folder
            app = renaming_gui.RenamingGUI(folder_path)
            app.run()
            
            # Show selector again when Phase 2 is closed
            self.root.deiconify()
            self.status_var.set("Complete workflow finished!")
            
        except Exception as e:
            self.root.deiconify()
            self.status_var.set("Phase 2 error!")
            messagebox.showerror("Error", f"Phase 2 error: {str(e)}")
            print(f"Phase 2 error: {traceback.format_exc()}")
    
    def run(self):
        """Run the main selector."""
        self.root.mainloop()


def run_phase1_cli(folder_path: str):
    """Run Phase 1 from command line."""
    print(f"Starting Phase 1: Label extraction from {folder_path}")
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder does not exist: {folder_path}")
        return False
    
    try:
        success = label_extractor.run_phase1(folder_path)
        
        if success:
            print("\\nPhase 1 completed successfully!")
            print(f"Label images saved to: {os.path.join(folder_path, config.LABEL_FOLDER)}")
        else:
            print("\\nPhase 1 failed!")
        
        return success
    
    except Exception as e:
        print(f"\\nPhase 1 error: {e}")
        print(traceback.format_exc())
        return False


def run_phase2_cli(folder_path: str = ""):
    """Run Phase 2 from command line."""
    print("Starting Phase 2: GUI for file renaming")
    
    try:
        renaming_gui.run_phase2(folder_path)
        print("\\nPhase 2 completed!")
    
    except Exception as e:
        print(f"\\nPhase 2 error: {e}")
        print(traceback.format_exc())


def run_auto_detect_cli(folder_path: str):
    """Run auto-detection from command line."""
    print(f"Auto-detecting required phase for: {folder_path}")
    print("=" * 50)
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder does not exist: {folder_path}")
        return False
    
    try:
        required_phase = detect_required_phase(folder_path)
        
        if required_phase == 'none':
            print("No supported WSI files found.")
            return False
        
        elif required_phase == 'phase1':
            print("\\nRunning Phase 1: Label extraction")
            success = label_extractor.run_phase1(folder_path)
            
            if success:
                print("\\nPhase 1 completed! Now starting Phase 2...")
                # Automatically continue to Phase 2 with folder path
                renaming_gui.run_phase2(folder_path)
                return True
            else:
                print("\\nPhase 1 failed!")
                return False
        
        elif required_phase == 'phase2':
            print("\\nRunning Phase 2: File renaming")
            renaming_gui.run_phase2(folder_path)
            return True
        
        return False
    
    except Exception as e:
        print(f"\\nAuto-detect error: {e}")
        print(traceback.format_exc())
        return False


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Histology Slide Renaming Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Auto-detect and run appropriate phase
  python main.py /path/to/slides    # Auto-detect for specific folder
  python main.py --gui              # Run GUI selector  
  python main.py --phase1 /path/to/slides  # Extract labels only
  python main.py --phase2           # Run renaming GUI only
        """
    )
    
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder path for auto-detection (optional)"
    )
    
    parser.add_argument(
        "--phase1", 
        metavar="FOLDER",
        help="Run Phase 1 only: extract label images from specified folder"
    )
    
    parser.add_argument(
        "--phase2", 
        action="store_true",
        help="Run Phase 2 only: open renaming GUI"
    )
    
    parser.add_argument(
        "--gui", 
        action="store_true",
        help="Run GUI selector"
    )
    
    args = parser.parse_args()
    
    try:
        if args.phase1:
            # Run Phase 1 only
            run_phase1_cli(args.phase1)
        
        elif args.phase2:
            # Run Phase 2 only
            run_phase2_cli()
        
        elif args.gui:
            # Run GUI selector
            print("Starting Histology Slide Renaming Tool...")
            selector = MainSelector()
            selector.run()
        
        elif args.folder:
            # Auto-detect and run for specified folder
            run_auto_detect_cli(args.folder)
        
        else:
            # Default behavior: prompt user for folder and auto-detect
            from tkinter import filedialog
            import tkinter as tk
            
            root = tk.Tk()
            root.withdraw()
            
            folder_path = filedialog.askdirectory(
                title="Select Folder with Slide Files",
                initialdir=os.getcwd()
            )
            root.destroy()
            
            if folder_path:
                run_auto_detect_cli(folder_path)
            else:
                print("No folder selected. Starting GUI selector...")
                selector = MainSelector()
                selector.run()
    
    except KeyboardInterrupt:
        print("\\n\\nApplication interrupted by user")
    
    except Exception as e:
        print(f"\\nApplication error: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()