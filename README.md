# Histology Slide Renaming Tool

A comprehensive Python application for histology slide review and systematic file renaming. This tool streamlines the workflow of processing whole-slide images by extracting label images and providing an intuitive GUI for renaming based on visual review. Features intelligent auto-detection, setup-guided workflow, and advanced performance optimizations.

## Features

### Setup-Guided Workflow (NEW in v2.0!)
- **Interactive Setup Screen**: Comprehensive configuration before processing begins
- **Crop Preset Selection**: Choose default crop coordinates or manual selection
- **Slide Naming Configuration**: Define amount per slide and skip factor for systematic naming
- **Batch Size Customization**: Optimize processing speed for your system
- **Runtime Adjustments**: Modify naming configuration during Phase 2 processing

### Intelligent Auto-Detection
- **Automatic Phase Selection**: Automatically determines whether to run Phase 1 or Phase 2
- **1:1 Correspondence Check**: Verifies exact file matching between WSI and label images
- **Smart Workflow**: Seamlessly transitions from Phase 1 to Phase 2 when needed
- **Resume Capability**: Skip Phase 1 if perfect correspondence already exists

### Phase 1: Label Image Extraction
- **Multi-format Support**: Works with .svs, .ndpi, .scn, .vms, .vmu, .mrxs files
- **Automatic Label Extraction**: Uses OpenSlide to extract label images from slides
- **Smart Crop Selection**: Use preset coordinates or interactive GUI selection
- **Parallel Processing**: Configurable batch processing for optimal performance
- **Batch Processing**: Applies same crop to all slides automatically
- **Image Processing**: Rotates labels by 270° for optimal viewing
- **Error Handling**: Moves unreadable slides to separate folder

### Phase 2: Advanced GUI-Based Renaming (ENHANCED in v2.0!)
- **Split-Pane Interface**: Simultaneous image viewing and data table management
- **Dynamic CSV Table**: Real-time table showing Index, Label Image, Identifier, New Filename, and Status
- **Interactive Navigation**: Click table rows to jump to specific images
- **Enhanced Keyboard Controls**: Left/Right arrow keys for navigation with focus-aware input
- **Dual File Renaming**: Automatically renames both WSI files and corresponding JPEG labels
- **Smart Auto-Population**: Intelligent sequence generation with configurable skip patterns
- **Edit Persistence**: User edits preserved and propagated intelligently
- **Non-Destructive Editing**: Changes only affect proceeding files within defined buffers
- **Performance Optimized**: Cached operations and throttled updates for smooth operation

### Advanced Renaming Logic (NEW in v2.0!)
- **Combined Identifiers**: Generate compound names (e.g., "001_002") for multiple slides per specimen
- **Smart Continuation**: Adjust numbering sequence based on user edits
- **Skip Factor Implementation**: Configurable numerical gaps in sequence (skip 003, use 004_005)
- **Buffer-Based Updates**: Intelligent propagation prevents destructive overwrites
- **Explicit vs Auto-Populated**: Track user intentions to preserve manual edits

## Requirements

### System Requirements
- Python 3.7 or higher
- Windows, macOS, or Linux

### Dependencies
```bash
pip install openslide-python pillow pandas numpy opencv-python
```

