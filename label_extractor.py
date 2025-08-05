"""Phase 1: Label Image Extraction from histology slides."""

import os
import traceback
from typing import Optional, Tuple, List
from pathlib import Path
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial

try:
    import openslide
except ImportError:
    print("OpenSlide not found. Please install openslide-python: pip install openslide-python")
    exit(1)

from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox, simpledialog
import cv2
import numpy as np

import config
import utils


def process_slide_parallel(slide_file: str, crop_coords: Optional[Tuple[int, int, int, int]], 
                          label_folder: str, cannot_open_folder: str) -> Tuple[str, bool, str]:
    """
    Process a single slide file in parallel.
    
    Args:
        slide_file: Path to the slide file
        crop_coords: Crop coordinates (x1, y1, x2, y2) or None
        label_folder: Path to label output folder
        cannot_open_folder: Path to cannot_open folder
        
    Returns:
        Tuple of (slide_filename, success, message)
    """
    slide_filename = os.path.basename(slide_file)
    
    try:
        # Extract label image
        result = _extract_label_image_standalone(slide_file, cannot_open_folder)
        if result is None:
            return (slide_filename, False, "Could not extract label image")
        
        label_image, is_direct_label = result
        
        # Determine if we need to crop
        need_crop = crop_coords is not None and not is_direct_label
        
        # Process the image (crop and rotate)
        processed_image = _process_label_image_standalone(label_image, crop_coords, need_crop)
        if processed_image is None:
            return (slide_filename, False, "Failed to process label image")
        
        # Save processed image
        output_filename = _get_label_filename_standalone(slide_file)
        output_path = os.path.join(label_folder, output_filename)
        processed_image.save(output_path, "JPEG", quality=90)
        
        method = "direct label" if is_direct_label else "cropped overview"
        return (slide_filename, True, f"Label extracted ({method})")
        
    except Exception as e:
        return (slide_filename, False, f"Error: {str(e)}")


def _extract_label_image_standalone(slide_file: str, cannot_open_folder: str) -> Optional[Tuple[Image.Image, bool]]:
    """Standalone version of _extract_label_image for parallel processing."""
    try:
        # Try to open slide
        slide = openslide.OpenSlide(slide_file)
        
        # Method 1: Try to get direct label image (best option!)
        if 'label' in slide.associated_images:
            label_image = slide.associated_images['label']
            
            # Convert RGBA to RGB if needed
            if label_image.mode == 'RGBA':
                label_image = label_image.convert('RGB')
            
            slide.close()
            return label_image, True  # True means no cropping needed
        
        # Method 2: Check for 'macro' image specifically (needs cropping)
        if 'macro' in slide.associated_images:
            label_image = slide.associated_images['macro']
            
            # Convert RGBA to RGB if needed
            if label_image.mode == 'RGBA':
                label_image = label_image.convert('RGB')
            
            slide.close()
            return label_image, False  # False means cropping IS needed
        
        # Method 3: Check for other associated images that might be direct labels
        for assoc_name in slide.associated_images.keys():
            if any(keyword in assoc_name.lower() for keyword in ['label', 'overview']) and assoc_name != 'macro':
                label_image = slide.associated_images[assoc_name]
                
                # Convert RGBA to RGB if needed
                if label_image.mode == 'RGBA':
                    label_image = label_image.convert('RGB')
                
                slide.close()
                return label_image, True  # True means no cropping needed
        
        # Method 4: Fall back to level 6 overview (requires cropping)
        target_level = min(6, slide.level_count - 1)
        
        # Get dimensions for the target level
        level_dims = slide.level_dimensions[target_level]
        
        # Read the entire level - this contains BOTH tissue and label areas
        whole_image = slide.read_region((0, 0), target_level, level_dims)
        
        # Convert RGBA to RGB if needed
        if whole_image.mode == 'RGBA':
            whole_image = whole_image.convert('RGB')
        
        slide.close()
        return whole_image, False  # False means cropping IS needed
        
    except Exception as e:
        print(f"Cannot open slide {os.path.basename(slide_file)}: {e}")
        # Move to cannot_open folder
        try:
            utils.move_file(slide_file, cannot_open_folder)
            print(f"Moved to cannot_open folder: {os.path.basename(slide_file)}")
        except Exception as move_error:
            print(f"Error moving file: {move_error}")
        return None


