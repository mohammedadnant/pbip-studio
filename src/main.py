"""
PBIP Studio - Desktop Application
Main entry point for PyQt6 + FastAPI application
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
import threading
import uvicorn


def setup_logging() -> Path:
    """Configure file logging for frozen and dev runs."""
    log_root = Path(os.getenv('LOCALAPPDATA', Path.home())) / 'PBIP Studio' / 'logs'
    log_root.mkdir(parents=True, exist_ok=True)
    log_file = log_root / 'app.log'
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # Also log to console
        ]
    )
    return log_file

# Determine if we're running as frozen executable or in development
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = Path(sys.executable).parent
    # Add the library.zip to path for frozen apps
    sys.path.insert(0, str(application_path))
    sys.path.insert(0, str(application_path / 'lib'))
    # Ensure Qt can locate bundled plugins when running from MSI install
    qt_plugin_dir = application_path / 'lib' / 'PyQt6' / 'Qt6' / 'plugins'
    qt_platforms = qt_plugin_dir / 'platforms'
    os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', str(qt_platforms))
    os.environ.setdefault('QT_PLUGIN_PATH', str(qt_plugin_dir))
else:
    # Running in development - add src to path
    application_path = Path(__file__).parent.parent
    sys.path.insert(0, str(Path(__file__).parent))

# Now import our modules
from gui.main_window import MainWindow
from api.server import app as fastapi_app


class BackendThread(threading.Thread):
    """Run FastAPI backend in separate daemon thread"""

    def __init__(self, port=8000):
        super().__init__(daemon=True)  # Daemon thread will exit when main program exits
        self.port = port
        self.server = None

    def run(self):
        """Start FastAPI server"""
        logging.info("Starting backend server on port %s", self.port)
        try:
            # Disable uvicorn's logging configuration to avoid formatter errors in frozen apps
            config = uvicorn.Config(
                fastapi_app,
                host="127.0.0.1",
                port=self.port,
                log_level="error",
                access_log=False,
                log_config=None  # Disable uvicorn's default log config
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            logging.error(f"Backend server error: {e}")
    
    def stop(self):
        """Stop the server gracefully"""
        if self.server:
            self.server.should_exit = True


def main():
    """Main application entry point"""
    
    # Set working directory to application path when frozen
    if getattr(sys, 'frozen', False):
        os.chdir(application_path)

    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    qt_plugin_path = os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH')
    if qt_plugin_path:
        logging.info("QT_QPA_PLATFORM_PLUGIN_PATH=%s", qt_plugin_path)
    qt_plugin_root = os.environ.get('QT_PLUGIN_PATH')
    if qt_plugin_root:
        logging.info("QT_PLUGIN_PATH=%s", qt_plugin_root)

    logging.info("Launching PBIP Studio")

    # Create Qt Application FIRST (required for any Qt widgets)
    qt_app = QApplication(sys.argv)
    logging.info("Qt application initialized")
    qt_app.setApplicationName("PBIP Studio")
    qt_app.setOrganizationName("PBIP Studio")

    # Start FastAPI backend in daemon thread
    backend = BackendThread(port=8000)
    backend.start()
    logging.info("Backend thread started")
    
    # Give backend a moment to start
    import time
    time.sleep(0.5)

    # Create and show main window
    try:
        logging.info("About to create MainWindow instance")
        window = MainWindow()
        logging.info("Main window constructed successfully")
    except Exception as e:
        logging.exception("Failed to construct MainWindow")
        error_msg = f"Failed to create main window: {str(e)}"
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Startup Error")
            msg_box.setText(error_msg)
            msg_box.setDetailedText(f"Log file: {LOG_PATH}")
            msg_box.exec()
        except:
            pass
        raise
    
    try:
        window.show()
        window.showMaximized()  # Maximize window after showing
        logging.info("Main window show() called")
    except Exception as e:
        logging.exception("Failed to show MainWindow")
        raise

    # Run application
    logging.info("Starting Qt event loop")
    exit_code = qt_app.exec()
    
    # Cleanup
    logging.info("Shutting down backend server...")
    backend.stop()
    backend.join(timeout=2)
    
    logging.info("Application closed with exit code %s", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    LOG_PATH = setup_logging()
    try:
        main()
    except Exception as exc:  # Log and surface fatal errors when running the MSI
        logging.exception("Fatal error while launching application")
        message = (
            "PBIP Studio failed to start.\n\n"
            f"Detailed logs: {LOG_PATH}\n\n"
            f"Error: {exc}"
        )
        try:
            from ctypes import windll
            windll.user32.MessageBoxW(None, message, "PBIP Studio", 0x10)
        except Exception:
            pass
        sys.exit(1)
