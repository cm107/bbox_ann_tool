import os
from pathlib import Path
import json
from typing import TYPE_CHECKING
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, 
                           QListWidgetItem, QListWidget)

if TYPE_CHECKING:
    from .ann_handler import AnnotationHandler
from .logger import logger

class LabelHandler(QObject):
    """
    Handles all label-related operations in the BBox Annotation Tool.
    
    This class is responsible for:
    1. Managing the current active label state
    2. Maintaining a list of all unique labels used across annotations
    3. Providing interfaces for label selection and editing
    4. Managing the UI display of labels and annotations
    5. Updating label displays when annotations change

    Interfaces with:
    - BBoxAnnotationTool: Main application window that parents this handler
    - AnnotationHandler: Direct interface for annotation operations, discovered via parent

    Signal flow:
    - label_changed: Emitted when current label is changed
    - label_deleted: Emitted when a label is deleted
    - label_renamed: Emitted when a label is renamed
    """
    # Signals
    label_changed = pyqtSignal(str)  # Current label changed
    label_deleted = pyqtSignal(str)  # A label was deleted
    label_renamed = pyqtSignal(str, str)  # old_label, new_label
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._current_label = ""
        self._ann_handler = None
        
        logger.debug("[LabelHandler] Initialized", "Init")
        
    def setup(self) -> None:
        """
        Set up handler references after all handlers are initialized.
        Should be called after all handlers are created but before use.
        """
        # Find the AnnotationHandler instance
        if self.parent():
            for child in self.parent().children():
                if child.__class__.__name__ == 'AnnotationHandler':
                    self._ann_handler = child
                    break
            if not self._ann_handler:
                logger.error("[LabelHandler] Could not find AnnotationHandler", "Init")
                raise RuntimeError("[LabelHandler] Could not find AnnotationHandler in parent's children")
        
        logger.debug("[LabelHandler] Setup complete", "Init")
    
    @property
    def current_label(self) -> str:
        """The currently selected label for new annotations"""
        return self._current_label
        
    @current_label.setter
    def current_label(self, value: str) -> None:
        if value != self._current_label:
            self._current_label = value
            self.label_changed.emit(value)

    def get_all_unique_labels(self) -> list[str]:
        """
        Get all unique labels from all annotation files in the output directory.
        Returns a sorted list of labels.
        """
        output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        labels = set()
        if Path(output_dir).exists():
            for file in Path(output_dir).glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        
                    # Handle new format (direct list of annotations)
                    if isinstance(data, list):
                        for ann in data:
                            if isinstance(ann, dict) and ann.get("label"):
                                labels.add(ann["label"])
                    # Handle old format (with "annotations" key)
                    elif isinstance(data, dict) and "annotations" in data:
                        for ann in data["annotations"]:
                            if ann.get("label"):
                                labels.add(ann["label"])
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return sorted(list(labels))
        
    def edit_label_dialog(self, old_label: str) -> str | None:
        """
        Show a dialog to edit a label. Returns the new label if accepted,
        or None if cancelled.
        """
        dialog = QDialog()
        dialog.setWindowTitle("Edit Label")
        layout = QVBoxLayout()

        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.get_all_unique_labels())
        combo.setCurrentText(old_label)
        layout.addWidget(combo)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            new_label = combo.currentText()
            if new_label and new_label != old_label:
                self.label_renamed.emit(old_label, new_label)
                return new_label
        return None

    @property
    def ann_handler(self) -> 'AnnotationHandler':
        """Get the reference to AnnotationHandler"""
        return self._ann_handler

    def update_label_list(self, label_list: 'QListWidget', group_similar: bool = False) -> None:
        """
        Update a QListWidget with the current annotations' labels.
        Args:
            label_list: QListWidget to update
            group_similar: If True, group similar labels and show counts
        """
        from PyQt5.QtCore import Qt  # Add Qt import at the top
        
        label_list.clear()
        logger.debug(f"[LabelHandler] Updating label list, group_similar={group_similar}", "UI")
        
        if group_similar:
            # Group similar labels and show counts
            label_counts = {}
            for ann in self.ann_handler.annotations:
                # Handle both old dict format and new BBox object format
                if hasattr(ann, 'label'):  # New BBox object format
                    label = ann.label
                elif isinstance(ann, dict) and "label" in ann:  # Old dict format
                    label = ann["label"]
                else:
                    continue
                    
                if label:
                    label_counts[label] = label_counts.get(label, 0) + 1
            
            for label, count in label_counts.items():
                text = f"{label} ({count})" if count > 1 else label
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, label)
                label_list.addItem(item)
        else:
            # Show all annotations separately
            for i, ann in enumerate(self.ann_handler.annotations):
                # Handle both old dict format and new BBox object format
                if hasattr(ann, 'label'):  # New BBox object format
                    label = ann.label
                elif isinstance(ann, dict) and "label" in ann:  # Old dict format
                    label = ann["label"]
                else:
                    continue
                    
                if label:
                    text = f"{label} #{i+1}"
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, label)
                    item.setData(Qt.UserRole + 1, i)  # Store annotation index
                    label_list.addItem(item)