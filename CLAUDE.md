# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the LostMindAI Desktop application repository.

## Build and Run Commands

### Main Application
- Run the application: `python V2/PyQt6_Gemini_App/src/main.py`
- Run with debug mode: `python V2/PyQt6_Gemini_App/src/main.py --debug`
- Run with custom config: `python V2/PyQt6_Gemini_App/src/main.py --config /path/to/config.json`

### Development Setup
- Install dependencies: `pip install -r V2/PyQt6_Gemini_App/requirements.txt`
- Set up Google Cloud authentication (one of):
  - Set environment variables: `export GOOGLE_CLOUD_PROJECT=your-project-id GOOGLE_CLOUD_LOCATION=us-central1`
  - Use Application Default Credentials: `gcloud auth application-default login`
  - Use service account key: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json`

### Convenience Scripts
- Windows: `V2/PyQt6_Gemini_App/run.bat`
- Unix/Linux/macOS: `bash V2/PyQt6_Gemini_App/run.sh`

## Architecture Overview

### Core Components
- **ConfigManager** (`src/config_manager.py`): Centralized configuration management using JSON-based settings
- **ModelRegistry** (`src/model_registry.py`): Model discovery and capability management for Gemini models
- **GeminiAssistant** (`src/gemini_assistant.py`): Core Gemini API integration with Vertex AI
- **MainWindow** (`src/ui/main_window.py`): Main PyQt6 application window with tabbed interface

### UI Structure
- Modular UI components in `src/ui/` directory
- `ChatDisplay`: Markdown-rendered chat interface with syntax highlighting
- `ControlsPanel`: Message input with file upload and settings
- `FilePanel`: File attachment management with validation
- `SettingsPanel`: Configuration editor with real-time validation
- `StatusBar`: Application status and progress indicators

### Configuration System
- JSON-based configuration in `config/config.json`
- Supports authentication, model settings, UI preferences, and feature toggles
- Environment variable overrides supported
- Settings persist between sessions

### Authentication Patterns
- Uses Vertex AI with proper `aiplatform.init()` initialization
- Supports multiple authentication methods (service account, ADC, environment variables)
- Graceful fallback when authentication is missing

## Key Implementation Details

### Model Management
- Distinguishes between base and tuned models
- Handles Gemini 2.0 search grounding capabilities
- Robust fallback mechanisms for model discovery failures
- Dynamic capability detection based on model versions

### File Handling
- Supports images, documents, and videos with size/type validation
- Proper MIME type handling for different file formats
- GCS and YouTube URL integration
- File metadata extraction and display

### Error Handling
- Comprehensive error classification with user-friendly messages
- Detailed logging with Docker integration support
- Graceful degradation when features are unavailable
- Debug mode for troubleshooting

### Streaming and UI Updates
- Efficient streaming chat responses with real-time UI updates
- Non-blocking UI during API calls
- Proper thread management for concurrent operations

## Development Guidelines

### File Organization
- Keep UI components modular in `src/ui/`
- Utilities and helpers in `src/utils/`
- Configuration changes should update `config/config.json`
- Logs are automatically saved to `logs/` directory

### Testing and Debugging
- Use `--debug` flag for verbose logging
- Check `logs/lostmind_ai_YYYYMMDD.log` for detailed error information
- Model discovery issues can be debugged via Settings tab refresh
- Authentication problems are logged with specific error codes

### Configuration Updates
- Edit `config/config.json` for persistent settings changes
- Use ConfigManager for programmatic configuration access
- Settings panel provides UI for runtime configuration changes
- Validate configuration schema when making structural changes