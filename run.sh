#!/bin/bash
# Make this script executable with: chmod +x run.sh

# Run Script for LostMind AI Gemini Chat Assistant
# This script sets up environment variables and runs the application

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3.9 or newer."
    exit 1
fi

# Check for virtual environment
if [ -d "venv" ]; then
    echo "Using virtual environment..."
    source venv/bin/activate
fi

# Check if requirements are installed
if ! python3 -c "import PyQt6" &> /dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the application
echo "Starting LostMind AI Gemini Chat Assistant..."
python3 run.py "$@"
