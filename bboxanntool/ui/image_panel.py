"""Image display panel with controls."""

import cv2
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QComboBox, QSizePolicy, QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

class ImagePanel(QWidget):
    image_loaded = pyqtSignal(str)  # Emitted when a new image is loaded
    mode_changed = pyqtSignal(bool)  # True for edit mode, False for draw mode
    save_requested = pyqtSignal()   # Emitted when save button is clicked
    update_needed = pyqtSignal()   # Emitted when display needs to be updated
    coordinate_clicked = pyqtSignal(tuple)  # Emitted when clicking on the image with coordinates
    navigate_requested = pyqtSignal(int)  # Emitted when navigation is requested (1 for next, -1 for prev)

    def __init__(self, settings, drawing_controller=None, editing_controller=None, ann_handler=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.drawing_controller = drawing_controller
        self.editing_controller = editing_controller
        self.ann_handler = ann_handler
        self.init_ui()
        self.image_size = None  # Store the original image size

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
        
        # Image area
        self.image_label = QLabel("Select An Image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(600, 400)
        layout.addWidget(self.image_label)
        
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

    # Navigation shortcuts are now handled at the application level

    def set_mode(self, edit_mode):
        """Set the current mode."""
        self.mode_selector.setCurrentText("Edit Mode" if edit_mode else "Draw Mode")

    def display_image(self, cv_image):
        """Display an OpenCV image."""
        if cv_image is None:
            self.image_label.setText("Select An Image")
            self.image_size = None
            return

        # Store original image dimensions
        self.image_size = (cv_image.shape[1], cv_image.shape[0])  # width, height

        qformat = QImage.Format_Indexed8
        if len(cv_image.shape) == 3:
            if cv_image.shape[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888
        
        img = QImage(cv_image.data, cv_image.shape[1], cv_image.shape[0],
                    cv_image.strides[0], qformat)
        img = img.rgbSwapped()
        pixmap = QPixmap.fromImage(img)
        
        # Scale image to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(self.image_label.size(), 
                                    Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def get_display_transform(self):
        """Get the transformation parameters for mouse coordinate conversion."""
        if not self.image_label.pixmap() or not self.image_size:
            return None

        label_rect = self.image_label.rect()
        orig_w, orig_h = self.image_size  # Original image dimensions
        
        # Calculate the actual size of the displayed image
        scale = min(label_rect.width() / orig_w, label_rect.height() / orig_h)
        scaled_w = orig_w * scale
        scaled_h = orig_h * scale
        
        # Calculate the offsets to center the image in the label
        offset_x = (label_rect.width() - scaled_w) / 2
        offset_y = (label_rect.height() - scaled_h) / 2
        
        return {
            'scale': scale,
            'image_size': (orig_w, orig_h),  # Original image dimensions
            'scaled_size': (scaled_w, scaled_h),  # Display dimensions
            'offset_x': offset_x,
            'offset_y': offset_y
        }

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if not self.image_label.pixmap() or event.button() != Qt.LeftButton:
            return

        # Get the position relative to the label
        pos = self.image_label.mapFromParent(event.pos())
        transform = self.get_display_transform()
        if not transform:
            return
        
        # Convert to image coordinates
        img_x = (pos.x() - transform['offset_x']) / transform['scale']
        img_y = (pos.y() - transform['offset_y']) / transform['scale']
        
        # Ensure coordinates are within bounds
        img_x = max(0, min(img_x, transform['image_size'][0]-1))
        img_y = max(0, min(img_y, transform['image_size'][1]-1))

        if not (0 <= img_x < transform['image_size'][0] and 
                0 <= img_y < transform['image_size'][1]):
            return

        coords = (int(img_x), int(img_y))

        # Handle based on mode
        if self.mode_selector.currentText() == "Edit Mode" and self.editing_controller:
            selection = self.editing_controller.find_control_point(coords, self.ann_handler.annotations)
            if selection is not None:
                self.editing_controller.start_dragging(coords, selection)
                self.ann_handler.select_annotation(selection[0])
                self.update_needed.emit()
        elif self.drawing_controller:  # Draw mode
            # Check if we have a valid label before allowing drawing to start
            main_window = self.ann_handler.parent()
            if main_window and hasattr(main_window, 'label_panel'):
                label = main_window.label_panel.get_current_label()
                if label and label.strip():  # Only start drawing if we have a non-empty label
                    self.drawing_controller.start_drawing(coords)
                    self.update_needed.emit()

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if not self.image_label.pixmap():
            return

        # Get the position relative to the label
        pos = self.image_label.mapFromParent(event.pos())
        transform = self.get_display_transform()
        if not transform:
            return
        
        # Convert to image coordinates
        img_x = (pos.x() - transform['offset_x']) / transform['scale']
        img_y = (pos.y() - transform['offset_y']) / transform['scale']
        
        # Ensure coordinates are within bounds
        img_x = max(0, min(img_x, transform['image_size'][0]-1))
        img_y = max(0, min(img_y, transform['image_size'][1]-1))

        coords = (int(img_x), int(img_y))
        
        # Handle based on mode
        if self.drawing_controller and self.drawing_controller.update_drawing(coords):
            self.update_needed.emit()
        elif self.editing_controller and self.editing_controller.dragging:
            self.editing_controller.update_dragging(coords, self.ann_handler.annotations)
            self.update_needed.emit()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton:
            if self.drawing_controller and self.drawing_controller.drawing:
                # Get the position relative to the label
                pos = self.image_label.mapFromParent(event.pos())
                transform = self.get_display_transform()
                if transform:
                    # Convert to image coordinates
                    img_x = (pos.x() - transform['offset_x']) / transform['scale']
                    img_y = (pos.y() - transform['offset_y']) / transform['scale']
                    
                    # Check bounds and ensure coordinates are valid
                    img_x = max(0, min(img_x, transform['image_size'][0]-1))
                    img_y = max(0, min(img_y, transform['image_size'][1]-1))
                    
                    if (0 <= img_x < transform['image_size'][0] and 
                            0 <= img_y < transform['image_size'][1]):
                        coords = (int(img_x), int(img_y))
                        # Get label from the main window through the annotation handler
                        main_window = self.ann_handler.parent()
                        if main_window and hasattr(main_window, 'label_panel'):
                            label = main_window.label_panel.get_current_label()
                            if label:  # Only finalize if we have a label
                                self.drawing_controller.finish_drawing(coords, label)
                            self.update_needed.emit()
            elif self.editing_controller and self.editing_controller.dragging:
                self.editing_controller.finish_dragging()
                self.update_needed.emit()