def _process_label_image_standalone(image: Image.Image, crop_coords: Optional[Tuple[int, int, int, int]], 
                                  apply_crop: bool) -> Optional[Image.Image]:
    """Standalone version of _process_label_image for parallel processing."""
    try:
        processed = image.copy()
        
        # Apply crop if coordinates are available and requested
        if apply_crop and crop_coords:
            x1, y1, x2, y2 = crop_coords
            processed = processed.crop((x1, y1, x2, y2))
        
        # Rotate by configured angle
        processed = processed.rotate(config.DEFAULT_ROTATION_ANGLE, expand=True)
        
        return processed
        
    except Exception as e:
        print(f"Error processing label image: {e}")
        return None


def _get_label_filename_standalone(slide_file: str) -> str:
    """Standalone version of _get_label_filename for parallel processing."""
    base_name = os.path.splitext(os.path.basename(slide_file))[0]
    return f"{base_name}.jpg"


class CropSelector:
    """GUI for manual crop selection on the first image."""
    
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.crop_coords = None
        self.root = None
        self.canvas = None
        self.photo = None
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.image_id = None
        self.original_image = None
        self.display_scale = 1.0
        
    def select_crop_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Open GUI for crop selection. Returns (x1, y1, x2, y2) or None."""
        try:
            # Load image
            print(f"Loading image for crop selection: {self.image_path}")
            self.original_image = Image.open(self.image_path)
            print(f"Image loaded successfully: {self.original_image.size}")
            
            # Setup and run GUI
            self._setup_gui()
            print("Crop selection GUI created, waiting for user input...")
            self.root.mainloop()
            
            print(f"GUI closed. Crop coordinates: {self.crop_coords}")
            return self.crop_coords
        except Exception as e:
            print(f"Error in crop selection: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up if GUI was created
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            
            return None
    
    def _setup_gui(self):
        """Setup the crop selection GUI."""
        self.root = tk.Tk()
        self.root.title("Select LABEL AREA - Crop the label portion from whole slide overview")
        self.root.geometry("900x700")
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Force window to be on top and focused
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))
        
        # Scale image to fit display
        img_width, img_height = self.original_image.size
        max_display_width, max_display_height = 800, 600
        
        scale_x = max_display_width / img_width
        scale_y = max_display_height / img_height
        self.display_scale = min(scale_x, scale_y, 1.0)
        
        display_width = int(img_width * self.display_scale)
        display_height = int(img_height * self.display_scale)
        
        # Create canvas first
        self.canvas = tk.Canvas(self.root, width=display_width, height=display_height, bg="white")
        self.canvas.pack(pady=10)
        
        # Force GUI update before creating image
        self.root.update_idletasks()
        
        # Resize image for display and keep strong reference
        display_image = self.original_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        # Use a more robust approach for PhotoImage creation
        try:
            # Method 1: Direct PhotoImage creation with explicit root
            self.photo = ImageTk.PhotoImage(display_image, master=self.root)
            self.canvas.image = self.photo  # Store reference
            self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            print("Image displayed successfully in canvas")
            
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            try:
                # Method 2: Save to temporary file and reload
                temp_path = os.path.join(os.path.dirname(self.image_path), "temp_display.png")
                display_image.save(temp_path, "PNG")
                
                # Force a small delay
                self.root.after(100)
                self.root.update()
                
                self.photo = ImageTk.PhotoImage(file=temp_path)
                self.canvas.image = self.photo
                self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                print("Image displayed successfully using temp file method")
                
                # Clean up temp file after a delay
                self.root.after(1000, lambda: self._cleanup_temp_file(temp_path))
                
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
                try:
                    # Method 3: Use PIL Image directly with tkinter Canvas (no PhotoImage)
                    # Convert PIL image to bytes and use create_image differently
                    self._draw_image_fallback(display_image, display_width, display_height)
                    print("Using fallback drawing method")
                    
                except Exception as e3:
                    print(f"All methods failed: {e3}")
                    # Show error message in canvas
                    self.canvas.create_text(
                        display_width//2, display_height//2,
                        text=f"Image display failed\nClick and drag to select crop area anyway\nImage size: {self.original_image.size}",
                        font=("Arial", 12), fill="red", anchor=tk.CENTER
                    )
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self._on_mouse_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        
        # Add buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Confirm Crop", command=self._confirm_crop, 
                 bg="green", fg="white", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self._cancel_crop, 
                 bg="red", fg="white", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        # Instructions
        instructions = tk.Label(self.root, 
                               text="CROP THE LABEL AREA: Click and drag to select the LABEL portion from the macro image\n(You're seeing the full slide - crop only the label/text area, not the tissue)",
                               font=("Arial", 10), fg="blue", justify=tk.CENTER)
        instructions.pack()
    
    def _on_mouse_press(self, event):
        """Handle mouse press."""
        self.start_x = event.x
        self.start_y = event.y
        
        # Remove previous rectangle
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag."""
        # Remove previous rectangle
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # Draw new rectangle
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )
    
    def _on_mouse_release(self, event):
        """Handle mouse release."""
        pass  # Rectangle is already drawn
    
    def _confirm_crop(self):
        """Confirm the crop selection."""
        print("Confirm crop button clicked")
        
        if self.rect_id is None:
            print("No crop region selected")
            messagebox.showwarning("Warning", "Please select a crop region first!")
            return
        
        # Get rectangle coordinates
        coords = self.canvas.coords(self.rect_id)
        print(f"Canvas coordinates: {coords}")
        
        if len(coords) != 4:
            print("Invalid coordinates")
            messagebox.showerror("Error", "Invalid crop selection!")
            return
        
        # Convert display coordinates to original image coordinates
        x1 = int(coords[0] / self.display_scale)
        y1 = int(coords[1] / self.display_scale)
        x2 = int(coords[2] / self.display_scale)
        y2 = int(coords[3] / self.display_scale)
        
        # Ensure coordinates are in correct order
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        self.crop_coords = (x1, y1, x2, y2)
        print(f"Setting crop coordinates: {self.crop_coords}")
        self.root.destroy()
    
    def _cancel_crop(self):
        """Cancel crop selection."""
        print("Cancel crop button clicked")
        self.crop_coords = None
        self.root.destroy()
    
    def _on_window_close(self):
        """Handle window close event (X button)."""
        print("Window closed with X button - treating as cancel")
        self.crop_coords = None
        self.root.destroy()
    
    def _cleanup_temp_file(self, temp_path):
        """Clean up temporary file."""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"Cleaned up temp file: {temp_path}")
        except Exception as e:
            print(f"Could not clean up temp file {temp_path}: {e}")
    
    def _draw_image_fallback(self, display_image, display_width, display_height):
        """Fallback method to draw image using canvas primitives."""
        # This is a last resort - draw a representation of the image
        # Convert image to a simple grid pattern or use canvas drawing
        
        # Create a visual representation using rectangles
        # Sample the image at regular intervals and draw colored rectangles
        sample_size = 20  # Size of each sample square
        cols = display_width // sample_size
        rows = display_height // sample_size
        
        for row in range(rows):
            for col in range(cols):
                # Sample pixel from original image
                sample_x = int((col / cols) * display_image.width)
                sample_y = int((row / rows) * display_image.height)
                
                try:
                    pixel = display_image.getpixel((sample_x, sample_y))
                    if isinstance(pixel, tuple) and len(pixel) >= 3:
                        r, g, b = pixel[:3]
                        color = f"#{r:02x}{g:02x}{b:02x}"
                    else:
                        color = "#808080"  # Gray fallback
                    
                    x1 = col * sample_size
                    y1 = row * sample_size
                    x2 = x1 + sample_size
                    y2 = y1 + sample_size
                    
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                    
                except Exception:
                    # If pixel sampling fails, use gray
                    x1 = col * sample_size
                    y1 = row * sample_size
                    x2 = x1 + sample_size
                    y2 = y1 + sample_size
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="#808080", outline="")
        
        # Add text overlay
        self.canvas.create_text(
            display_width//2, 30,
            text="Fallback Image Display - Click and drag to crop",
            font=("Arial", 10), fill="white", anchor=tk.CENTER
        )


