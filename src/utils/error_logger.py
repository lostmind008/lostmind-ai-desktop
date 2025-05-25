#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error Logger for LostMind AI Gemini Chat Assistant

This module handles error logging and reporting, including Docker integration
for centralized error collection.
"""

import os
import json
import socket
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

class DockerErrorLogger:
    """
    Helper class to send error logs to DebuggerDOGE container
    for centralized error tracking and analysis.
    """
    
    def __init__(self, host: str = "localhost", port: int = 5001, enabled: bool = True):
        """
        Initialize the Docker error logger.
        
        Args:
            host (str, optional): Docker container host. Defaults to "localhost".
            port (int, optional): Docker container port. Defaults to 5001.
            enabled (bool, optional): Whether error logging is enabled. Defaults to True.
        """
        self.host = host
        self.port = port
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)
        self.app_name = "GeminiChatAssistant"
    
    def send_error_log(self, error_details: Dict[str, Any]) -> bool:
        """
        Send error log to DebuggerDOGE container
        
        Args:
            error_details (Dict[str, Any]): Dictionary containing error details
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Add timestamp if not present
            if "timestamp" not in error_details:
                error_details["timestamp"] = datetime.now().isoformat()
            
            # Add application name
            if "application" not in error_details:
                error_details["application"] = self.app_name
            
            # Convert to JSON
            error_json = json.dumps(error_details)
            
            # Create connection
            with socket.create_connection((self.host, self.port), timeout=5) as sock:
                # Send data
                sock.sendall(error_json.encode('utf-8'))
            
            self.logger.info(f"Error log sent to DebuggerDOGE: {error_json}")
            return True
            
        except ConnectionRefusedError:
            self.logger.warning("Failed to connect to DebuggerDOGE container. Is it running?")
            return False
        except Exception as e:
            self.logger.error(f"Failed to send error log to DebuggerDOGE: {str(e)}")
            return False
    
    def log_exception(self, 
                     exception: Exception, 
                     context: str = "", 
                     additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log an exception to the DebuggerDOGE container.
        
        Args:
            exception (Exception): The exception to log.
            context (str, optional): Context of the exception (e.g., method name). 
                Defaults to "".
            additional_info (Optional[Dict[str, Any]], optional): Additional information
                to include in the log. Defaults to None.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.enabled:
            return False
        
        try:
            # Prepare error details
            error_details = {
                "error": str(exception),
                "error_type": exception.__class__.__name__,
                "stack_trace": traceback.format_exc(),
                "context": context,
                "application": self.app_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add additional info if provided
            if additional_info:
                error_details.update(additional_info)
            
            # Send error log
            return self.send_error_log(error_details)
            
        except Exception as e:
            self.logger.error(f"Failed to log exception: {str(e)}")
            return False

class ErrorLogger:
    """
    Enhanced error logging and handling class that integrates Docker error logging
    with standard Python logging.
    """
    
    def __init__(self, 
                app_name: str = "GeminiChatAssistant",
                log_to_file: bool = True,
                log_dir: str = "logs",
                docker_logging: bool = True,
                docker_host: str = "localhost",
                docker_port: int = 5001):
        """
        Initialize the error logger.
        
        Args:
            app_name (str, optional): Application name for logs. 
                Defaults to "GeminiChatAssistant".
            log_to_file (bool, optional): Whether to log to file. Defaults to True.
            log_dir (str, optional): Directory for log files. Defaults to "logs".
            docker_logging (bool, optional): Whether to enable Docker logging. 
                Defaults to True.
            docker_host (str, optional): Docker container host. Defaults to "localhost".
            docker_port (int, optional): Docker container port. Defaults to 5001.
        """
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)
        
        # Initialize Docker error logger
        self.docker_logger = DockerErrorLogger(
            host=docker_host,
            port=docker_port,
            enabled=docker_logging
        )
        
        # Set up file logging if enabled
        if log_to_file:
            # Ensure log directory exists
            os.makedirs(log_dir, exist_ok=True)
            
            # Create log file path with date
            log_file = os.path.join(
                log_dir, 
                f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"
            )
            
            # Set up file handler
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
    
    def log_error(self, 
                 error_message: str, 
                 exception: Optional[Exception] = None,
                 context: str = "",
                 additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with both standard logging and Docker error logging.
        
        Args:
            error_message (str): Error message to log.
            exception (Optional[Exception], optional): Exception object if available.
                Defaults to None.
            context (str, optional): Context of the error. Defaults to "".
            additional_info (Optional[Dict[str, Any]], optional): Additional information.
                Defaults to None.
        """
        # Log with standard logger
        if exception:
            self.logger.error(f"{error_message}: {str(exception)}")
            self.logger.debug(traceback.format_exc())
        else:
            self.logger.error(error_message)
        
        # Prepare error details for Docker logging
        error_details = {
            "error_message": error_message,
            "context": context,
            "application": self.app_name
        }
        
        # Add exception details if available
        if exception:
            error_details.update({
                "error": str(exception),
                "error_type": exception.__class__.__name__,
                "stack_trace": traceback.format_exc()
            })
        
        # Add additional info if provided
        if additional_info:
            error_details.update(additional_info)
        
        # Send to Docker logger
        self.docker_logger.send_error_log(error_details)
    
    def log_exception(self,
                     exception: Exception,
                     context: str = "",
                     additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an exception with both standard logging and Docker error logging.
        
        Args:
            exception (Exception): Exception to log.
            context (str, optional): Context of the exception. Defaults to "".
            additional_info (Optional[Dict[str, Any]], optional): Additional information.
                Defaults to None.
        """
        # Log with standard logger
        self.logger.exception(f"Exception in {context}: {str(exception)}")
        
        # Log with Docker logger
        self.docker_logger.log_exception(
            exception=exception,
            context=context,
            additional_info=additional_info
        )
    
    def log_warning(self,
                  warning_message: str,
                  context: str = "",
                  additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a warning.
        
        Args:
            warning_message (str): Warning message to log.
            context (str, optional): Context of the warning. Defaults to "".
            additional_info (Optional[Dict[str, Any]], optional): Additional information.
                Defaults to None.
        """
        # Log with standard logger
        self.logger.warning(f"{warning_message}")
        
        # Only log warnings to Docker if additional_info is provided
        if additional_info:
            warning_details = {
                "warning_message": warning_message,
                "context": context,
                "application": self.app_name,
                "level": "WARNING"
            }
            warning_details.update(additional_info)
            
            # Send to Docker logger
            self.docker_logger.send_error_log(warning_details)
