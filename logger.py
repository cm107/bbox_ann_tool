import os
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QComboBox, QHBoxLayout, QPushButton, QLabel

class BBoxLogger(QObject):
    """Custom logger with GUI integration"""
    status_message = pyqtSignal(str, int)  # message, duration in ms

    def __init__(self):
        super().__init__()
        self.setup_logger()

    def setup_logger(self):
        # Create logs directory
        log_dir = Path.home() / ".bbox_ann_tool" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('bbox_tool')
        self.logger.setLevel(logging.DEBUG)

        # Create handlers
        today = datetime.now().strftime('%Y-%m-%d')
        file_handler = RotatingFileHandler(
            str(log_dir / f"bbox_tool_{today}.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(logging.DEBUG)

        # Create formatters
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(component)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)

        # Start new session
        self.logger.info("=== New Session Started ===", extra={'component': 'Session'})

    def status(self, message, duration=5000):
        """Show status message and log as INFO"""
        self.status_message.emit(message, duration)
        self.logger.info(message, extra={'component': 'Status'})

    def info(self, message, component='General'):
        """Log an INFO level message"""
        self.logger.info(message, extra={'component': component})

    def warning(self, message, component='General'):
        """Log a WARNING level message"""
        self.logger.warning(message, extra={'component': component})

    def error(self, message, component='General'):
        """Log an ERROR level message"""
        self.logger.error(message, extra={'component': component})

    def debug(self, message, component='General'):
        """Log a DEBUG level message"""
        self.logger.debug(message, extra={'component': component})


class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Filter controls
        filter_layout = QHBoxLayout()
        
        # Log level filter
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Log Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self.filter_logs)
        level_layout.addWidget(self.level_combo)
        filter_layout.addLayout(level_layout)

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QTextEdit()
        self.search_edit.setMaximumHeight(30)
        self.search_edit.textChanged.connect(self.filter_logs)
        search_layout.addWidget(self.search_edit)
        filter_layout.addLayout(search_layout)

        layout.addLayout(filter_layout)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_logs)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_logs)
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.load_logs()

    def load_logs(self):
        log_dir = Path.home() / ".bbox_ann_tool" / "logs"
        if not log_dir.exists():
            self.log_display.setText("No logs found.")
            return

        # Read latest log file
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = log_dir / f"bbox_tool_{today}.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                self.full_log_text = f.read()
            self.filter_logs()
        else:
            self.log_display.setText("No logs for today.")

    def filter_logs(self):
        if not hasattr(self, 'full_log_text'):
            return

        filtered_lines = []
        level = self.level_combo.currentText()
        search_text = self.search_edit.toPlainText().lower()

        for line in self.full_log_text.split('\n'):
            if level != "All" and f"[{level}]" not in line:
                continue
            if search_text and search_text not in line.lower():
                continue
            filtered_lines.append(line)

        self.log_display.setText('\n'.join(filtered_lines))

    def export_logs(self):
        # Implement log export functionality
        pass  # TODO
