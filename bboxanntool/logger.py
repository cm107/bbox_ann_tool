"""Logging components for BBox Annotation Tool."""

import os
import logging
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QComboBox, 
                            QLabel, QPushButton, QHBoxLayout, QLineEdit)
from PyQt5.QtCore import pyqtSignal, QObject

class BBoxLogger(QObject):
    status_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('bbox_tool')
        if not self.logger.handlers:
            self.setup_logger()
        
    def setup_logger(self):
        """Configure logger with file and stream handlers."""
        self.logger.setLevel(logging.DEBUG)

        # File handler
        log_dir = Path.home() / '.bbox_ann_tool' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Daily log file
        log_file = log_dir / f"bbox_tool_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(component)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def debug(self, message, component="General"):
        """Log a debug message."""
        self.logger.debug(message, extra={'component': component})
        
    def info(self, message, component="General"):
        """Log an info message."""
        self.logger.info(message, extra={'component': component})
        
    def warning(self, message, component="General"):
        """Log a warning message."""
        self.logger.warning(message, extra={'component': component})
        
    def error(self, message, component="General"):
        """Log an error message."""
        self.logger.error(message, extra={'component': component})
        
    def status(self, message):
        """Show a temporary status message in the status bar."""
        self.status_message.emit(message)

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setGeometry(100, 100, 800, 600)
        
        # Load log files
        log_dir = Path.home() / '.bbox_ann_tool' / 'logs'
        self.log_files = sorted(log_dir.glob('*.log'), reverse=True)
        
        self.init_ui()
        self.load_current_log()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Controls
        controls = QHBoxLayout()
        
        # File selector
        controls.addWidget(QLabel("Log File:"))
        self.file_selector = QComboBox()
        for log_file in self.log_files:
            self.file_selector.addItem(log_file.name, str(log_file))
        self.file_selector.currentIndexChanged.connect(self.load_current_log)
        controls.addWidget(self.file_selector)
        
        # Level filter
        controls.addWidget(QLabel("Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self.filter_logs)
        controls.addWidget(self.level_filter)
        
        # Search box
        controls.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.textChanged.connect(self.filter_logs)
        controls.addWidget(self.search_box)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_current_log)
        controls.addWidget(self.refresh_btn)
        
        layout.addLayout(controls)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.log_display)
        
        self.setLayout(layout)

    def load_current_log(self):
        if self.file_selector.count() == 0:
            return
            
        file_path = Path(self.file_selector.currentData())
        try:
            with open(file_path, 'r') as f:
                self.raw_logs = f.readlines()
            self.filter_logs()
        except Exception as e:
            self.log_display.setText(f"Error loading log file: {str(e)}")

    def filter_logs(self):
        if not hasattr(self, 'raw_logs'):
            return
            
        level = self.level_filter.currentText()
        search_text = self.search_box.text().lower()
        
        filtered_logs = []
        for line in self.raw_logs:
            # Apply level filter
            if level != "All" and f"[{level}]" not in line:
                continue
            
            # Apply search filter
            if search_text and search_text not in line.lower():
                continue
                
            filtered_logs.append(line)
        
        self.log_display.setText(''.join(filtered_logs))
