# Troubleshooting Crop Selection Issues

## Error: "image 'pyimage1' doesn't exist"

This is a common tkinter/PIL issue that can occur when working with images in GUI applications. Here are the fixes I've implemented and additional troubleshooting steps:

### What I Fixed

1. **Image Reference Management**: Added `self.canvas.image = self.photo` to prevent garbage collection
2. **GUI Initialization**: Added `self.root.update_idletasks()` before creating images
3. **Error Handling**: Added try-catch blocks with fallback image creation
4. **Window Management**: Made the crop window stay on top and focused

### Testing Your Setup

To verify your setup works, try running the main application:

```bash
python main.py
```

This will test basic functionality when you select Phase 1.

### If Issues Persist

#### Option 1: Try Different Python Environment
```bash
# Create a new virtual environment
python -m venv crop_env
# Activate it (Windows)
crop_env\Scripts\activate
# Activate it (Mac/Linux)  
source crop_env/bin/activate
# Install dependencies
pip install -r requirements.txt
```

#### Option 2: Manual tkinter Installation (Linux)
```bash
sudo apt-get install python3-tk
sudo apt-get install python3-pil.imagetk
```

#### Option 3: Alternative Image Library
If PIL ImageTk continues to have issues, you can modify the code to use OpenCV instead:

```python
import cv2
import numpy as np

# Instead of PIL ImageTk, use OpenCV with tkinter
def cv_to_tkinter(cv_image):
    height, width, channels = cv_image.shape
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    from PIL import Image, ImageTk
    image = Image.fromarray(cv_image)
    return ImageTk.PhotoImage(image)
```

#### Option 4: Check Display Settings (Linux)
```bash
# Make sure DISPLAY is set correctly
echo $DISPLAY
# If empty or wrong, set it:
export DISPLAY=:0.0
```

### System-Specific Solutions

#### Windows
- Make sure you have the latest Python from python.org
- Try running as administrator if permission issues
- Check Windows display scaling settings

#### macOS  
- Install Python from python.org (not just command line tools)
- If using Homebrew Python, install tkinter separately:
  ```bash
  brew install python-tk
  ```

#### Linux
- Install required packages:
  ```bash
  sudo apt-get install python3-tk python3-pil python3-pil.imagetk
  # Or for other distros:
  sudo dnf install tkinter python3-pillow-tk
  ```

### Alternative Crop Selection Methods

If the GUI crop selector continues to have issues, you can:

1. **Use Command Line Coordinates**: Modify the code to accept crop coordinates as parameters
2. **Use a Different GUI Library**: Replace tkinter with PyQt5/6 
3. **Use Image Viewer**: Open the label in an external viewer and manually note coordinates

### Debugging Steps

1. **Check Image File**: Make sure the temporary label image is being created correctly
2. **Test Simple Tkinter**: Run a basic tkinter window test
3. **Check PIL Version**: Ensure Pillow is up to date
4. **Try Different Image Formats**: Test with PNG instead of JPEG

### Getting More Debug Info

Enable verbose debugging by modifying the crop selector call:

```python
# In label_extractor.py, add more debug output
print(f"Python version: {sys.version}")
print(f"Tkinter version: {tk.TkVersion}")
print(f"PIL version: {Image.__version__}")
```

### Last Resort Solutions

1. **Skip Crop Selection**: Modify the code to use the entire label image without cropping
2. **Pre-crop Images**: Manually crop the first image and use those dimensions
3. **Use Different Computer**: Test on a different system to isolate the issue

### Contact Support

If none of these solutions work, please provide:
- Operating system and version
- Python version (`python --version`)
- Error traceback from running `python test_crop.py`
- Output from the debug commands above

The crop selection is a critical part of Phase 1, but the application can be modified to work around this issue if needed.