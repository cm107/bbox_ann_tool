import sys
import cv2
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                           QListWidget, QListWidgetItem, QMenuBar, QMenu, 
                           QAction, QDialog, QColorDialog, QLineEdit, QSizePolicy,
                           QCheckBox, QComboBox, QDialogButtonBox, QMessageBox,
                           QSpinBox, QTextEdit)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QIcon
from PyQt5.QtCore import Qt, QPoint, QRect, QSettings, QObject, QObject, pyqtSignal

class AppearanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Appearance Settings")
        self.settings = QSettings(str(Path.home() / ".bbox_ann_tool" / "settings.ini"), 
                                QSettings.Format.IniFormat)
        self.init_ui()

    def create_color_button(self, setting_name, label_text, default_color):
        """Creates a button with a color preview"""
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        
        # Create color preview
        preview = QLabel()
        preview.setFixedSize(20, 20)
        preview.setStyleSheet(f"background-color: {self.settings.value(setting_name, default_color)};")
        layout.addWidget(preview)
        
        # Create button
        button = QPushButton("Change")
        button.clicked.connect(lambda: self.change_color(setting_name, preview, label_text))
        layout.addWidget(button)
        layout.addStretch()
        
        return layout

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Color settings with previews
        layout.addLayout(self.create_color_button("bbox_color", "Normal BBox Color:", "#FF0000"))
        layout.addLayout(self.create_color_button("bbox_selected_color", "Selected BBox Color:", "#00FF00"))
        layout.addLayout(self.create_color_button("points_color", "Edit Points Color:", "#0000FF"))
        layout.addLayout(self.create_color_button("label_color", "Label Text Color:", "#000000"))
        
        # Bbox line width
        line_width_layout = QHBoxLayout()
        line_width_layout.addWidget(QLabel("BBox Line Width:"))
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 10)
        self.line_width_spin.setValue(int(self.settings.value("bbox_line_width", 2)))
        self.line_width_spin.valueChanged.connect(self.change_line_width)
        line_width_layout.addWidget(self.line_width_spin)
        line_width_layout.addStretch()
        layout.addLayout(line_width_layout)
        
        # Edit points size
        points_size_layout = QHBoxLayout()
        points_size_layout.addWidget(QLabel("Edit Points Size:"))
        self.points_size_spin = QSpinBox()
        self.points_size_spin.setRange(3, 20)
        self.points_size_spin.setValue(int(self.settings.value("points_size", 6)))
        self.points_size_spin.valueChanged.connect(lambda v: self.change_numeric("points_size", v))
        points_size_layout.addWidget(self.points_size_spin)
        points_size_layout.addStretch()
        layout.addLayout(points_size_layout)
        
        # Label font size
        label_size_layout = QHBoxLayout()
        label_size_layout.addWidget(QLabel("Label Font Size:"))
        self.label_size_spin = QSpinBox()
        self.label_size_spin.setRange(8, 72)
        self.label_size_spin.setValue(int(self.settings.value("label_font_size", 12)))
        self.label_size_spin.valueChanged.connect(lambda v: self.change_numeric("label_font_size", v))
        label_size_layout.addWidget(self.label_size_spin)
        label_size_layout.addStretch()
        layout.addLayout(label_size_layout)
        
        # Theme settings
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_btn = QPushButton(self.settings.value("theme", "light").title())
        self.theme_btn.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_btn)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        layout.addStretch()
        self.setLayout(layout)

    def change_color(self, setting_name, preview, label_text):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings.setValue(setting_name, color.name())
            preview.setStyleSheet(f"background-color: {color.name()};")
            if self.parent():
                self.parent().update_display()

    def change_line_width(self, value):
        self.settings.setValue("bbox_line_width", value)
        if self.parent():
            self.parent().update_display()

    def change_numeric(self, setting_name, value):
        self.settings.setValue(setting_name, value)
        if self.parent():
            self.parent().update_display()

    def toggle_theme(self):
        current_theme = self.settings.value("theme", "light")
        new_theme = "dark" if current_theme == "light" else "light"
        self.settings.setValue("theme", new_theme)
        self.theme_btn.setText(new_theme.title())
        if self.parent():
            self.parent().apply_theme()

