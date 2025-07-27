import os
import json
from pathlib import Path
from typing import Any
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from .logger import logger
from .annotation import Annotation, Annotations, BBox, ANN

class AnnotationHandler(QObject):
    state_reset = pyqtSignal()  # Emitted when the handler state is reset
    current_ann_path_changed = pyqtSignal(str)  # Emitted when the current annotation path changes
    empty_annotations_initialized = pyqtSignal(str)  # Emitted when empty annotations are initialized
    existing_annotations_loaded = pyqtSignal(str)  # Emitted when existing annotations are loaded
    annotations_saved = pyqtSignal(str)  # Emitted when annotations are saved
    unsaved_changes_state_changed = pyqtSignal(bool)  # Emitted when unsaved changes state changes
    unsaved_changes_created = pyqtSignal()  # Emitted when unsaved changes are created
    unsaved_changes_resolved = pyqtSignal()  # Emitted when unsaved changes are resolved
    annotations_changed = pyqtSignal()  # Emitted when annotations are modified
    selected_index_changed = pyqtSignal(int)  # Emitted when the selected annotation index changes
    annotation_unselected = pyqtSignal()  # Emitted when the selected annotation is cleared
    annotation_selected = pyqtSignal(object)  # Emitted when an annotation is selected
    annotation_renamed = pyqtSignal(int, str, str)  # Emitted when an annotation is renamed (index, old_label, new_label)
    annotation_edited = pyqtSignal(int, str, str)  # Emitted when an annotation is edited (index, key, value)
    annotation_deleted = pyqtSignal(int, str)  # Emitted when an annotation is deleted (index, label)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        # State variables
        self._current_ann_path: str | None = None
        self._annotations: Annotations | None = None
        self._selected_index: int | None = None
        self._has_unsaved_changes: bool = False

        # Connections
        self.state_reset.connect(
            lambda: logger.debug("[AnnotationHandler] State reset", "State")
        )
        self.current_ann_path_changed.connect(
            lambda path: logger.debug(f"[AnnotationHandler] Current annotation path changed: {path}", "State")
        )
        self.current_ann_path_changed.connect(self.load_annotations)
        self.empty_annotations_initialized.connect(
            lambda path: logger.info(f"[AnnotationHandler] Empty annotations initialized for: {path}", "State")
        )
        self.existing_annotations_loaded.connect(
            lambda path: logger.info(f"[AnnotationHandler] Existing annotations loaded from: {path}", "State")
        )
        self.annotations_saved.connect(
            lambda path: logger.info(f"[AnnotationHandler] Annotations saved to: {path}", "State")
        )
        self.unsaved_changes_created.connect(
            lambda: logger.debug(f"[AnnotationHandler] Unsaved changes created", "State")
        )
        self.unsaved_changes_resolved.connect(
            lambda: logger.debug(f"[AnnotationHandler] Unsaved changes resolved", "State")
        )
        self.selected_index_changed.connect(
            lambda index: logger.debug(f"[AnnotationHandler] Selected index changed: {index}", "State")
        )
        self.annotation_renamed.connect(
            lambda index, old_label, new_label: logger.info(f"[AnnotationHandler] Annotation renamed at index {index}: {old_label} -> {new_label}", "State")
        )
        self.annotation_edited.connect(
            lambda index, key, value: logger.info(f"[AnnotationHandler] Annotation edited at index {index}: {key} = {value}", "State")
        )
        self.annotation_deleted.connect(
            lambda index, label: logger.info(f"[AnnotationHandler] Annotation deleted at index {index}: {label}", "State")
        )

        logger.debug(f"[{type(self).__name__}] Initialized", "Init")
    
    def _reset(self):
        """Reset the annotation handler state."""
        self._current_ann_path = None
        self._annotations = None
        self._selected_index = None
        self._has_unsaved_changes = False

    def reset(self):
        """Reset the annotation handler state."""
        self._reset()
        self.state_reset.emit()

    @property
    def current_ann_path(self) -> str | None:
        """The path to the current annotation file"""
        return self._current_ann_path
    
    @current_ann_path.setter
    def current_ann_path(self, value: str | None):
        if value is None:
            self.reset()
        elif value != self._current_ann_path:
            self._current_ann_path = value
            self.current_ann_path_changed.emit(value)
        else:
            pass  # No change, do nothing

    @property
    def annotations(self) -> Annotations | None:
        """The current annotations"""
        return self._annotations

    def load_annotations(self):
        """Load annotations from the current annotation path"""
        if self._current_ann_path is None:
            logger.error("[AnnotationHandler] Can't load annotations before setting current_ann_path", "Error")
            raise ValueError("current_ann_path must be set before loading annotations")
        if not Path(self._current_ann_path).exists():
            self._annotations = Annotations([])
            self.empty_annotations_initialized.emit(self._current_ann_path)
        else:
            try:
                self._annotations = Annotations.load(self._current_ann_path)
                self.existing_annotations_loaded.emit(self._current_ann_path)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"[AnnotationHandler] Failed to load annotations: {str(e)}", "Error")
                raise
        
        # Clear selection and reset unsaved changes state after loading
        self.select_annotation(None)
        self._set_has_unsaved_changes(False)
        
        # Emit annotations_changed to update the UI
        self.annotations_changed.emit()
    
    def save_annotations(self):
        """Save annotations to the current annotation path"""
        if self._current_ann_path is None:
            logger.error("[AnnotationHandler] Can't save annotations before setting current_ann_path", "Error")
            raise ValueError("current_ann_path must be set before saving annotations")
        elif self._annotations is None:
            logger.warning("[AnnotationHandler] No annotations to save", "Warning")
            return
        elif not self._has_unsaved_changes:
            logger.debug("[AnnotationHandler] No unsaved changes, skipping save", "Info")
            return
        try:
            self._annotations.save(self._current_ann_path)
            self._set_has_unsaved_changes(False)
            self.annotations_saved.emit(self._current_ann_path)
        except Exception as e:
            logger.error(f"[AnnotationHandler] Failed to save annotations: {str(e)}", "Error")

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether there are unsaved changes to the annotations"""
        return self._has_unsaved_changes

    def _set_has_unsaved_changes(self, value: bool):
        """(Private) Set the unsaved changes state and emit signal"""
        if value != self._has_unsaved_changes:
            self._has_unsaved_changes = value
            self.unsaved_changes_state_changed.emit(value)
            if value:
                self.unsaved_changes_created.emit()
            else:
                self.unsaved_changes_resolved.emit()

    def add_annotation(self, ann: ANN):
        """Add a new annotation to the current annotations"""
        if self._annotations is None:
            logger.error("[AnnotationHandler] Can't add annotation before loading annotations", "Error")
            raise ValueError("Annotations must be loaded before adding new annotations")
        self._annotations.append(ann)
        self._set_has_unsaved_changes(True)
        self.annotations_changed.emit()

    @property
    def selected_index(self) -> int | None:
        """The index of the currently selected annotation"""
        return self._selected_index

    @property
    def selected_annotation(self) -> ANN | None:
        """The currently selected annotation, or None if no annotation is selected"""
        if (
            self._annotations is not None
            and self._selected_index is not None
            and 0 <= self._selected_index < len(self._annotations)
        ):
            return self._annotations[self._selected_index]
        return None

    def select_annotation(self, index: int | None):
        if index is None:
            self._selected_index = None
            self.selected_index_changed.emit(self._selected_index)
            self.annotation_unselected.emit()
        elif 0 <= index < len(self._annotations):
            self._selected_index = index
            self.selected_index_changed.emit(self._selected_index)
            self.annotation_selected.emit(self.selected_annotation)
        else:
            logger.error(f"[AnnotationHandler] Invalid annotation index: {index}. {len(self._annotations)=}", "Error")
            raise IndexError(f"Invalid annotation index: {index}. Must be between 0 and {len(self._annotations) - 1}")

    def rename_selected_annotation(self, label: str):
        ann = self.selected_annotation
        if ann is None:
            logger.warning("[AnnotationHandler] No annotation selected to rename", "Warning")
            return
        old_label = ann.label
        if old_label == label:
            logger.warning("[AnnotationHandler] No change in label, skipping rename", "Warning")
            return
        ann.label = label
        self._set_has_unsaved_changes(True)
        self.annotation_renamed.emit(self._selected_index, old_label, label)
        self.annotations_changed.emit()

    def edit_selected_annotation(self, key: str, value: Any):
        if self._selected_index is None:
            logger.warning("[AnnotationHandler] No annotation selected to edit", "Warning")
            return
        ann = self._annotations[self._selected_index]
        if not hasattr(ann, key):
            logger.error(f"[AnnotationHandler] Annotation does not have attribute '{key}'", "Error")
            raise AttributeError(f"Annotation does not have attribute '{key}'")
        setattr(ann, key, value)
        self.annotation_edited.emit(self._selected_index, key, str(value))
        self._set_has_unsaved_changes(True)
        self.annotations_changed.emit()

    def delete_selected_annotation(self):
        if self._selected_index is None:
            logger.warning("[AnnotationHandler] No annotation selected to delete", "Warning")
            return

        ann = self._annotations.pop(self._selected_index)
        idx = self._selected_index; label = ann.label
        self.select_annotation(None)  # Clear selection after deletion
        self.annotation_deleted.emit(idx, label)

    def delete_annotations_by_label(self, label: str):
        """Delete all annotations with a given label"""
        if self._annotations is None:
            logger.error("[AnnotationHandler] Can't delete annotations before loading annotations", "Error")
            raise ValueError("Annotations must be loaded before deleting by label")
        
        deleted_idx_list = []
        for idx in list(range(len(self._annotations)))[::-1]:
            if self._annotations[idx].label == label:
                del self._annotations[idx]
                if self._selected_index is not None:
                    if self._selected_index >= idx:
                        self._selected_index -= 1
                    elif self._selected_index == idx:
                        self.select_annotation(None)
                deleted_idx_list.append(idx)
        if len(deleted_idx_list) > 0:
            deleted_idx_list.sort()
            self._set_has_unsaved_changes(True)
            self.annotations_changed.emit()
            for idx in deleted_idx_list:
                self.annotation_deleted.emit(idx, label)

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
