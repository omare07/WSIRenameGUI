"""Utility functions for the histology slide renaming application."""

import os
import shutil
import csv
from typing import List, Tuple, Optional
from pathlib import Path
import config

def create_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def get_slide_files(folder_path: str) -> List[str]:
    """Get all supported slide files from the folder."""
    slide_files = []
    for file in os.listdir(folder_path):
        if any(file.lower().endswith(ext) for ext in config.SUPPORTED_EXTENSIONS):
            slide_files.append(os.path.join(folder_path, file))
    return sorted(slide_files)

def move_file(src: str, dst_folder: str) -> str:
    """Move file to destination folder, creating folder if needed."""
    create_directory(dst_folder)
    filename = os.path.basename(src)
    dst_path = os.path.join(dst_folder, filename)
    shutil.move(src, dst_path)
    return dst_path

def generate_new_filename(prefix: str, identifier: str, extension: str) -> str:
    """Generate new filename with format: prefix_identifier.extension"""
    # Parse identifier (e.g., "002 001", "002001", or just "285")
    identifier = identifier.strip()
    
    # Check if input contains spaces
    if ' ' in identifier:
        # Multiple numbers with spaces: "002 001" -> "002_001"
        parts = identifier.split()
        digits_parts = [''.join(filter(str.isdigit, part)).zfill(3) for part in parts if ''.join(filter(str.isdigit, part))]
        formatted_id = '_'.join(digits_parts)
    else:
        # Single string of digits
        digits_only = ''.join(filter(str.isdigit, identifier))
        if not digits_only:
            raise ValueError("Identifier must contain at least one digit")
        
        # If 6 or more digits, split into groups of 3
        if len(digits_only) >= 6:
            # "002001" -> "002_001"
            groups = []
            for i in range(0, len(digits_only), 3):
                groups.append(digits_only[i:i+3])
            formatted_id = '_'.join(groups)
        else:
            # Less than 6 digits: "285" -> "285" (keep as single number)
            formatted_id = digits_only
    
    return f"{prefix}{formatted_id}{extension}"

def check_duplicate_filename(filepath: str) -> str:
    """Check if file exists and append suffix if needed."""
    if not os.path.exists(filepath):
        return filepath
    
    base, ext = os.path.splitext(filepath)
    counter = 1
    new_filepath = f"{base}{config.DUPLICATE_SUFFIX}{ext}"
    
    while os.path.exists(new_filepath):
        counter += 1
        new_filepath = f"{base}{config.DUPLICATE_SUFFIX}{counter}{ext}"
    
    return new_filepath

def save_renaming_log(renaming_data: List[Tuple[str, str]], log_path: str) -> None:
    """Save renaming actions to CSV log."""
    with open(log_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Original_File', 'New_File', 'Timestamp'])
        
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for original, new in renaming_data:
            writer.writerow([original, new, timestamp])

def should_skip_file(filename: str) -> bool:
    """Check if file should be skipped based on prefix rules."""
    basename = os.path.basename(filename)
    return any(basename.startswith(prefix) for prefix in config.SKIP_PREFIXES)