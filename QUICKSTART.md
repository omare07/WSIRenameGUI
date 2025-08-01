# Quick Start Guide - Histology Slide Renaming Tool

## Crop Selection Issues? Start Here!

If you're getting "image 'pyimage1' doesn't exist" errors, this guide will help you get started quickly.

### Option 1: Use the Smart Launcher (Recommended)

```bash
python launch_phase1.py
```

This launcher will:
- Test your system for PhotoImage compatibility
- Automatically choose the best crop selection method
- Provide a fallback coordinate-based method if needed

### Option 2: Use Coordinate-Based Crop Selection

```bash
python simple_crop.py
```

Test the coordinate-based crop selector directly. This method always works and lets you:
- Enter crop coordinates manually
- Use preset crop regions (center 50%, top half, etc.)
- See the exact image dimensions

### Option 3: Standard Method (If PhotoImage Works)

```bash
python main.py
```

Use the standard application with visual crop selection.

## Step-by-Step Instructions

### Phase 1: Extract Label Images

1. **Test your slides first** (recommended):
   ```bash
   python test_smart_extraction.py /path/to/your/slides
   ```
   This shows you which slides have direct labels vs. need cropping.

2. **Choose your method based on your system:**
   - **Anaconda Python**: Use `python launch_phase1.py`
   - **System Python**: Try `python main.py` first
   - **Any issues**: Use `python launch_phase1.py`

3. **Select your slide folder** containing .ndpi, .svs, .scn files

4. **Automatic processing**:
   - **If slides have direct label images**: **Instant processing** - no user interaction needed!
   - **If slides need cropping**: You'll choose crop region once (applied to all slides)
     - **Visual method**: Click and drag on the displayed image
     - **Coordinate method**: Enter pixel coordinates (recommended for most users)

5. **Wait for processing** to complete

### Phase 2: Rename Files

```bash
python main.py --phase2
```

Then follow the GUI to review and rename files.

## Troubleshooting Common Issues

### "image 'pyimage1' doesn't exist"

**This is a common issue with certain Python installations. Solutions:**

1. **Use the smart launcher:**
   ```bash
   python launch_phase1.py
   ```

2. **Use coordinate-based crop selection:**
   - Will prompt you to enter crop coordinates
   - Shows image dimensions to help you choose
   - Provides preset options (center 50%, top half, etc.)

### Example Coordinate Selection

If your label image is 1000x800 pixels:
- **Center 50% crop**: X1=250, Y1=200, X2=750, Y2=600
- **Top half**: X1=0, Y1=0, X2=1000, Y2=400
- **Custom region**: Enter any coordinates within 0-1000 for X, 0-800 for Y

### No Supported Files Found

Make sure your folder contains:
- .ndpi files
- .svs files  
- .scn files
- Other OpenSlide-supported formats

### OpenSlide Errors

1. **Install OpenSlide system library:**
   - Windows: Download from [OpenSlide.org](https://openslide.org/download/)
   - macOS: `brew install openslide`
   - Linux: `sudo apt-get install openslide-tools`

2. **Then install Python package:**
   ```bash
   pip install openslide-python
   ```

## Recommended Workflow

### For Most Users (Especially Anaconda):

```bash
# 1. Test system compatibility
python test_setup.py

# 2. Extract labels with smart method selection
python launch_phase1.py

# 3. Review and rename
python main.py --phase2
```

### For System Python Users:

```bash
# 1. Try standard method
python main.py

# 2. If crop selection fails, use:
python launch_phase1.py
```

## Expected Output Structure

After Phase 1:
```
your_slide_folder/
├── slide1.ndpi
├── slide2.ndpi
├── label_image/
│   ├── slide1.jpg
│   └── slide2.jpg
└── cannot_open/
    └── corrupted_slide.ndpi
```

## Pro Tips

1. **Test First**: Run `python test_crop.py` to verify crop selection works
2. **Backup Files**: Keep copies of original slides before renaming
3. **Coordinate Method**: When in doubt, use coordinate-based crop selection
4. **Image Size**: Note the label image dimensions shown in the console
5. **Presets**: Use preset crop regions if you're unsure about coordinates

## Command Reference

| Command | Purpose |
|---------|---------|
| `python launch_phase1.py` | Smart Phase 1 launcher with compatibility detection |
| `python main.py` | Standard application |
| `python main.py --phase1 /path/to/slides` | Direct Phase 1 |
| `python main.py --phase2` | Direct Phase 2 |
| `python test_setup.py` | Test installation |
| `python test_crop.py` | Test crop selection |
| `python simple_crop.py` | Test coordinate method |

## Still Having Issues?

1. **Check your Python version**: `python --version`
2. **Verify dependencies**: `python test_setup.py`
3. **Try the coordinate method**: `python simple_crop.py`
4. **Check console output**: Look for detailed error messages
5. **Use the troubleshooting guide**: See `troubleshoot_crop.md`

## Quick Help

**Error**: "image 'pyimage1' doesn't exist"  
**Solution**: Use `python launch_phase1.py`

**Error**: "No module named 'openslide'"  
**Solution**: Install OpenSlide system library first

**Error**: "No supported files found"  
**Solution**: Check file extensions and folder path

**Error**: GUI doesn't appear  
**Solution**: Install tkinter: `sudo apt-get install python3-tk` (Linux)

---

**Success**: After Phase 1 completes, you'll have cropped and rotated label images ready for Phase 2 renaming!