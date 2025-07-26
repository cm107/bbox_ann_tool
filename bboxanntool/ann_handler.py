import os
import json
from pathlib import Path
from typing import TYPE_CHECKING
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from .label_handler import LabelHandler
from .logger import logger

class AnnotationHandler(QObject):
    """
    Handles all annotation-related operations in the BBox Annotation Tool.
    
    This class is responsible for:
    1. Managing the list of annotations for the current image
    2. Saving and loading annotations from files
    3. Creating, editing, and deleting annotations
    4. Tracking selected annotations
    5. Maintaining unsaved changes state

    Interfaces with:
    - BBoxAnnotationTool: Main application window that parents this handler
    - LabelHandler: Direct interface for label operations, discovered via parent

    Signal flow:
    - annotations_changed: Emitted when annotations are modified in a way that affects labels
    - bbox_modified: Emitted when only bbox coordinates are changed (dragging)
    - selection_changed: Emitted when the selected annotation changes
    - unsaved_changes: Emitted when there are unsaved changes
    """
    # Signals
    annotations_changed = pyqtSignal()  # Changes that affect labels or structure
    bbox_modified = pyqtSignal(int)  # Signal which bbox was modified (index)
    selection_changed = pyqtSignal(int, str)  # index, label
    unsaved_changes = pyqtSignal(bool)  # True when there are unsaved changes
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.current_image_path = None
        self.annotations = []  # List of {"label": str, "bbox": [x1,y1,x2,y2]}
        self.selected_index = None
        self._has_unsaved_changes = False
        self._label_handler = None
                
        logger.debug("[AnnotationHandler] Initialized", "Init")

    def setup(self) -> None:
        """
        Set up handler references after all handlers are initialized.
        Should be called after all handlers are created but before use.
        """
        # Find the LabelHandler instance
        if self.parent():
            for child in self.parent().children():
                if child.__class__.__name__ == 'LabelHandler':
                    self._label_handler = child
                    break
            if not self._label_handler:
                logger.error("[AnnotationHandler] Could not find LabelHandler", "Init")
                raise RuntimeError("[AnnotationHandler] Could not find LabelHandler in parent's children")
        
        logger.debug("[AnnotationHandler] Setup complete", "Init")

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether there are unsaved changes to the annotations"""
        return self._has_unsaved_changes
    
    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value: bool):
        if value != self._has_unsaved_changes:
            self._has_unsaved_changes = value
            self.unsaved_changes.emit(value)
    
    @property
    def label_handler(self) -> 'LabelHandler':
        """Get the reference to LabelHandler"""
        if not self._label_handler:
            raise RuntimeError("[AnnotationHandler] Not properly initialized. Call setup() first.")
        return self._label_handler

    def get_annotation_path(self, image_path=None):
        """Get the path where annotations for an image should be saved"""
        if image_path is None:
            image_path = self.current_image_path
        if not image_path:
            return None
            
        output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return str(Path(output_dir) / f"{Path(image_path).stem}.json")
    
    def load_annotations(self, image_path):
        """Load annotations for a specific image"""
        self.current_image_path = image_path
        self.annotations.clear()
        self.selected_index = None
        
        ann_path = self.get_annotation_path()
        if ann_path and Path(ann_path).exists():
            try:
                with open(ann_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Convert old format to new format
                        self.annotations = [{"label": "", "bbox": list(bbox[0] + bbox[1])} for bbox in data]
                    else:
                        self.annotations = data.get("annotations", [])
            except (json.JSONDecodeError, FileNotFoundError):
                pass
                
        self.has_unsaved_changes = False
        self.annotations_changed.emit()
    
    def save_annotations(self):
        """Save annotations for the current image"""
        if not self.current_image_path:
            return False
            
        ann_path = self.get_annotation_path()
        if not ann_path:
            return False
            
        try:
            data = {"annotations": self.annotations}
            with open(ann_path, 'w') as f:
                json.dump(data, f, indent=4)
            self.has_unsaved_changes = False
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save annotations: {str(e)}")
            return False
    
    def add_annotation(self, bbox, label):
        """Add a new annotation with the given bounding box and label"""
        self.annotations.append({
            "label": label,
            "bbox": bbox
        })
        self.has_unsaved_changes = True
        self.annotations_changed.emit()
    
    def update_annotation(self, index, bbox=None, label=None):
        """Update an existing annotation's bbox and/or label"""
        if 0 <= index < len(self.annotations):
            if bbox is not None:
                self.annotations[index]["bbox"] = bbox
                self.has_unsaved_changes = True
                self.bbox_modified.emit(index)  # Emit just the index for coordinate changes
            if label is not None:
                self.annotations[index]["label"] = label
                self.has_unsaved_changes = True
                self.annotations_changed.emit()  # Emit annotations_changed when label changes
    
    def delete_annotation(self, index):
        """Delete an annotation by index"""
        if index is None or not (0 <= index < len(self.annotations)):
            return
            
        self.annotations.pop(index)
        if self.selected_index == index:
            self.selected_index = None
            self.selection_changed.emit(-1, "")  # Clear selection
        elif self.selected_index is not None and self.selected_index > index:
            self.selected_index -= 1
            # Update selection to point to the correct annotation
            self.selection_changed.emit(self.selected_index, self.annotations[self.selected_index]["label"])
            
        self.has_unsaved_changes = True
        self.annotations_changed.emit()
    
    def delete_annotations_by_label(self, label):
        """Delete all annotations with a given label"""
        original_len = len(self.annotations)
        self.annotations = [ann for ann in self.annotations if ann["label"] != label]
        if len(self.annotations) != original_len:
            self.selected_index = None
            self.has_unsaved_changes = True
            self.annotations_changed.emit()
            self.selection_changed.emit(-1, "")
    
    def rename_label(self, old_label, new_label):
        """Rename all annotations with old_label to new_label"""
        changed = False
        for ann in self.annotations:
            if ann["label"] == old_label:
                ann["label"] = new_label
                changed = True
        if changed:
            self.has_unsaved_changes = True
            self.annotations_changed.emit()
            if self.selected_index is not None:
                self.selection_changed.emit(self.selected_index, new_label)
    
    def select_annotation(self, index):
        """Select an annotation by index"""
        if index != self.selected_index and (-1 <= index < len(self.annotations)):
            self.selected_index = index
            label = self.annotations[index]["label"] if index >= 0 else ""
            self.selection_changed.emit(index, label)
    
    def check_unsaved_changes(self):
        """
        Check if there are unsaved changes and return True if it's OK to proceed,
        False if the user wants to cancel
        """
        if not self.has_unsaved_changes:
            return True
            
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Unsaved Changes")
        msg_box.setText("There are unsaved changes. Do you want to continue without saving?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        return msg_box.exec_() == QMessageBox.Yes