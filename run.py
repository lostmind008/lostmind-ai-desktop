#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Run Script for LostMind AI Gemini Chat Assistant

Simple script to launch the application from the root directory.
Handles Python path and invokes the main entry point.
"""

import os
import sys
from pathlib import Path

def run_application():
    """Set up the environment and run the application."""
    # Get the absolute path of the script directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Add the script directory to Python path
    sys.path.insert(0, str(script_dir))
    
    # Add the src directory to Python path
    src_dir = script_dir / "src"
    sys.path.insert(0, str(src_dir))
    
    # Import and run the main function
    from src.main import main
    
    # Check if any command-line arguments should be passed to main
    return main()

if __name__ == "__main__":
    sys.exit(run_application())