### Additional System Requirements
- **OpenSlide Library**: Must be installed separately
  - **Windows**: Download from [OpenSlide Downloads](https://openslide.org/download/)
  - **macOS**: `brew install openslide`
  - **Linux**: `sudo apt-get install openslide-tools python3-openslide`

## Installation

1. **Clone or download** this repository
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install OpenSlide** for your operating system (see requirements above)

## Usage

### Quick Start (Setup-Guided Workflow - RECOMMENDED)
```bash
# Run setup-guided workflow (NEW default behavior)
python main.py

# Setup-guided workflow for specific folder
python main.py /path/to/slides

# Advanced users - manual options
python main.py --phase1 /path/to/slides    # Extract labels only
python main.py --phase2                     # Renaming GUI only
python main.py --gui                        # GUI selector
```

### Setup-Guided Workflow

#### Step 1: Initial Configuration
1. Run `python main.py` to launch the setup screen
2. Configure your processing parameters:
   - **Crop Preset**: Choose default crop (10, 13, 578, 732) or manual selection
   - **Slide Naming Order**: 
     - Amount per slide (e.g., 2 for combined naming like "001_002")
     - Skip factor (e.g., 1 to skip numerical values: 001_002, skip 003, then 004_005)
   - **Batch Size**: Processing batch size (default: 12)
3. Click "Start Processing" to begin

#### Step 2: Automatic Processing
- The application automatically detects what needs to be done:
  - **No label images or incomplete set**: Runs Phase 1 then Phase 2
  - **Perfect 1:1 correspondence exists**: Runs Phase 2 directly
- Phase 1 (if needed): Uses your crop preset for efficient batch processing
- Phase 2: Launches with your naming configuration pre-loaded

#### Step 3: Advanced Renaming Interface
1. **Split-Pane Interface**: View images on left, manage data table on right
2. **Navigation Options**:
   - Use Previous/Next buttons
   - Click table rows to jump to specific images
   - Use Left/Right arrow keys for keyboard navigation
3. **Smart Auto-Population**: Numbers auto-populate based on your configuration
4. **Manual Overrides**: Edit any identifier - sequence intelligently adjusts
5. **Real-Time Updates**: Table updates immediately to reflect changes
6. **Runtime Configuration**: Adjust "Amount per slide" and "Skip factor" as needed

### Example Naming Sequences
With **Amount per slide: 2** and **Skip factor: 1**:
- File 1: `KPC12-1_001_002.ndpi`
- File 2: `KPC12-1_004_005.ndpi` (skipped 003)
- File 3: `KPC12-1_006_007.ndpi`

With **Amount per slide: 1** and **Skip factor: 2**:
- File 1: `KPC12-1_001.ndpi`
- File 2: `KPC12-1_004.ndpi` (skipped 002, 003)
- File 3: `KPC12-1_007.ndpi` (skipped 005, 006)

### Advanced Features

#### Dual File Renaming
When renaming `slide001.ndpi` to `KPC12-1_001_002.ndpi`:
- **WSI File**: `slide001.ndpi` → `KPC12-1_001_002.ndpi`
- **Label File**: `slide001.jpg` → `KPC12-1_001_002.jpg`
- **Graceful Handling**: Missing label files generate warnings but don't fail the process

#### Smart Sequence Adjustment
- **User Edit**: Change `015_016` to `031_032`
- **Auto-Continuation**: Next file becomes `034_035`
- **Intelligent Propagation**: Updates all subsequent non-edited files
- **Boundary Respect**: Stops at explicitly renamed files to prevent overwrites

#### Performance Optimizations
- **Cached File Operations**: Instant lookups for repeated operations
- **Selective Table Updates**: Only update changed rows for smooth performance
- **Throttled Refreshes**: Batch GUI updates to prevent blocking
- **Pre-built Mappings**: Build file relationships upfront for faster navigation

## Configuration

### Default Settings (config.py)
```python
DEFAULT_PREFIX = "KPC12-1_"          # Default filename prefix
DEFAULT_LABEL_LEVEL = 6              # OpenSlide level for label extraction
DEFAULT_ROTATION_ANGLE = 270         # Rotation angle for labels
DEFAULT_BATCH_SIZE = 12              # Parallel processing batch size
SKIP_PREFIXES = ['.', 'T']          # Skip files starting with these
DEFAULT_CROP_COORDS = (10, 13, 578, 732)  # Default crop coordinates
```

### Workflow Configuration (workflow_config.json)
Generated automatically by setup screen:
```json
{
  "use_default_crop": true,
  "crop_coords": [10, 13, 578, 732],
  "amount_per_slide": 2,
  "skip_factor": 1,
  "batch_size": 12
}
```

## File Structure

```
histology-renaming-tool/
├── main.py                 # Main application entry point
├── config.py              # Configuration settings
├── utils.py               # Utility functions
├── label_extractor.py     # Phase 1: Label extraction
├── renaming_gui.py        # Phase 2: Advanced renaming GUI
├── setup_screen.py        # Setup-guided workflow interface
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Advanced Usage

### Command Line Options
```bash
# Setup-guided workflow (default, recommended)
python main.py
python main.py /path/to/slides

# Manual phase selection
python main.py --gui                        # GUI selector
python main.py --phase1 /path/to/slides    # Extract labels only
python main.py --phase2                     # Renaming GUI only
```

### Session Management
- **Save Session**: Stores current renaming mappings to JSON file
- **Load Session**: Restores previous session state
- **Auto-Resume**: GUI remembers applied renames during session
- **Configuration Persistence**: Setup preferences saved in workflow_config.json

### Keyboard Shortcuts
- **Left/Right Arrows**: Navigate between images (when not in text fields)
- **Enter**: Apply current rename and advance to next image
- **Tab**: Move between interface elements
- **Click Table Rows**: Jump to specific image

## Troubleshooting

### Common Issues

**OpenSlide Import Error**
```
Solution: Install OpenSlide system library first, then python package
Windows: Download from openslide.org
macOS: brew install openslide
Linux: sudo apt-get install openslide-tools
```

**Performance Issues**
```
Solution: Adjust batch size and table buffer in configuration
- Reduce batch_size for limited memory systems
- Increase table_buffer_size for smoother navigation
- Use local storage instead of network drives
```

**GUI Responsiveness**
```
Solution: Performance optimizations implemented in v2.0
- Cached file operations reduce repeated disk access
- Throttled table updates prevent GUI blocking
- Selective row updates improve responsiveness
```

**Naming Sequence Issues**
```
Solution: Check configuration parameters
- Verify amount_per_slide matches your requirements
- Ensure skip_factor represents numerical gaps, not file gaps
- Use setup screen to test naming preview before processing
```

### Performance Tips
- **Local Storage**: Copy files locally for optimal performance
- **Batch Size**: Adjust based on CPU cores and available memory
- **Table Buffer**: Increase for smoother navigation with large datasets
- **SSD Storage**: Use solid-state drives for significantly faster processing
- **Memory**: Ensure adequate RAM for your dataset size

## Output Files

### Label Images
- **Format**: JPEG with 90% quality
- **Location**: `label_image/` subfolder
- **Naming**: Same as original slide with .jpg extension
- **Processing**: Cropped and rotated as specified

### Renamed Slides
- **Location**: User-specified output folder
- **Format**: Original format preserved
- **Naming**: `[prefix][identifier][extension]`
- **Dual Renaming**: Both WSI and corresponding JPEG files renamed

### Log Files
- **Filename**: `renaming_log.csv`
- **Contents**: Original file, new file, timestamp, label file
- **Location**: Output folder
- **Format**: CSV for easy analysis

### Configuration Files
- **workflow_config.json**: Setup screen preferences
- **Session files**: JSON format for resume capability

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **OpenSlide** project for slide reading capabilities
- **Pillow** for image processing
- **tkinter** for GUI framework
- Histology community for workflow insights

## Support

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed description
4. Include error messages and system information

---

**Version**: 2.0  
**Author**: Histology Tools Development Team  
**Last Updated**: 2024

## What's New in Version 2.0

### Major New Features
- **Setup-Guided Workflow**: Interactive configuration screen before processing
- **Split-Pane Interface**: Simultaneous image viewing and table management
- **Dynamic CSV Table**: Real-time data table with Index, Label Image, Identifier, New Filename, and Status
- **Interactive Navigation**: Click table rows to jump to images, enhanced keyboard controls
- **Dual File Renaming**: Automatic renaming of both WSI and JPEG label files
- **Advanced Naming Logic**: Combined identifiers, skip factors, and smart sequence continuation

### Enhanced Performance
- **Cached Operations**: File system lookups, identifier extraction, and slide path mapping
- **Selective Updates**: Only update changed table rows for improved responsiveness
- **Throttled Refreshes**: Batch GUI updates to prevent interface blocking
- **Optimized Navigation**: Pre-built file mappings for instant access

### Improved User Experience
- **Setup Screen**: Configure crop presets, naming patterns, and batch sizes before processing
- **Smart Auto-Population**: Automatic identifier generation with intelligent sequence management
- **Edit Persistence**: User changes preserved and intelligently propagated
- **Non-Destructive Editing**: Changes only affect subsequent files within defined parameters
- **Enhanced 1:1 Correspondence**: Perfect file matching verification for Phase 1 skip logic

### Technical Improvements
- **Buffer-Based Logic**: Intelligent change propagation without destructive overwrites
- **Focus-Aware Navigation**: Arrow key navigation respects text input fields
- **Error Handling**: Comprehensive exception handling with graceful degradation
- **Configuration Management**: Persistent settings storage and runtime adjustability