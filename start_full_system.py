#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Full System Launcher for LostMindAI Desktop Application with Backend Service.

This script can start both the FastAPI backend service and the PyQt6 desktop
client, or run them individually based on command line options.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging
import argparse
from pathlib import Path
from typing import Optional, List

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProcessManager:
    """Manages backend and frontend processes."""
    
    def __init__(self):
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.running = False
        
    def start_backend(self, backend_dir: str = "backend", host: str = "127.0.0.1", port: int = 8000):
        """Start the FastAPI backend service."""
        try:
            backend_path = Path(backend_dir)
            if not backend_path.exists():
                logger.error(f"Backend directory not found: {backend_path}")
                return False
            
            # Change to backend directory
            original_cwd = os.getcwd()
            os.chdir(backend_path)
            
            # Start the backend using uvicorn
            cmd = [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", host,
                "--port", str(port),
                "--reload"
            ]
            
            logger.info(f"Starting backend service: {' '.join(cmd)}")
            
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Restore original directory
            os.chdir(original_cwd)
            
            # Start background thread to monitor backend output
            threading.Thread(
                target=self._monitor_backend_output,
                daemon=True
            ).start()
            
            # Wait a moment for backend to start
            time.sleep(3)
            
            # Check if process is still running
            if self.backend_process.poll() is None:
                logger.info(f"Backend service started successfully on {host}:{port}")
                return True
            else:
                logger.error("Backend service failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start backend service: {e}")
            return False
    
    def start_frontend(self, mode: str = "backend", backend_url: str = "http://localhost:8000"):
        """Start the PyQt6 desktop client."""
        try:
            # Use the enhanced main script
            cmd = [
                sys.executable, "src/main_enhanced.py",
                "--mode", mode,
                "--backend-url", backend_url
            ]
            
            logger.info(f"Starting desktop client: {' '.join(cmd)}")
            
            self.frontend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start background thread to monitor frontend output
            threading.Thread(
                target=self._monitor_frontend_output,
                daemon=True
            ).start()
            
            # Wait a moment for frontend to start
            time.sleep(2)
            
            # Check if process is still running
            if self.frontend_process.poll() is None:
                logger.info("Desktop client started successfully")
                return True
            else:
                logger.error("Desktop client failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start desktop client: {e}")
            return False
    
    def _monitor_backend_output(self):
        """Monitor backend process output."""
        if not self.backend_process:
            return
        
        try:
            for line in iter(self.backend_process.stdout.readline, ''):
                if line:
                    logger.info(f"[BACKEND] {line.strip()}")
                if self.backend_process.poll() is not None:
                    break
        except Exception as e:
            logger.error(f"Error monitoring backend output: {e}")
    
    def _monitor_frontend_output(self):
        """Monitor frontend process output."""
        if not self.frontend_process:
            return
        
        try:
            for line in iter(self.frontend_process.stdout.readline, ''):
                if line:
                    logger.info(f"[FRONTEND] {line.strip()}")
                if self.frontend_process.poll() is not None:
                    break
        except Exception as e:
            logger.error(f"Error monitoring frontend output: {e}")
    
    def stop_all(self):
        """Stop all processes gracefully."""
        logger.info("Shutting down all processes...")
        
        if self.frontend_process:
            try:
                logger.info("Stopping desktop client...")
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=10)
                logger.info("Desktop client stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Desktop client did not stop gracefully, killing...")
                self.frontend_process.kill()
            except Exception as e:
                logger.error(f"Error stopping desktop client: {e}")
        
        if self.backend_process:
            try:
                logger.info("Stopping backend service...")
                self.backend_process.terminate()
                self.backend_process.wait(timeout=10)
                logger.info("Backend service stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Backend service did not stop gracefully, killing...")
                self.backend_process.kill()
            except Exception as e:
                logger.error(f"Error stopping backend service: {e}")
        
        self.running = False
    
    def wait_for_processes(self):
        """Wait for all processes to complete."""
        self.running = True
        
        try:
            while self.running:
                # Check if processes are still running
                backend_running = self.backend_process and self.backend_process.poll() is None
                frontend_running = self.frontend_process and self.frontend_process.poll() is None
                
                if not backend_running and not frontend_running:
                    logger.info("All processes have exited")
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_all()

