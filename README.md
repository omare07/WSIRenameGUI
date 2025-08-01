# Histology Slide Renaming Tool

A comprehensive Python application for histology slide review and systematic file renaming. This tool streamlines the workflow of processing whole-slide images by extracting label images and providing an intuitive GUI for renaming based on visual review.

## Features

### Phase 1: Label Image Extraction
- **Multi-format Support**: Works with .svs, .ndpi, .scn, .vms, .vmu, .mrxs files
- **Automatic Label Extraction**: Uses OpenSlide to extract label images from slides
- **Manual Crop Selection**: Interactive GUI for selecting region of interest on first image
- **Batch Processing**: Applies same crop to all slides automatically
- **Image Processing**: Rotates labels by 270° for optimal viewing
- **Error Handling**: Moves unreadable slides to separate folder

### Phase 2: GUI-Based Renaming
- **Visual Review**: Display label images with easy navigation
- **Smart Renaming**: Input numeric identifiers with automatic formatting
- **Preview System**: See new filenames before applying changes
- **Duplicate Handling**: Automatic suffix addition for duplicate names
- **Batch Operations**: Rename all files at once with progress tracking
- **Session Management**: Save and load renaming sessions
- **Comprehensive Logging**: CSV logs of all renaming actions

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

### Quick Start
```bash
# Run the complete application with GUI selector
python main.py

# Or run specific phases
python main.py --phase1 /path/to/slides    # Extract labels only
python main.py --phase2                     # Renaming GUI only
```

### Detailed Workflow

#### Step 1: Prepare Your Slides
- Place all slide files (.svs, .ndpi, .scn, etc.) in a single folder
- Ensure files are accessible and not corrupted

#### Step 2: Extract Label Images (Phase 1)
1. Run the application and select "Phase 1: Extract Labels"
2. Choose your slide folder
3. The first slide will open for crop selection:
   - Click and drag to select the region of interest
   - This region will be applied to all slides
   - Click "Confirm Crop" to proceed
4. Wait for processing to complete

**Output Structure:**
```
[Your Slide Folder]/
├── slide1.ndpi
├── slide2.ndpi
├── label_image/
│   ├── slide1.jpg
│   └── slide2.jpg
└── cannot_open/
    └── corrupted_slide.ndpi
```

#### Step 3: Review and Rename (Phase 2)
1. Run "Phase 2: Rename Files" or continue from Phase 1
2. Configure settings:
   - **Slide Folder**: Folder containing original slides
   - **Output Folder**: Where renamed files will be moved
   - **Prefix**: Text prefix for new names (e.g., "KPC12-1_")
   - **Extension**: File extension (.ndpi, .svs, etc.)
3. Load images and navigate through labels
4. For each image:
   - Enter numeric identifier (e.g., "002 001" or "002001")
   - Preview the new filename
   - Click "Apply to Current" or press Enter
5. Review summary and click "Rename All Files"

### Example Renaming
- **Input**: `002 001` or `002001`
- **Output**: `KPC12-1_002_001.ndpi`
- **Duplicate**: `KPC12-1_002_001_b.ndpi`

## Configuration

### Default Settings (config.py)
```python
DEFAULT_PREFIX = "KPC12-1_"          # Default filename prefix
DEFAULT_LABEL_LEVEL = 6              # OpenSlide level for label extraction
DEFAULT_ROTATION_ANGLE = 270         # Rotation angle for labels
SKIP_PREFIXES = ['.', 'T']          # Skip files starting with these
```

### Customization
- Modify `config.py` to change default settings
- GUI allows runtime configuration of most settings
- Session files store user preferences

## File Structure

```
histology-renaming-tool/
├── main.py                 # Main application entry point
├── config.py              # Configuration settings
├── utils.py               # Utility functions
├── label_extractor.py     # Phase 1: Label extraction
├── renaming_gui.py        # Phase 2: Renaming GUI
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Advanced Usage

### Command Line Options
```bash
# Run GUI selector (default)
python main.py
python main.py --gui

# Extract labels from specific folder
python main.py --phase1 "/path/to/slide/folder"

# Open renaming GUI directly
python main.py --phase2

# Run complete workflow
python main.py  # Then select "Run Complete Workflow"
```

### Session Management
- **Save Session**: Stores current renaming mappings to JSON file
- **Load Session**: Restores previous session state
- **Auto-Resume**: GUI remembers applied renames during session

### Batch Processing Tips
1. **Organize Slides**: Group related slides in folders
2. **Consistent Naming**: Use systematic numeric identifiers
3. **Preview Before Rename**: Always review the summary
4. **Backup Originals**: Keep copies of original files
5. **Check Logs**: Review CSV logs for audit trails

## Troubleshooting

### Common Issues

**OpenSlide Import Error**
```
Solution: Install OpenSlide system library first, then python package
Windows: Download from openslide.org
macOS: brew install openslide
Linux: sudo apt-get install openslide-tools
```

**Cannot Open Slide Files**
```
Solution: Check file permissions and format support
Supported: .svs, .ndpi, .scn, .vms, .vmu, .mrxs
Files moved to cannot_open/ folder automatically
```

**GUI Not Responding**
```
Solution: Ensure tkinter is installed
Usually included with Python, but may need separate install on Linux
sudo apt-get install python3-tk
```

**Label Extraction Fails**
```
Solution: Try different label extraction level
Modify DEFAULT_LABEL_LEVEL in config.py
Common values: 4, 5, 6, 7
```

### Performance Tips
- **Large Datasets**: Process in smaller batches
- **Memory Usage**: Close other applications during processing
- **Storage Space**: Ensure adequate disk space for output
- **Network Drives**: Copy files locally for better performance

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
- **Duplicates**: Automatic suffix handling

### Log Files
- **Filename**: `renaming_log.csv`
- **Contents**: Original file, new file, timestamp
- **Location**: Output folder
- **Format**: CSV for easy analysis

### Session Files
- **Format**: JSON
- **Contents**: Folder paths, settings, rename mappings
- **Usage**: Resume interrupted sessions

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

**Version**: 1.0  
**Author**: Histology Tools Development Team  
**Last Updated**: 2024