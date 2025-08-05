"""Smart launcher for Phase 1 that handles PhotoImage issues."""

import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import traceback

def test_photoimage():
    """Test if PhotoImage works in this environment."""
    try:
        from PIL import Image, ImageTk
        
        # Create a simple test image
        test_img = Image.new('RGB', (100, 100), color='red')
        
        # Try to create PhotoImage
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        photo = ImageTk.PhotoImage(test_img)
        
        # Try to create canvas and display image
        canvas = tk.Canvas(root, width=100, height=100)
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        
        root.destroy()
        print("PhotoImage test passed")
        return True
        
    except Exception as e:
        print(f"PhotoImage test failed: {e}")
        return False

def choose_crop_method():
    """Let user choose crop method."""
    root = tk.Tk()
    root.title("Choose Crop Method")
    root.geometry("500x300")
    
    choice = [None]
    
    tk.Label(root, text="Choose Crop Selection Method", 
             font=("Arial", 14, "bold")).pack(pady=20)
    
    tk.Label(root, text="Two methods are available for selecting the crop region:", 
             font=("Arial", 10)).pack(pady=10)
    
    # Method descriptions
    method_frame = tk.Frame(root)
    method_frame.pack(pady=20)
    
    def choose_visual():
        choice[0] = "visual"
        root.destroy()
    
    def choose_coordinate():
        choice[0] = "coordinate"
        root.destroy()
    
    # Visual method button
    visual_frame = tk.Frame(method_frame)
    visual_frame.pack(pady=10)
    
    tk.Button(visual_frame, text="Visual Selection", command=choose_visual,
              font=("Arial", 12), bg="#4CAF50", fg="white", 
              width=20, height=2).pack()
    tk.Label(visual_frame, text="Click and drag on displayed image\\n(May not work with some Python installations)",
             font=("Arial", 8), fg="gray").pack()
    
    # Coordinate method button  
    coord_frame = tk.Frame(method_frame)
    coord_frame.pack(pady=10)
    
    tk.Button(coord_frame, text="Coordinate Entry", command=choose_coordinate,
              font=("Arial", 12), bg="#2196F3", fg="white",
              width=20, height=2).pack()
    tk.Label(coord_frame, text="Enter coordinates manually\\n(Works with all Python installations)",
             font=("Arial", 8), fg="gray").pack()
    
    root.mainloop()
    return choice[0]

def launch_phase1():
    """Launch Phase 1 with appropriate crop method."""
    print("Histology Slide Renaming Tool - Phase 1 Launcher")
    print("=" * 50)
    
    # Get folder path
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title="Select Folder with Slide Files",
            initialdir=os.getcwd()
        )
        root.destroy()
    
    if not folder_path:
        print("No folder selected. Exiting.")
        return
    
    if not os.path.exists(folder_path):
        print(f"Folder does not exist: {folder_path}")
        return
    
    print(f"Processing slides in: {folder_path}")
    
    # Test PhotoImage capability
    print("\\nTesting image display capabilities...")
    photoimage_works = test_photoimage()
    
    # Choose method based on test results
    if photoimage_works:
        print("Visual crop selection should work. Proceeding with standard method...")
        crop_method = "visual"
    else:
        print("PhotoImage issues detected. Recommend using coordinate entry method.")
        crop_method = choose_crop_method()
        
        if crop_method is None:
            print("No method selected. Exiting.")
            return
    
    print(f"Using crop method: {crop_method}")
    
    # Note: The label extractor will handle coordinate method automatically
    
    # Import and run Phase 1
    try:
        import label_extractor
        success = label_extractor.run_phase1(folder_path)
        
        if success:
            print("\\nPhase 1 completed successfully!")
            print(f"Label images saved to: {os.path.join(folder_path, 'label_image')}")
        else:
            print("\\nPhase 1 failed!")
            
    except Exception as e:
        print(f"\\nPhase 1 error: {e}")
        print("Full traceback:")
        traceback.print_exc()



if __name__ == "__main__":
    launch_phase1()