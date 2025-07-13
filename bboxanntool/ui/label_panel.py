"""Label management panel."""

from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget,
                           QCheckBox, QLineEdit, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

class LabelPanel(QWidget):
    label_selected = pyqtSignal(str)  # Emitted when a label is selected
    label_input_changed = pyqtSignal(str)  # Emitted when label input text changes
    group_mode_changed = pyqtSignal(bool)  # Emitted when group checkbox changes

    def __init__(self, ann_handler=None, parent=None):
        super().__init__(parent)
        self.ann_handler = ann_handler
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # File list
        layout.addWidget(QLabel("Image Files:"))
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)
        
        # Label input section
        layout.addWidget(QLabel("Label:"))
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Enter label for new bbox")
        self.label_input.textChanged.connect(self.label_input_changed.emit)
        layout.addWidget(self.label_input)
        
        # Used labels list
        layout.addWidget(QLabel("Previously Used Labels:"))
        self.used_labels_list = QListWidget()
        self.used_labels_list.itemClicked.connect(
            lambda item: self.label_selected.emit(item.text())
        )
        layout.addWidget(self.used_labels_list)
        
        # Current image labels
        layout.addWidget(QLabel("Labels in Image:"))
        
        # Group labels checkbox
        self.group_labels_cb = QCheckBox("Group similar labels")
        self.group_labels_cb.setChecked(False)
        self.group_labels_cb.stateChanged.connect(
            lambda state: self.group_mode_changed.emit(bool(state))
        )
        layout.addWidget(self.group_labels_cb)
        
        # Labels in current image
        self.label_list = QListWidget()
        self.label_list.itemClicked.connect(self._on_label_list_clicked)
        layout.addWidget(self.label_list)

    def _on_label_list_clicked(self, item):
        """Handle click on a label in the current image list."""
        # Get the index from the item's data
        index = item.data(Qt.UserRole + 1)
        if index is not None and self.ann_handler is not None:  # Individual mode
            self.ann_handler.select_annotation(index)
        
    def update_used_labels(self, labels):
        """Update the list of previously used labels."""
        self.used_labels_list.clear()
        for label in labels:
            self.used_labels_list.addItem(label)

    def update_current_labels(self, labels, counts=None):
        """Update the list of labels in the current image."""
        self.label_list.clear()
        for i, label in enumerate(labels):
            text = label if counts is None else f"{label} ({counts[i]})"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, label)
            self.label_list.addItem(item)

    def update_file_list(self, files, annotated_files=None):
        """Update the list of image files."""
        self.file_list.clear()
        for file_path in files:
            item = QListWidgetItem(str(Path(file_path).name))
            if annotated_files and file_path in annotated_files:
                item.setIcon(QIcon.fromTheme("dialog-ok"))
            self.file_list.addItem(item)

    def get_current_label(self):
        """Get the current label from the input field."""
        return self.label_input.text()

    def set_current_label(self, label):
        """Set the current label in the input field."""
        self.label_input.setText(label)

    def clear_selection(self):
        """Clear the current label selection."""
        self.label_list.clearSelection()
