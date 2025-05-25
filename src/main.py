#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Entry Point for LostMind AI Gemini Chat Assistant

This module is the main entry point for the Gemini Chat Assistant application.
It initializes the application, sets up logging, and creates the main window.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from config_manager import ConfigManager
from ui.main_window import MainWindow
from utils.error_logger import ErrorLogger

def setup_logging(log_dir="logs", level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_dir (str, optional): Directory for log files. Defaults to "logs".
        level (int, optional): Logging level. Defaults to logging.INFO.
    
    Returns:
        logging.Logger: Root logger.
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path with date
    log_file = os.path.join(
        log_dir, 
        f"lostmind_ai_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger()

def show_splash(app, config):
    """
    Show a splash screen.
    
    Args:
        app (QApplication): Application instance.
        config (ConfigManager): Configuration manager.
    
    Returns:
        QSplashScreen: Splash screen instance.
    """
    # Create a splash screen
    splash_pixmap = QPixmap(500, 300)
    splash_pixmap.fill(Qt.GlobalColor.white)
    
    splash = QSplashScreen(splash_pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
    
    # Add text to splash screen
    splash.showMessage(
        "Loading LostMindAI Desktop...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.darkGray
    )
    
    # Add title
    title_font = QFont("Arial", 24, QFont.Weight.Bold)
    splash.setFont(title_font)
    splash.showMessage(
        "LostMindAI\nDesktop",
        Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.darkBlue
    )
    
    # Add version
    version_font = QFont("Arial", 10)
    splash.setFont(version_font)
    splash.showMessage(
        "Version 1.0.0\n© 2025 LostMindAI",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.darkGray
    )
    
    splash.show()
    app.processEvents()
    
    return splash

def check_dependencies():
    """
    Check if all required dependencies are installed.
    
    Returns:
        bool: True if all dependencies are available, False otherwise.
    """
    try:
        # Check PyQt6
        from PyQt6.QtWidgets import QWidget
        
        # Check Google Cloud libraries
        from google import genai
        from google.cloud import aiplatform
        
        # Check other dependencies
        import PIL
        
        return True
    except ImportError as e:
        QMessageBox.critical(
            None,
            "Missing Dependencies",
            f"Required dependency not found: {str(e)}\n\n"
            "Please install all required dependencies using:\n"
            "pip install -r requirements.txt"
        )
        return False

def check_auth_setup():
    """
    Check if Google Cloud authentication is set up.
    
    Returns:
        bool: True if authentication is set up, False otherwise.
    """
    # Check for GOOGLE_APPLICATION_CREDENTIALS
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        return True
    
    # Check for gcloud default credentials
    home_dir = os.path.expanduser("~")
    gcloud_creds = os.path.join(home_dir, ".config", "gcloud", "application_default_credentials.json")
    if os.path.exists(gcloud_creds):
        return True
    
    # Check for service account via environment
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        # There's at least some environment setup
        return True
    
    return False

def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LostMindAI Desktop - AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--config", type=str, help="Path to custom config file")
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logging(level=log_level)
    logger.info("Starting LostMindAI Desktop")
    
    # Load configuration
    config_path = args.config
    config = ConfigManager(config_path)
    
    # Override log level from config if specified
    config_log_level = config.get_value(['advanced', 'logging_level'], None)
    if config_log_level:
        try:
            log_level = getattr(logging, config_log_level.upper())
            logger.setLevel(log_level)
            logger.info(f"Log level set to {config_log_level}")
        except AttributeError:
            logger.warning(f"Invalid log level in config: {config_log_level}")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("LostMindAI Desktop")
    app.setQuitOnLastWindowClosed(True)
    
    # Show splash screen
    splash = show_splash(app, config)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing dependencies")
        splash.close()
        return 1
    
    # Check authentication setup
    if not check_auth_setup():
        response = QMessageBox.warning(
            None,
            "Authentication Not Found",
            "Google Cloud authentication not found.\n\n"
            "You can still use the application, but you'll need to configure "
            "authentication in the settings.\n\n"
            "Continue anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.No:
            logger.error("Authentication not set up, exiting")
            splash.close()
            return 1
    
    # Create main window
    try:
        main_window = MainWindow(config)
        
        # Close splash screen and show main window after a delay
        QTimer.singleShot(1500, lambda: (splash.close(), main_window.show()))
        
        # Run application
        return app.exec()
        
    except Exception as e:
        logger.exception("Error creating main window")
        splash.close()
        
        QMessageBox.critical(
            None,
            "Initialization Error",
            f"Failed to initialize application: {str(e)}\n\n"
            "Please check the logs for more information."
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())
