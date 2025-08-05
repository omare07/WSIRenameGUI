# Label Cropping Workflow Explained

## Understanding the Crop Selection Process

### What You'll See vs. What You Need to Crop

**What the application shows you:**
- The **entire slide overview** from level 6 (like your MATLAB code)
- This contains BOTH the tissue area AND the label area
- The tissue area is typically large and central
- The label area is typically smaller and positioned separately (often in a corner)

**What you need to crop:**
- ONLY the **label portion** from this overview
- This is the small area that contains the slide label/barcode/text
- NOT the tissue area (which is what you were seeing before)

### Visual Example

```
┌─────────────────────────────────────────┐
│ ┌─────────────┐                        │  <- Whole slide overview (level 6)
│ │  SLIDE-001  │    ┌─────────────────┐ │
│ │  2024-01-15 │    │                 │ │  
│ │  KPC12-1    │    │   TISSUE AREA   │ │  <- Large tissue area (don't crop this)
│ └─────────────┘    │    (large)      │ │
│  ^                 │                 │ │
│  │                 └─────────────────┘ │
│  └─ LABEL AREA                         │
│     (crop this!)                       │
└─────────────────────────────────────────┘
```

### How This Matches Your MATLAB Code

Your MATLAB code:
```matlab
imlabel=imread([pth,imlist(k).name],6);  % Reads whole slide overview
[imlabel,rr] = imcrop(imlabel);          % Crops LABEL from overview
```

My updated Python code:
```python
# Read level 6 (whole slide overview) - same as MATLAB
whole_image = slide.read_region((0, 0), target_level, level_dims)

# Then crop the LABEL AREA from this overview - same as MATLAB imcrop
```

### Crop Selection Methods

**1. Visual Method (if PhotoImage works):**
- You'll see the whole slide overview
- Click and drag to select ONLY the label area
- Ignore the large tissue area

**2. Coordinate Method (PhotoImage backup):**
- Enter pixel coordinates for the label area
- Use preset buttons for common label positions:
  - Top-Left Corner (most common)
  - Top-Right Corner  
  - Bottom-Left Corner
  - Bottom-Right Corner

### Typical Label Dimensions

For a slide overview of 1000x800 pixels:
- **Label area**: Usually around 200x200 to 300x300 pixels
- **Position**: Often in corners or edges
- **Content**: Slide ID, date, barcode, study info

### Example Coordinates

If your overview is 990x540 pixels (like you mentioned):
- **Top-left label**: X1=0, Y1=0, X2=248, Y2=135
- **Top-right label**: X1=742, Y1=0, X2=990, Y2=135  
- **Bottom-left label**: X1=0, Y1=405, X2=248, Y2=540
- **Custom position**: Any coordinates that capture just the label

### Why This Change Was Needed

**Before (incorrect):**
- Was trying to extract pre-separated label images
- Only showed tissue area without label
- Didn't match your MATLAB workflow

**Now (correct):**
- Reads whole slide overview (level 6) like MATLAB
- Shows both tissue AND label areas
- Lets you crop the label portion like MATLAB imcrop
- Applies same crop to all slides in batch

This now exactly matches your MATLAB workflow: read the whole overview, crop the label area, rotate, and save!