class GlobalEventFilter(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            # Skip if a text input has focus
            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, (QLineEdit, QTextEdit)):
                return False

            if event.key() == Qt.Key_E:
                self.main_window.set_mode(True)  # Switch to Edit mode
                return True
            elif event.key() == Qt.Key_D:
                self.main_window.set_mode(False)  # Switch to Draw mode
                return True
            elif event.key() == Qt.Key_Escape:
                self.main_window.cancel_current_action()
                return True
        return False

class BBoxAnnotationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BBox Annotation Tool")
        self.setGeometry(100, 100, 1280, 720)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon_original.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize settings
        self.settings = QSettings(str(Path.home() / ".bbox_ann_tool" / "settings.ini"), 
                                QSettings.Format.IniFormat)
        
        # Initialize variables
        self.original_image = None
        self.current_image_path = None
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_label = ""
        self.current_annotation_index = None
        self.bboxes = []
        
        # Edit mode variables
        self.edit_mode = False  # Toggle between Draw (False) and Edit (True) modes
        self.dragging = False  # True when dragging a point or bbox
        self.drag_start = None  # Starting position for drag operation
        self.selected_point = None  # (bbox_index, point_index) or (bbox_index, 'center') when dragging
        self.point_size = int(self.settings.value("points_size", 6))  # Size of edit points
        self.points_color = QColor(self.settings.value("points_color", "#0000FF"))  # Color of edit points
        
        self.init_ui()
        self.apply_theme()
        
        # Install global event filter for keyboard shortcuts
        self.event_filter = GlobalEventFilter(self)
        QApplication.instance().installEventFilter(self.event_filter)

        # Install the global event filter
        self.global_event_filter = GlobalEventFilter(self)
        app.installEventFilter(self.global_event_filter)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side (Image and buttons)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Draw Mode", "Edit Mode"])
        self.mode_selector.setCurrentText("Draw Mode")  # Set default mode
        self.mode_selector.currentTextChanged.connect(
            lambda text: self.set_mode(text == "Edit Mode")
        )
        mode_layout.addWidget(self.mode_selector)
        mode_layout.addStretch()
        left_layout.addLayout(mode_layout)
        
        # Image area
        self.image_label = QLabel("Select An Image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(600, 400)
        left_layout.addWidget(self.image_label)
        
        # Button bar
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        self.load_button = QPushButton("Open Image")
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)
        
        self.load_dir_button = QPushButton("Open Directory")
        self.load_dir_button.clicked.connect(self.open_directory)
        button_layout.addWidget(self.load_dir_button)
        
        self.save_button = QPushButton("Save Annotation")
        self.save_button.clicked.connect(self.save_annotations)
        button_layout.addWidget(self.save_button)
        
        left_layout.addWidget(button_widget)
        main_layout.addWidget(left_widget)
        
        # Right side (File list and label selector)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.load_image_from_list)
        right_layout.addWidget(QLabel("Image Files:"))
        right_layout.addWidget(self.file_list)
        
        # Label selector section
        right_layout.addWidget(QLabel("Label:"))
        
        # Label input and selection
        label_input_layout = QVBoxLayout()
        
        # New label input
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Enter label for new bbox")
        label_input_layout.addWidget(self.label_input)
        
        # Used labels list
        right_layout.addWidget(QLabel("Previously Used Labels:"))
        self.used_labels_list = QListWidget()
        self.used_labels_list.itemClicked.connect(self.select_existing_label)
        label_input_layout.addWidget(self.used_labels_list)
        
        right_layout.addLayout(label_input_layout)
        
        # Current image labels section
        right_layout.addWidget(QLabel("Labels in Image:"))
        
        # Group labels checkbox
        self.group_labels_cb = QCheckBox("Group similar labels")
        self.group_labels_cb.setChecked(False)
        self.group_labels_cb.stateChanged.connect(self.update_label_list)
        right_layout.addWidget(self.group_labels_cb)
        
        # Labels in current image
        self.label_list = QListWidget()
        self.label_list.itemClicked.connect(self.highlight_bbox)
        self.label_list.viewport().installEventFilter(self)  # For handling clicks on empty space
        right_layout.addWidget(self.label_list)
        
        main_layout.addWidget(right_widget)
        
        # Create menu bar
        self.create_menu_bar()

    def load_image(self):
        last_dir = self.settings.value("last_image_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", last_dir,
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            self.settings.setValue("last_image_dir", str(Path(file_path).parent))
            self.load_image_file(file_path)
            self.update_file_list([file_path])

    def cancel_current_action(self):
        """Cancel the current drawing/editing action and clear selection"""
        self.drawing = False
        self.dragging = False
        self.selected_point = None
        self.drag_start = None
        self.clear_bbox_selection()
        self.update_display()

    def load_image_file(self, image_path):
        self.current_image_path = image_path
        self.original_image = cv2.imread(image_path)
        self.bboxes = []
        self.cancel_current_action()  # Clear any current selection
        self.load_annotations()
        self.update_used_labels_list()
        self.update_display()

    def open_directory(self):
        last_dir = self.settings.value("last_dir", str(Path.home()))
        dir_path = QFileDialog.getExistingDirectory(self, "Open Directory", last_dir)
        if dir_path:
            self.settings.setValue("last_dir", dir_path)
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']:
                image_files.extend(Path(dir_path).glob(ext))
                image_files.extend(Path(dir_path).glob(ext.upper()))
            self.update_file_list([str(f) for f in image_files])

    def update_file_list(self, files):
        self.file_list.clear()
        for file_path in files:
            item = QListWidgetItem(str(Path(file_path).name))
            # Check if annotation file exists
            ann_path = self.get_annotation_path(file_path)
            if Path(ann_path).exists():
                item.setIcon(QIcon.fromTheme("dialog-ok"))
            self.file_list.addItem(item)

    def load_image_from_list(self, item):
        file_name = item.text()
        dir_path = Path(self.settings.value("last_dir", ""))
        image_path = str(dir_path / file_name)
        self.load_image_file(image_path)

    def get_annotation_path(self, image_path):
        output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return str(Path(output_dir) / f"{Path(image_path).stem}.json")

    def load_annotations(self):
        if not self.current_image_path:
            return

        ann_path = self.get_annotation_path(self.current_image_path)
        if Path(ann_path).exists():
            with open(ann_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Convert old format to new format
                    self.bboxes = [{"label": "", "bbox": list(bbox[0] + bbox[1])} for bbox in data]
                else:
                    self.bboxes = data.get("annotations", [])
        
        self.update_label_list()

    def save_annotations(self):
        if not self.current_image_path:
            return

        ann_path = self.get_annotation_path(self.current_image_path)
        data = {"annotations": self.bboxes}
        with open(ann_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Update file list icon
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.text() == Path(self.current_image_path).name:
                item.setIcon(QIcon.fromTheme("dialog-ok"))
                break

    def update_label_list(self):
        self.label_list.clear()
        
        if self.group_labels_cb.isChecked():
            # Group similar labels and show counts
            label_counts = {}
            for ann in self.bboxes:
                if ann["label"]:
                    label_counts[ann["label"]] = label_counts.get(ann["label"], 0) + 1
            
            for label, count in label_counts.items():
                text = f"{label} ({count})" if count > 1 else label
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, label)
                self.label_list.addItem(item)
        else:
            # Show all annotations separately
            for i, ann in enumerate(self.bboxes):
                if ann["label"]:
                    text = f"{ann['label']} #{i+1}"
                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, ann["label"])
                    item.setData(Qt.UserRole + 1, i)  # Store annotation index
                    self.label_list.addItem(item)

    def highlight_bbox(self, item):
        # Get the actual label without the count
        self.current_label = item.data(Qt.UserRole)
        # Store the specific annotation index (if not in grouped mode)
        self.current_annotation_index = item.data(Qt.UserRole + 1)
        self.update_display()

    def update_display(self):
        if self.original_image is None:
            self.image_label.setText("Select An Image")
            return

        image_to_display = self.original_image.copy()
        bbox_color = QColor(self.settings.value("bbox_color", "#FF0000"))
        bgr_color = (bbox_color.blue(), bbox_color.green(), bbox_color.red())

        # Get appearance settings
        line_width = int(self.settings.value("bbox_line_width", 2))
        selected_color = QColor(self.settings.value("bbox_selected_color", "#00FF00"))
        selected_bgr = (selected_color.blue(), selected_color.green(), selected_color.red())
        label_color = QColor(self.settings.value("label_color", "#000000"))
        label_bgr = (label_color.blue(), label_color.green(), label_color.red())
        label_size = float(self.settings.value("label_font_size", 12)) / 24.0  # Convert to OpenCV scale

        for i, bbox in enumerate(self.bboxes):
            color = bgr_color
            if self.current_label and bbox["label"] == self.current_label:
                if self.group_labels_cb.isChecked() or (self.current_annotation_index is not None and i == self.current_annotation_index):
                    color = selected_bgr

            x1, y1, x2, y2 = bbox["bbox"]
            cv2.rectangle(image_to_display, (x1, y1), (x2, y2), color, line_width)
            
            # Draw label with custom color and size
            cv2.putText(image_to_display, bbox["label"], (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, label_size, label_bgr, max(1, line_width // 2))
            
            # In edit mode, draw control points for all bboxes
            if self.edit_mode:
                points = [
                    (x1, y1),  # Top-left
                    (x2, y1),  # Top-right
                    (x2, y2),  # Bottom-right
                    (x1, y2),  # Bottom-left
                    ((x1 + x2) // 2, (y1 + y2) // 2)  # Center
                ]
                
                # Get point appearance settings
                point_color = QColor(self.settings.value("points_color", "#0000FF"))
                point_bgr = (point_color.blue(), point_color.green(), point_color.red())
                point_size = int(self.settings.value("points_size", 6))
                
                # Draw edit points
                for px, py in points[:-1]:  # Corner points as squares
                    half = point_size // 2
                    cv2.rectangle(image_to_display, 
                                (px - half, py - half),
                                (px + half, py + half),
                                point_bgr, -1)  # Filled
                
                # Draw center point as circle
                cx, cy = points[-1]
                cv2.circle(image_to_display, (cx, cy), 
                          point_size // 2, point_bgr, -1)
        
        self.display_scaled_image(image_to_display)

    def display_scaled_image(self, image_to_display):
        qformat = QImage.Format_Indexed8
        if len(image_to_display.shape) == 3:
            if image_to_display.shape[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888
        
        img = QImage(image_to_display.data, image_to_display.shape[1], image_to_display.shape[0],
                    image_to_display.strides[0], qformat)
        img = img.rgbSwapped()
        pixmap = QPixmap.fromImage(img)
        
        # Scale image to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def _transform_coords(self, pos):
        if self.original_image is None or not self.image_label.pixmap():
            return None

        # Get the geometry of the label and the scaled image
        label_rect = self.image_label.rect()
        pixmap = self.image_label.pixmap()
        
        # Calculate scaling factors
        img_w = self.original_image.shape[1]
        img_h = self.original_image.shape[0]
        
        # Calculate the actual size of the displayed image
        scale = min(label_rect.width() / img_w, label_rect.height() / img_h)
        scaled_w = img_w * scale
        scaled_h = img_h * scale
        
        # Calculate the offset to center the image in the label
        offset_x = (label_rect.width() - scaled_w) / 2
        offset_y = (label_rect.height() - scaled_h) / 2
        
        # Adjust mouse position by subtracting offset and dividing by scale
        img_x = (pos.x() - offset_x) / scale
        img_y = (pos.y() - offset_y) / scale
        
        # Check if point is within image bounds
        if not (0 <= img_x < img_w and 0 <= img_y < img_h):
            return None
        
        return int(img_x), int(img_y)

    def set_mode(self, edit_mode):
        self.edit_mode = edit_mode
        if hasattr(self, 'mode_selector'):
            self.mode_selector.setCurrentText("Edit Mode" if edit_mode else "Draw Mode")
        self.update_display()
        self.statusBar().showMessage(f"{'Edit' if edit_mode else 'Draw'} Mode")

    def mousePressEvent(self, event):
        if self.original_image is None or event.button() != Qt.LeftButton:
            return

        pos = self.image_label.mapFrom(self, event.pos())
        coords = self._transform_coords(pos)
        if not coords:
            return

        if self.edit_mode:
            # Try to find which bbox point was clicked
            point_size = int(self.settings.value("points_size", 6))
            click_x, click_y = coords
            
            # Check each bbox's control points
            for bbox_idx, bbox_data in enumerate(self.bboxes):
                x1, y1, x2, y2 = bbox_data["bbox"]
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                points = [
                    (x1, y1),  # Top-left (0)
                    (x2, y1),  # Top-right (1)
                    (x2, y2),  # Bottom-right (2)
                    (x1, y2),  # Bottom-left (3)
                    center     # Center (4)
                ]
                
                # Check if click is near any point of this bbox
                for point_idx, (px, py) in enumerate(points):
                    if abs(px - click_x) <= point_size and abs(py - click_y) <= point_size:
                        self.dragging = True
                        self.drag_start = coords
                        self.selected_point = (bbox_idx, point_idx)
                        # Update selection to match the bbox being edited
                        self.current_annotation_index = bbox_idx
                        self.current_label = self.bboxes[bbox_idx]["label"]
                        # Update the label list selection
                        self.update_label_list()
                        for i in range(self.label_list.count()):
                            item = self.label_list.item(i)
                            if item.data(Qt.UserRole + 1) == bbox_idx:
                                self.label_list.setCurrentItem(item)
                                break
                        return
                    
        else:  # Draw mode
            self.drawing = True
            self.start_point = coords

    def mouseMoveEvent(self, event):
        pos = self.image_label.mapFrom(self, event.pos())
        coords = self._transform_coords(pos)
        if not coords:
            return

        if self.drawing:  # Draw mode - creating new bbox
            self.end_point = coords
            temp_image = self.original_image.copy()
            
            bbox_color = QColor(self.settings.value("bbox_color", "#FF0000"))
            bgr_color = (bbox_color.blue(), bbox_color.green(), bbox_color.red())
            
            # Draw existing bboxes
            for bbox in self.bboxes:
                x1, y1, x2, y2 = bbox["bbox"]
                cv2.rectangle(temp_image, (x1, y1), (x2, y2), bgr_color, 2)
                cv2.putText(temp_image, bbox["label"], (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 1)
            
            # Draw current bbox
            x1, y1 = self.start_point
            x2, y2 = self.end_point
            cv2.rectangle(temp_image, (x1, y1), (x2, y2), bgr_color, 2)
            if self.label_input.text():
                cv2.putText(temp_image, self.label_input.text(), (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 1)
            
            self.display_scaled_image(temp_image)
            
        elif self.dragging and self.selected_point:  # Edit mode - modifying existing bbox
            bbox_idx, point_idx = self.selected_point
            bbox = self.bboxes[bbox_idx]["bbox"]
            x1, y1, x2, y2 = bbox
            dx = coords[0] - self.drag_start[0]
            dy = coords[1] - self.drag_start[1]
            
            if point_idx == 4:  # Center point - move entire bbox
                x1, x2 = x1 + dx, x2 + dx
                y1, y2 = y1 + dy, y2 + dy
            else:  # Corner point - resize bbox
                if point_idx == 0:    # Top-left
                    x1, y1 = coords
                elif point_idx == 1:  # Top-right
                    x2, y1 = coords
                elif point_idx == 2:  # Bottom-right
                    x2, y2 = coords
                elif point_idx == 3:  # Bottom-left
                    x1, y2 = coords
            
            # Update bbox with new coordinates
            self.bboxes[bbox_idx]["bbox"] = [
                min(x1, x2), min(y1, y2),
                max(x1, x2), max(y1, y2)
            ]
            self.drag_start = coords
            self.update_display()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.drawing and self.label_input.text():  # Finish drawing new bbox
                pos = self.image_label.mapFrom(self, event.pos())
                coords = self._transform_coords(pos)
                if coords:
                    self.drawing = False
                    self.end_point = coords
                    x1, y1 = self.start_point
                    x2, y2 = self.end_point
                    bbox = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
                    self.bboxes.append({
                        "label": self.label_input.text(),
                        "bbox": bbox
                    })
                    self.update_label_list()
                    self.update_display()
            elif self.dragging:  # Finish editing bbox
                self.dragging = False
                self.selected_point = None
                self.drag_start = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_display()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Image", self)
        open_action.setShortcut("Ctrl+I")
        open_action.triggered.connect(self.load_image)
        file_menu.addAction(open_action)
        
        open_dir_action = QAction("Open Image Directory", self)
        open_dir_action.setShortcut("Ctrl+D")
        open_dir_action.triggered.connect(self.open_directory)
        file_menu.addAction(open_dir_action)
        
        change_output_action = QAction("Change Output Directory", self)
        change_output_action.setShortcut("Ctrl+O")
        change_output_action.triggered.connect(self.change_output_directory)
        file_menu.addAction(change_output_action)
        
        save_action = QAction("Save Annotation", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_annotations)
        file_menu.addAction(save_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        appearance_action = QAction("Appearance", self)
        appearance_action.triggered.connect(self.show_appearance_settings)
        view_menu.addAction(appearance_action)

    def apply_theme(self):
        theme = self.settings.value("theme", "light")
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #ffffff; }
                QPushButton { background-color: #3b3b3b; border: 1px solid #555555; padding: 5px; }
                QPushButton:hover { background-color: #4b4b4b; }
                QLabel { color: #ffffff; }
                QListWidget { background-color: #3b3b3b; border: 1px solid #555555; }
                QListWidget::item:selected { background-color: #4b4b4b; }
                QMenuBar { background-color: #3b3b3b; }
                QMenuBar::item:selected { background-color: #4b4b4b; }
            """)
        else:
            self.setStyleSheet("")

    def show_appearance_settings(self):
        dialog = AppearanceDialog(self)
        dialog.exec_()

    def change_output_directory(self):
        current_output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", current_output_dir)
        if dir_path:
            self.settings.setValue("output_dir", dir_path)

    def get_all_unique_labels(self):
        output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        labels = set()
        if Path(output_dir).exists():
            for file in Path(output_dir).glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            # Old format doesn't have labels
                            continue
                        for ann in data.get("annotations", []):
                            if ann.get("label"):
                                labels.add(ann["label"])
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        return sorted(list(labels))

    def select_existing_label(self, item):
        self.label_input.setText(item.text())

    def update_used_labels_list(self):
        self.used_labels_list.clear()
        for label in self.get_all_unique_labels():
            self.used_labels_list.addItem(label)

    def eventFilter(self, source, event):
        if (source is self.label_list.viewport() and
            event.type() == event.MouseButtonPress):
            item = self.label_list.itemAt(event.pos())
            if not item or self.label_list.currentItem() == item:
                self.clear_bbox_selection()
            if event.button() == Qt.RightButton and item:
                self.show_label_context_menu(item, event.globalPos())
        return super().eventFilter(source, event)

    def clear_bbox_selection(self):
        self.label_list.clearSelection()
        self.current_label = ""
        self.current_annotation_index = None
        self.update_display()

    def show_label_context_menu(self, item, pos):
        menu = QMenu()
        edit_action = menu.addAction("Edit Label")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(pos)
        if action == edit_action:
            self.edit_label(item)
        elif action == delete_action:
            self.delete_label(item)

    def edit_label(self, item):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Label")
        layout = QVBoxLayout()

        # Combo box with existing labels
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(self.get_all_unique_labels())
        combo.setCurrentText(item.data(Qt.UserRole))
        layout.addWidget(combo)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            new_label = combo.currentText()
            if new_label:
                index = item.data(Qt.UserRole + 1)
                if index is not None:  # Individual mode
                    self.bboxes[index]["label"] = new_label
                else:  # Group mode
                    old_label = item.data(Qt.UserRole)
                    for bbox in self.bboxes:
                        if bbox["label"] == old_label:
                            bbox["label"] = new_label
                self.update_label_list()
                self.update_display()

    def delete_label(self, item):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirm Delete")
        
        index = item.data(Qt.UserRole + 1)
        if index is not None:  # Individual mode
            msg_box.setText(f"Delete annotation '{item.text()}'?")
        else:  # Group mode
            label = item.data(Qt.UserRole)
            count = sum(1 for bbox in self.bboxes if bbox["label"] == label)
            msg_box.setText(f"Delete all {count} annotations with label '{label}'?")
        
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        if msg_box.exec_() == QMessageBox.Yes:
            if index is not None:  # Individual mode
                self.bboxes.pop(index)
            else:  # Group mode
                label = item.data(Qt.UserRole)
                self.bboxes = [bbox for bbox in self.bboxes if bbox["label"] != label]
            self.update_label_list()
            self.update_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon_original.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = BBoxAnnotationTool()
    window.show()
    sys.exit(app.exec_())