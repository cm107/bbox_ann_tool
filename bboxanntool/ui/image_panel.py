"""Image display panel with controls."""

import cv2
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QComboBox, QSizePolicy, QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from ..canvas.ann_canvas import AnnotationCanvas  # new import

class ImagePanel(QWidget):
    image_loaded = pyqtSignal(str)  # Emitted when a new image is loaded
    mode_changed = pyqtSignal(bool)  # True for edit mode, False for draw mode
    save_requested = pyqtSignal()   # Emitted when save button is clicked
    update_needed = pyqtSignal()   # Emitted when display needs to be updated
    coordinate_clicked = pyqtSignal(tuple)  # Emitted when clicking on the image with coordinates
    navigate_requested = pyqtSignal(int)  # Emitted when navigation is requested (1 for next, -1 for prev)

    def __init__(self, settings, drawing_controller=None, editing_controller=None, ann_handler=None, label_handler=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.drawing_controller = drawing_controller
        self.editing_controller = editing_controller
        self.ann_handler = ann_handler
        self.label_handler = label_handler
        self.image_size = None  # Store the original image size
        # create annotation canvas (pass label_handler directly so draw mode has label access)
        self.ann_canvas = AnnotationCanvas(settings,
                                           drawing_controller=self.drawing_controller,
                                           editing_controller=self.editing_controller,
                                           ann_handler=self.ann_handler,
                                           label_handler=self.label_handler,
                                           parent=self)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Draw Mode", "Edit Mode"])
        self.mode_selector.setCurrentText("Draw Mode")
        self.mode_selector.currentTextChanged.connect(
            lambda text: self.mode_changed.emit(text == "Edit Mode")
        )
        mode_layout.addWidget(self.mode_selector)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        # Replace image_label with annotation canvas
        self.ann_canvas.setMinimumSize(600, 400)
        layout.addWidget(self.ann_canvas, stretch=1)
        # Button bar
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Open Image")
        button_layout.addWidget(self.load_button)
        self.load_dir_button = QPushButton("Open Directory")
        button_layout.addWidget(self.load_dir_button)
        self.save_button = QPushButton("Save Annotation")
        self.save_button.clicked.connect(self.save_requested.emit)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def set_mode(self, edit_mode):
        self.mode_selector.setCurrentText("Edit Mode" if edit_mode else "Draw Mode")

    def display_image(self, cv_image):
        if cv_image is None:
            self.image_size = None
            self.ann_canvas.clear()
            return
        self.image_size = (cv_image.shape[1], cv_image.shape[0])
        # Set underlying image (Canvas handles render of base image; overlay will be triggered via update call)
        self.ann_canvas.image = cv_image

    # Deprecated transformation helpers retained for compatibility (not used with AnnotationCanvas)
    def get_display_transform(self):
        return None

    # Update annotations view state (called by main app update_display)
    def update_scene(self, annotations, selected_index, selected_label, group_mode, edit_mode, drag_preview_index, drag_preview_bbox, drawing_preview):
        self.ann_canvas.set_scene_state(annotations, selected_index, selected_label, group_mode, edit_mode, drag_preview_index, drag_preview_bbox, drawing_preview)

    # Expose refresh
    def refresh(self):
        self.ann_canvas.refresh()