class LabelExtractor:
    """Extract and process label images from histology slides."""
    
    def __init__(self, slide_folder: str):
        self.slide_folder = slide_folder
        self.label_folder = os.path.join(slide_folder, config.LABEL_FOLDER)
        self.cannot_open_folder = os.path.join(slide_folder, config.CANNOT_OPEN_FOLDER)
        self.crop_coords = None
        self.batch_size = config.DEFAULT_BATCH_SIZE  # Can be overridden via configuration
        
        # Create output directories
        utils.create_directory(self.label_folder)
        utils.create_directory(self.cannot_open_folder)
    
    def extract_all_labels(self) -> bool:
        """Extract label images from all slides in the folder."""
        slide_files = utils.get_slide_files(self.slide_folder)
        
        if not slide_files:
            print("No supported slide files found!")
            return False
        
        print(f"Found {len(slide_files)} slide files")
        
        # Process first slide for crop selection
        first_slide = slide_files[0]
        print(f"About to process first slide: {os.path.basename(first_slide)}")
        success = self._process_first_slide(first_slide)
        print(f"First slide processing returned: {success}")
        
        if not success:
            print("Failed to process first slide")
            return False
        
        # Note: crop_coords will be None if we used direct label extraction (which is fine!)
        if self.crop_coords is None:
            print("Using direct label extraction - no cropping needed for remaining slides")
        else:
            print(f"Using crop coordinates for remaining slides: {self.crop_coords}")
        
        remaining_slides = slide_files[1:]
        if not remaining_slides:
            print("Only one slide found - processing complete!")
            return True
        
        print(f"Starting to process remaining {len(remaining_slides)} slides in parallel batches of {self.batch_size}...")
        
        # Process remaining slides in parallel batches
        self._process_slides_in_batches(remaining_slides)
        
        print("Label extraction completed!")
        return True
    
    def _process_first_slide(self, slide_file: str) -> bool:
        """Process the first slide with manual crop selection."""
        print(f"Processing first slide: {os.path.basename(slide_file)}")
        
        # Extract label image
        result = self._extract_label_image(slide_file)
        if result is None:
            return False
        
        label_image, is_direct_label = result
        
        if is_direct_label:
            # We have a direct label image - no cropping needed!
            print("Using direct label image - skipping crop selection")
            self.crop_coords = None  # No cropping needed for subsequent slides
            
            # Just rotate and save
            processed_image = self._process_label_image(label_image, apply_crop=False)
            if processed_image is None:
                return False
            
            # Save processed first image
            output_filename = self._get_label_filename(slide_file)
            output_path = os.path.join(self.label_folder, output_filename)
            processed_image.save(output_path, "JPEG", quality=90)
            
            print(f"First slide processed successfully using direct label (no cropping needed)")
            return True
        
        else:
            # We have a whole slide overview - need to crop the label area
            print("Using whole slide overview - crop selection needed")
            
            # Check if crop coordinates are already set (from configuration)
            if self.crop_coords is not None:
                print(f"Using preset crop coordinates: {self.crop_coords}")
            else:
                print("No preset crop coordinates - prompting user for crop selection")
                
                # Save temporary label image for crop selection
                temp_label_path = os.path.join(self.label_folder, "temp_label.jpg")
                label_image.save(temp_label_path)
                
                try:
                    # Get crop selection from user
                    crop_selector = CropSelector(temp_label_path)
                    self.crop_coords = crop_selector.select_crop_region()
                    
                    # If PhotoImage-based crop selector failed, try simple method
                    if self.crop_coords is None:
                        print("PhotoImage crop selector failed, trying simple coordinate method...")
                        from simple_crop import SimpleCropSelector
                        simple_selector = SimpleCropSelector(temp_label_path, label_image.size)
                        self.crop_coords = simple_selector.select_crop_region()
                    
                    # Remove temporary file
                    os.remove(temp_label_path)
                    
                    if self.crop_coords is None:
                        print("Crop selection cancelled")
                        return False
                        
                except Exception as e:
                    print(f"Error during crop selection: {e}")
                    if os.path.exists(temp_label_path):
                        os.remove(temp_label_path)
                    return False
                
            # Now apply crop and rotation to first image (regardless of how we got the crop coords)
            print(f"Proceeding with crop coordinates: {self.crop_coords}")
            print("Applying crop and rotation to first image...")
            
            try:
                processed_image = self._process_label_image(label_image, apply_crop=True)
                if processed_image is None:
                    print("Failed to process label image")
                    return False
                
                print("Processed image successfully")
                
                # Save processed first image
                output_filename = self._get_label_filename(slide_file)
                output_path = os.path.join(self.label_folder, output_filename)
                print(f"Saving processed image to: {output_path}")
                processed_image.save(output_path, "JPEG", quality=90)
                
                print(f"First slide processed successfully. Crop region: {self.crop_coords}")
                return True
                
            except Exception as e:
                print(f"Error processing first slide: {e}")
                return False
    
    def _process_slides_in_batches(self, slide_files: List[str]):
        """Process slides in parallel batches."""
        batch_size = self.batch_size
        total_slides = len(slide_files)
        successful = 0
        failed = 0
        
        # Split slides into batches
        for batch_start in range(0, total_slides, batch_size):
            batch_end = min(batch_start + batch_size, total_slides)
            batch = slide_files[batch_start:batch_end]
            current_batch = batch_start // batch_size + 1
            total_batches = (total_slides + batch_size - 1) // batch_size
            
            print(f"\nProcessing batch {current_batch}/{total_batches} ({len(batch)} slides)...")
            
            # Process this batch in parallel
            batch_results = self._process_batch_parallel(batch)
            
            # Report results for this batch
            batch_successful = sum(1 for _, success, _ in batch_results if success)
            batch_failed = len(batch_results) - batch_successful
            
            successful += batch_successful
            failed += batch_failed
            
            print(f"Batch {current_batch} complete: {batch_successful} successful, {batch_failed} failed")
            
            # Print individual results
            for filename, success, message in batch_results:
                status = "✓" if success else "✗"
                print(f"  {status} {filename}: {message}")
        
        print(f"\nAll batches complete! Total: {successful} successful, {failed} failed")
    
    def _process_batch_parallel(self, batch_slides: List[str]) -> List[Tuple[str, bool, str]]:
        """Process a batch of slides in parallel."""
        # Create partial function with fixed parameters
        process_func = partial(
            process_slide_parallel,
            crop_coords=self.crop_coords,
            label_folder=self.label_folder,
            cannot_open_folder=self.cannot_open_folder
        )
        
        results = []
        
        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=min(len(batch_slides), os.cpu_count() or 1)) as executor:
            # Submit all tasks
            future_to_slide = {
                executor.submit(process_func, slide_file): slide_file 
                for slide_file in batch_slides
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_slide):
                slide_file = future_to_slide[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    filename = os.path.basename(slide_file)
                    results.append((filename, False, f"Exception: {str(e)}"))
        
        return results
    
    def _process_slide(self, slide_file: str, apply_crop: bool = False):
        """Process a single slide file."""
        try:
            # Extract label image
            result = self._extract_label_image(slide_file)
            if result is None:
                return
            
            label_image, is_direct_label = result
            
            # Determine if we need to crop
            # For subsequent slides: use same method as first slide
            # If first slide used direct label (crop_coords is None), don't crop
            # If first slide needed cropping (crop_coords is set), apply cropping
            need_crop = apply_crop and (self.crop_coords is not None)
            
            # Process the image (crop and rotate)
            processed_image = self._process_label_image(label_image, need_crop)
            if processed_image is None:
                return
            
            # Save processed image
            output_filename = self._get_label_filename(slide_file)
            output_path = os.path.join(self.label_folder, output_filename)
            processed_image.save(output_path, "JPEG", quality=90)
            
            method = "direct label" if is_direct_label else "cropped overview"
            print(f"Label extracted ({method}): {output_filename}")
            
        except Exception as e:
            print(f"Error processing {os.path.basename(slide_file)}: {e}")
    
    def _extract_label_image(self, slide_file: str) -> Optional[Tuple[Image.Image, bool]]:
        """Extract label image - try direct label first, then fall back to level 6 overview."""
        try:
            # Try to open slide
            slide = openslide.OpenSlide(slide_file)
            
            print(f"Slide levels available: {slide.level_count}")
            print(f"Level dimensions: {slide.level_dimensions}")
            print(f"Associated images: {list(slide.associated_images.keys())}")
            
            # Method 1: Try to get direct label image (best option!)
            if 'label' in slide.associated_images:
                print("Found direct label image - extracting without cropping needed!")
                label_image = slide.associated_images['label']
                
                # Convert RGBA to RGB if needed
                if label_image.mode == 'RGBA':
                    label_image = label_image.convert('RGB')
                
                slide.close()
                print(f"Successfully extracted direct label image: {label_image.size}")
                return label_image, True  # True means no cropping needed
            
            # Method 2: Check for 'macro' image specifically (needs cropping)
            if 'macro' in slide.associated_images:
                print(f"Found 'macro' image - this contains the full slide and needs cropping")
                label_image = slide.associated_images['macro']
                
                # Convert RGBA to RGB if needed
                if label_image.mode == 'RGBA':
                    label_image = label_image.convert('RGB')
                
                slide.close()
                print(f"Successfully extracted 'macro' image: {label_image.size}")
                return label_image, False  # False means cropping IS needed
            
            # Method 3: Check for other associated images that might be direct labels
            for assoc_name in slide.associated_images.keys():
                if any(keyword in assoc_name.lower() for keyword in ['label', 'overview']) and assoc_name != 'macro':
                    print(f"Found potential direct label image '{assoc_name}' - extracting...")
                    label_image = slide.associated_images[assoc_name]
                    
                    # Convert RGBA to RGB if needed
                    if label_image.mode == 'RGBA':
                        label_image = label_image.convert('RGB')
                    
                    slide.close()
                    print(f"Successfully extracted '{assoc_name}' image: {label_image.size}")
                    return label_image, True  # True means no cropping needed
            
            # Method 4: Fall back to level 6 overview (requires cropping)
            print("No direct label image found - using level 6 overview (will need cropping)")
            target_level = min(6, slide.level_count - 1)
            print(f"Using level {target_level} for whole slide overview")
            
            # Get dimensions for the target level
            level_dims = slide.level_dimensions[target_level]
            print(f"Level {target_level} dimensions: {level_dims}")
            
            # Read the entire level - this contains BOTH tissue and label areas
            whole_image = slide.read_region((0, 0), target_level, level_dims)
            
            # Convert RGBA to RGB if needed
            if whole_image.mode == 'RGBA':
                whole_image = whole_image.convert('RGB')
            
            slide.close()
            print(f"Successfully extracted whole slide overview: {whole_image.size}")
            return whole_image, False  # False means cropping IS needed
            
        except Exception as e:
            print(f"Cannot open slide {os.path.basename(slide_file)}: {e}")
            # Move to cannot_open folder
            try:
                utils.move_file(slide_file, self.cannot_open_folder)
                print(f"Moved to cannot_open folder: {os.path.basename(slide_file)}")
            except Exception as move_error:
                print(f"Error moving file: {move_error}")
            return None
    
    def _process_label_image(self, image: Image.Image, apply_crop: bool) -> Optional[Image.Image]:
        """Process label image (crop and rotate)."""
        try:
            processed = image.copy()
            
            # Apply crop if coordinates are available and requested
            if apply_crop and self.crop_coords:
                x1, y1, x2, y2 = self.crop_coords
                processed = processed.crop((x1, y1, x2, y2))
            
            # Rotate by configured angle
            processed = processed.rotate(config.DEFAULT_ROTATION_ANGLE, expand=True)
            
            return processed
            
        except Exception as e:
            print(f"Error processing label image: {e}")
            return None
    
    def _get_label_filename(self, slide_file: str) -> str:
        """Generate label image filename from slide filename."""
        base_name = os.path.splitext(os.path.basename(slide_file))[0]
        return f"{base_name}.jpg"


def run_phase1(slide_folder: str) -> bool:
    """Run Phase 1: Label Image Extraction."""
    if not os.path.exists(slide_folder):
        print(f"Slide folder does not exist: {slide_folder}")
        return False
    
    extractor = LabelExtractor(slide_folder)
    return extractor.extract_all_labels()


def run_phase1_with_config(slide_folder: str, config_data: dict) -> bool:
    """Run Phase 1: Label Image Extraction with configuration."""
    if not os.path.exists(slide_folder):
        print(f"Slide folder does not exist: {slide_folder}")
        return False
    
    print(f"Running Phase 1 with configuration:")
    print(f"  - Use default crop: {config_data.get('use_default_crop', True)}")
    print(f"  - Batch size: {config_data.get('batch_size', config.DEFAULT_BATCH_SIZE)}")
    
    # Create extractor with configuration
    extractor = LabelExtractor(slide_folder)
    
    # Configure batch size
    if 'batch_size' in config_data:
        extractor.batch_size = config_data['batch_size']
    
    # Configure crop settings
    if config_data.get('use_default_crop', True):
        # Use the default crop coordinates
        extractor.crop_coords = config_data.get('crop_coords', [10, 13, 578, 732])
        print(f"  - Using default crop coordinates: {extractor.crop_coords}")
    else:
        # Let user select crop region manually (existing behavior)
        print("  - Manual crop selection will be prompted")
        extractor.crop_coords = None
    
    return extractor.extract_all_labels()


if __name__ == "__main__":
    # For testing
    import sys
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        run_phase1(folder_path)
    else:
        print("Usage: python label_extractor.py <slide_folder_path>")