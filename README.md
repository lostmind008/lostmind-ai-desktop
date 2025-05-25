# LostMindAI Desktop

A modern PyQt6-based desktop application for interacting with Google's Gemini AI models via Vertex AI.

## Features

- **Modern UI**: Clean, responsive user interface built with PyQt6
- **Gemini Integration**: Seamless integration with Google's Gemini AI models via Vertex AI
- **File Support**: Upload and process various file types including images, PDFs, and text files
- **Google Search Grounding**: Enhanced responses using Google Search for Gemini 2.0 models
- **Chat Management**: Save, export, and manage chat sessions
- **Comprehensive Model Info**: Detailed information about model capabilities and features
- **Customizable Settings**: Configure model parameters, themes, and other settings

## Screenshots

*[Screenshots will be added here once the application is running]*

## Requirements

- Python 3.9+
- PyQt6
- Google Cloud account with Vertex AI enabled
- Proper authentication setup for Google Cloud

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/lostmind008/lostmind-ai-desktop.git
   cd lostmind-ai-desktop
   ```

2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up authentication for Google Cloud.
   
   Option 1: Set environment variables:
   ```
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GOOGLE_CLOUD_LOCATION=us-central1
   ```
   
   Option 2: Use Application Default Credentials:
   ```
   gcloud auth application-default login
   ```
   
   Option 3: Use a service account key:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

## Usage

Run the application:
```
python src/main.py
```

For debugging mode:
```
python src/main.py --debug
```

To use a custom configuration file:
```
python src/main.py --config /path/to/config.json
```

## Configuration

Edit `config/config.json` to customize:
- Default model settings
- UI preferences
- File handling
- Feature toggles

## Project Structure

```
├── config/                # Configuration files
│   └── config.json        # Main configuration
├── src/                   # Source code
│   ├── ui/                # UI components
│   │   ├── main_window.py # Main application window
│   │   ├── chat_display.py # Chat display component
│   │   ├── controls_panel.py # Message input controls
│   │   └── ...
│   ├── utils/             # Utility modules
│   │   ├── error_logger.py # Error logging utilities
│   │   └── file_handler.py # File handling utilities
│   ├── config_manager.py  # Configuration management
│   ├── model_registry.py  # Model discovery and registry
│   ├── gemini_assistant.py # Core Gemini functionality
│   └── main.py            # Application entry point
└── README.md              # This file
```

## Key Components

- **MainWindow**: Main application window with all UI components
- **ChatDisplay**: Displays chat messages with markdown rendering
- **ControlsPanel**: Message input and controls
- **ConfigManager**: Manages application configuration
- **ModelRegistry**: Discovers and manages available models
- **GeminiAssistant**: Core functionality for interacting with Gemini models

## Troubleshooting

### Authentication Issues

If you encounter authentication issues:

1. Ensure you have set up Google Cloud authentication correctly
2. Verify your project has the Vertex AI API enabled
3. Check that your account has the necessary permissions
4. Look at the application logs for detailed error messages

### Model Not Found

If models are not loading:

1. Use the "Refresh Model List" button in the Settings tab
2. Verify your Google Cloud project has access to Gemini models
3. Check your internet connection
4. Restart the application

### Running from Source

If you have issues running the application:

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check that you're using Python 3.9 or newer
3. Verify that PyQt6 is installed correctly
4. Run with debug mode: `python src/main.py --debug`

## License

Copyright © 2025 LostMindAI. All rights reserved.
