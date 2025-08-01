"""Configuration settings for the histology slide renaming application."""

import os
from typing import List, Tuple

# Supported slide file extensions
SUPPORTED_EXTENSIONS = ['.svs', '.ndpi', '.scn', '.vms', '.vmu', '.mrxs']

# Default settings
DEFAULT_PREFIX = "KPC12-1_"
DEFAULT_LABEL_LEVEL = 6
DEFAULT_ROTATION_ANGLE = 270

# Folder names
LABEL_FOLDER = "label_image"
CANNOT_OPEN_FOLDER = "cannot_open"

# GUI settings
WINDOW_SIZE = (800, 600)
IMAGE_DISPLAY_SIZE = (400, 300)

# File naming
DUPLICATE_SUFFIX = "_b"
LOG_FILENAME = "renaming_log.csv"

# Skip files starting with these characters
SKIP_PREFIXES = ['.', 'T']