def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    # Check Python packages
    required_packages = [
        "PyQt6", "aiohttp", "websockets", "uvicorn", "fastapi"
    ]
    
    for package in required_packages:
        try:
            __import__(package.lower().replace("-", "_"))
        except ImportError:
            missing_deps.append(package)
    
    if missing_deps:
        logger.error(f"Missing required packages: {', '.join(missing_deps)}")
        logger.error("Please install missing packages using:")
        logger.error(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def check_backend_availability(backend_url: str) -> bool:
    """Check if backend service is available."""
    try:
        import requests
        response = requests.get(f"{backend_url}/api/v1/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(description="LostMindAI Full System Launcher")
    parser.add_argument("--mode", choices=["backend-only", "frontend-only", "full", "direct"], 
                       default="full", help="Launch mode")
    parser.add_argument("--backend-host", default="127.0.0.1", help="Backend host")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port")
    parser.add_argument("--backend-url", help="Backend URL (for frontend-only mode)")
    parser.add_argument("--frontend-mode", choices=["direct", "backend"], default="backend",
                       help="Frontend connection mode")
    parser.add_argument("--no-deps-check", action="store_true", help="Skip dependency check")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check dependencies
    if not args.no_deps_check and not check_dependencies():
        return 1
    
    # Initialize process manager
    process_manager = ProcessManager()
    
    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        process_manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        backend_url = f"http://{args.backend_host}:{args.backend_port}"
        
        if args.mode == "backend-only":
            # Start only backend
            logger.info("Starting backend service only...")
            if not process_manager.start_backend(host=args.backend_host, port=args.backend_port):
                return 1
            
        elif args.mode == "frontend-only":
            # Start only frontend
            backend_url = args.backend_url or backend_url
            
            # Check if backend is available when using backend mode
            if args.frontend_mode == "backend":
                if not check_backend_availability(backend_url):
                    logger.warning(f"Backend not available at {backend_url}, switching to direct mode")
                    args.frontend_mode = "direct"
            
            logger.info("Starting desktop client only...")
            if not process_manager.start_frontend(mode=args.frontend_mode, backend_url=backend_url):
                return 1
            
        elif args.mode == "direct":
            # Start frontend in direct mode only
            logger.info("Starting desktop client in direct mode...")
            if not process_manager.start_frontend(mode="direct", backend_url=backend_url):
                return 1
            
        else:  # full mode
            # Start both backend and frontend
            logger.info("Starting full system (backend + frontend)...")
            
            # Start backend first
            if not process_manager.start_backend(host=args.backend_host, port=args.backend_port):
                logger.error("Failed to start backend, starting frontend in direct mode")
                if not process_manager.start_frontend(mode="direct", backend_url=backend_url):
                    return 1
            else:
                # Wait a bit more for backend to be fully ready
                time.sleep(5)
                
                # Start frontend in backend mode
                if not process_manager.start_frontend(mode="backend", backend_url=backend_url):
                    logger.error("Failed to start frontend")
                    return 1
        
        # Show startup summary
        logger.info("="*50)
        logger.info("LostMindAI System Started Successfully!")
        logger.info(f"Mode: {args.mode}")
        if process_manager.backend_process:
            logger.info(f"Backend: {backend_url}")
            logger.info(f"API Documentation: {backend_url}/docs")
        if process_manager.frontend_process:
            logger.info("Desktop Client: Running")
        logger.info("Press Ctrl+C to stop all services")
        logger.info("="*50)
        
        # Wait for processes
        process_manager.wait_for_processes()
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start system: {e}")
        process_manager.stop_all()
        return 1

if __name__ == "__main__":
    sys.exit(main())