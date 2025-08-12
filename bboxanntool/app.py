"""Main application window for BBox Annotation Tool."""

import sys
import cv2
import os
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                           QMenuBar, QMenu, QAction, QDialog, QFileDialog,
                           QMessageBox, QShortcut)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import (Qt, QSettings, QTimer, QObject, pyqtSignal, qVersion,
                        QPoint)
from PyQt5.Qt import PYQT_VERSION_STR

from .logger import BBoxLogger, LogViewerDialog
from .appearance import AppearanceDialog
from .ann_handler import AnnotationHandler
from .annotation import BBox
from .label_handler import LabelHandler
from .image_handler import ImageHandler
from .ui import ImagePanel, LabelPanel
from .rendering import ImageRenderer
from .controllers import DrawingController, EditingController

__version__ = "0.1.0"  # Application version

class BBoxAnnotationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BBox Annotation Tool")
        self.setGeometry(100, 100, 1280, 720)
        
        # Initialize logger
        self.logger = BBoxLogger()
        self.logger.status_message.connect(self.show_status_message)
        self.logger.info("[BBoxAnnotationTool] Starting application", "Init")
        
        # Initialize settings
        self.settings = QSettings(str(Path.home() / ".bbox_ann_tool" / "settings.ini"), 
                                QSettings.Format.IniFormat)
        
        # Initialize handlers
        self.image_handler = ImageHandler(self)
        self.label_handler = LabelHandler(self.settings, self)
        self.ann_handler = AnnotationHandler(self.settings, self)
        
        # Initialize components
        self.renderer = ImageRenderer(self.settings)
        self.drawing_controller = DrawingController(self.settings)
        self.editing_controller = EditingController(self.settings)
        
        # Initialize state variables
        # (ImageHandler now manages image state)
        
        # Store preview coordinates during dragging
        self.drag_preview_index = None
        self.drag_preview_bbox = None
        
        # Set up UI and handlers
        self.init_ui()
        self.setup_handlers()
        self.apply_theme()
        
        self.logger.debug("[BBoxAnnotationTool] UI initialized", "Init")

    def init_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create panels
        self.image_panel = ImagePanel(
            self.settings,
            drawing_controller=self.drawing_controller,
            editing_controller=self.editing_controller,
            ann_handler=self.ann_handler,
            label_handler=self.label_handler  # pass label handler so draw mode works
        )
        self.label_panel = LabelPanel(ann_handler=self.ann_handler)
        
        # Add panels to layout
        main_layout.addWidget(self.image_panel)
        main_layout.addWidget(self.label_panel)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Install event filter for context menu
        self.label_panel.label_list.viewport().installEventFilter(self)
        
        # Add global keyboard shortcuts
        draw_shortcut = QShortcut(Qt.Key_D, self)
        draw_shortcut.activated.connect(lambda: self.set_mode(False))
        draw_shortcut.setContext(Qt.ApplicationShortcut)
        
        edit_shortcut = QShortcut(Qt.Key_E, self)
        edit_shortcut.activated.connect(lambda: self.set_mode(True))
        edit_shortcut.setContext(Qt.ApplicationShortcut)
        
        # Navigation shortcuts
        for key in [Qt.Key_Right, Qt.Key_Left, Qt.Key_Up, Qt.Key_Down]:
            shortcut = QShortcut(key, self)
            if key in [Qt.Key_Right, Qt.Key_Down]:
                shortcut.activated.connect(lambda: self.image_panel.navigate_requested.emit(1))
            else:
                shortcut.activated.connect(lambda: self.image_panel.navigate_requested.emit(-1))
            shortcut.setContext(Qt.ApplicationShortcut)

    def setup_handlers(self):
        """Set up signal handlers and connections."""
        # Set up handler references
        self.label_handler.setup()
        
        # Connect image handler signals
        self.image_handler.current_image_changed.connect(self.on_image_changed)
        self.image_handler.current_image_path_changed.connect(self.on_image_path_changed)
        self.image_handler.image_paths_changed.connect(self.on_image_paths_changed)
        
        # Connect handler signals
        self.ann_handler.annotations_changed.connect(self.on_annotations_changed)
        # Note: New AnnotationHandler doesn't have bbox_modified signal - handled via annotations_changed
        self.ann_handler.selected_index_changed.connect(lambda idx: self.on_annotation_selected(idx, self.ann_handler.selected_annotation.label if self.ann_handler.selected_annotation else ""))
        self.ann_handler.annotation_unselected.connect(lambda: self.on_annotation_selected(-1, ""))
        self.ann_handler.unsaved_changes_state_changed.connect(self.on_unsaved_changes)
        
        self.label_handler.label_changed.connect(self.on_label_changed)
        # Note: New AnnotationHandler doesn't have rename_label method - handled differently
        
        # Connect UI panel signals
        self.image_panel.mode_changed.connect(self.set_mode)
        self.image_panel.save_requested.connect(self.save_annotations)
        self.image_panel.load_button.clicked.connect(self.load_image)
        self.image_panel.load_dir_button.clicked.connect(self.open_directory)
        self.image_panel.update_needed.connect(self.update_display)
        self.image_panel.navigate_requested.connect(self.navigate_to_image)  # Connect navigation signal
        
        self.label_panel.label_selected.connect(self.select_existing_label)
        self.label_panel.group_mode_changed.connect(
            lambda checked: self.label_handler.update_label_list(
                self.label_panel.label_list, checked
            )
        )
        self.label_panel.file_list.itemClicked.connect(self.load_image_from_list)
        
        # Connect controllers
        self.drawing_controller.bbox_created.connect(self.on_bbox_created)
        self.editing_controller.bbox_modified.connect(self.on_bbox_modified)
        self.editing_controller.bbox_preview.connect(self.on_bbox_preview)

    def load_image(self):
        if not self.ann_handler.check_unsaved_changes():
            return
            
        last_dir = self.settings.value("last_image_dir", str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", last_dir,
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            try:
                self.settings.setValue("last_image_dir", str(Path(file_path).parent))
                # Reset the ImageHandler and set single image
                self.image_handler.reset()
                self.image_handler._image_paths = [file_path]  # Set as single-image list
                self.image_handler._image_index = 0
                self.image_handler.current_image_path = file_path
                # Update the file list to show just this image
                self.label_panel.update_file_list([file_path])
                self.logger.status(f"[BBoxAnnotationTool] Opened image: {Path(file_path).name}")
                self.logger.info(f"[BBoxAnnotationTool] Loaded image file: {file_path}", "FileOps")
            except Exception as e:
                self.logger.error(f"[BBoxAnnotationTool] Failed to load image {file_path}: {str(e)}", "FileOps")
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")

    def open_directory(self):
        last_dir = self.settings.value("last_dir", str(Path.home()))
        dir_path = QFileDialog.getExistingDirectory(self, "Open Directory", last_dir)
        if dir_path:
            try:
                self.settings.setValue("last_dir", dir_path)
                self.image_handler.image_directory = dir_path
                self.logger.status(f"[BBoxAnnotationTool] Opened directory with {len(self.image_handler.image_paths or [])} images")
                self.logger.info(f"[BBoxAnnotationTool] Loaded directory {dir_path} with {len(self.image_handler.image_paths or [])} images", "FileOps")
                if not self.image_handler.image_paths:
                    self.logger.warning(f"[BBoxAnnotationTool] No image files found in directory: {dir_path}", "FileOps")
                else:
                    # Automatically navigate to the first image
                    self.image_handler.go_to_first_image()
            except Exception as e:
                self.logger.error(f"[BBoxAnnotationTool] Failed to open directory {dir_path}: {str(e)}", "FileOps")
                QMessageBox.critical(self, "Error", f"Failed to open directory: {str(e)}")

    def load_image_from_list(self, item):
        if not self.ann_handler.check_unsaved_changes():
            return
            
        file_name = item.text()
        # If we have image paths loaded, find the full path and set the index
        if self.image_handler.image_paths:
            for index, path in enumerate(self.image_handler.image_paths):
                if Path(path).name == file_name:
                    self.image_handler.image_index = index  # This will also set the current_image_path
                    return
        
        # Fallback to old method if not found in image_paths
        dir_path = Path(self.settings.value("last_dir", ""))
        image_path = str(dir_path / file_name)
        if Path(image_path).exists():
            self.image_handler.current_image_path = image_path

    def save_annotations(self):
        """Save annotations using the AnnotationHandler"""
        try:
            self.ann_handler.save_annotations()
            # Update file list icon
            image_path = self.image_handler.current_image_path
            if image_path:
                for i in range(self.label_panel.file_list.count()):
                    item = self.label_panel.file_list.item(i)
                    if item.text() == Path(image_path).name:
                        item.setIcon(QIcon.fromTheme("dialog-ok"))
                        break
                
                self.logger.status(f"[BBoxAnnotationTool] Saved annotations for {Path(image_path).name}")
                self.logger.info(f"[BBoxAnnotationTool] Saved annotations to {self.ann_handler.current_ann_path}", "FileOps")
        except Exception as e:
            self.logger.error(f"[BBoxAnnotationTool] Failed to save annotations: {str(e)}", "FileOps")
            QMessageBox.critical(self, "Error", f"Failed to save annotations: {str(e)}")

    def _convert_annotations_for_display(self, annotations):
        """Convert new annotation format to old format for renderer compatibility."""
        if annotations is None:
            return []
        converted = []
        for i, ann in enumerate(annotations):
            if hasattr(ann, 'p0') and hasattr(ann, 'p1'):  # BBox annotation
                # Use preview coordinates if this annotation is being dragged
                if self.drag_preview_index == i and self.drag_preview_bbox is not None:
                    x1, y1, x2, y2 = self.drag_preview_bbox
                else:
                    x1, y1 = ann.p0
                    x2, y2 = ann.p1
                converted.append({
                    "label": ann.label,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                })
        return converted

    def update_display(self):
        """Update the display with current annotations."""
        current_image = self.image_handler.current_image
        if current_image is None:
            self.image_panel.display_image(None)
            return
        # Ensure image set (only when changed) handled elsewhere; here just update overlay state
        if self.image_panel.ann_canvas.image is not current_image:
            self.image_panel.display_image(current_image)
        # Build drawing preview
        drawing_preview = None
        if self.drawing_controller.drawing:
            cur = self.drawing_controller.get_current_bbox()
            if cur:
                drawing_preview = cur
        # Update scene state in annotation canvas
        self.image_panel.update_scene(
            self.ann_handler.annotations or [],
            self.ann_handler.selected_index,
            self.label_handler.current_label,
            self.label_panel.group_labels_cb.isChecked(),
            self.editing_controller.dragging or self.image_panel.mode_selector.currentText() == "Edit Mode",
            self.drag_preview_index,
            self.drag_preview_bbox,
            drawing_preview
        )

    def set_mode(self, edit_mode):
        """Set the current mode (edit/draw)."""
        self.image_panel.set_mode(edit_mode)
        # Do not clear label selection (needed for drawing); only cancel active drag/draw
        if self.drawing_controller.drawing:
            self.drawing_controller.drawing = False
        if self.editing_controller.dragging:
            self.editing_controller.finish_dragging()
        self.drag_preview_index = None
        self.drag_preview_bbox = None
        mode = "Edit" if edit_mode else "Draw"
        self.logger.status(f"[BBoxAnnotationTool] Switched to {mode} Mode")
        self.update_display()

    def cancel_current_action(self):
        """Cancel the current drawing/editing action."""
        if self.drawing_controller.drawing:
            self.drawing_controller.drawing = False
        if self.editing_controller.dragging:
            self.editing_controller.finish_dragging()
        # Clear any preview coordinates
        self.drag_preview_index = None
        self.drag_preview_bbox = None
        self.label_panel.clear_selection()
        self.update_display()

    def select_existing_label(self, label):
        """Select an existing label from the list."""
        self.label_handler.current_label = label
        self.label_panel.set_current_label(label)

    def on_bbox_created(self, bbox, label):
        """Handle bbox creation from DrawingController."""
        # Convert from old format [x1, y1, x2, y2] to new BBox object
        import numpy as np
        x1, y1, x2, y2 = bbox
        p0 = np.array([x1, y1], dtype=np.float32)
        p1 = np.array([x2, y2], dtype=np.float32)
        bbox_obj = BBox(label, p0, p1)
        self.ann_handler.add_annotation(bbox_obj)

    def on_bbox_modified(self, index, new_bbox):
        """Handle bbox modification from EditingController."""
        # Clear preview coordinates when final modification is complete
        self.drag_preview_index = None
        self.drag_preview_bbox = None
        
        # Convert from old format [x1, y1, x2, y2] and update the existing annotation
        import numpy as np
        x1, y1, x2, y2 = new_bbox
        p0 = np.array([x1, y1], dtype=np.float32)
        p1 = np.array([x2, y2], dtype=np.float32)
        
        # Update the selected annotation's bbox coordinates
        if self.ann_handler.selected_index == index:
            self.ann_handler.edit_selected_annotation('p0', p0)
            self.ann_handler.edit_selected_annotation('p1', p1)

    def on_bbox_preview(self, index, new_bbox):
        """Handle bbox preview during dragging - provides visual feedback without triggering edit signals."""
        # Store preview coordinates for display
        self.drag_preview_index = index
        self.drag_preview_bbox = new_bbox
        self.update_display()

    def on_annotations_changed(self):
        """Handle changes to annotations."""
        self.label_handler.update_label_list(
            self.label_panel.label_list,
            self.label_panel.group_labels_cb.isChecked()
        )
        self.update_display()

    def on_annotation_selected(self, index, label):
        """Handle selection change from AnnotationHandler."""
        if index >= 0:
            for i in range(self.label_panel.label_list.count()):
                item = self.label_panel.label_list.item(i)
                if item.data(Qt.UserRole + 1) == index:
                    self.label_panel.label_list.setCurrentItem(item)
                    break
        else:
            self.label_panel.label_list.clearSelection()
        self.update_display()

    def on_label_changed(self, label):
        """Handle current label change from LabelHandler."""
        self.label_panel.set_current_label(label)

    def on_unsaved_changes(self, has_changes):
        """Handle unsaved changes state from AnnotationHandler."""
        self.setWindowTitle(f"BBox Annotation Tool {'*' if has_changes else ''}")

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
        
        # Logging menu
        logging_menu = menubar.addMenu("Logging")
        
        view_logs_action = QAction("View Logs", self)
        view_logs_action.triggered.connect(self.show_log_viewer)
        logging_menu.addAction(view_logs_action)

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
        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.logger.status("[BBoxAnnotationTool] Appearance settings updated")
            self.logger.info("[BBoxAnnotationTool] Updated appearance settings", "Settings")

    def change_output_directory(self):
        current_output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", current_output_dir)
        if dir_path:
            try:
                self.settings.setValue("output_dir", dir_path)
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                self.logger.status("[BBoxAnnotationTool] Changed output directory")
                self.logger.info(f"[BBoxAnnotationTool] Output directory changed to: {dir_path}", "FileOps")
            except Exception as e:
                self.logger.error(f"[BBoxAnnotationTool] Failed to set output directory {dir_path}: {str(e)}", "FileOps")
                QMessageBox.critical(self, "Error", f"Failed to set output directory: {str(e)}")

    def show_log_viewer(self):
        """Show the log viewer dialog"""
        dialog = LogViewerDialog(self)
        dialog.exec_()

    def show_status_message(self, message, duration=5000):
        """Show a temporary status message in the status bar"""
        self.statusBar().showMessage(message)
        QTimer.singleShot(duration, self.statusBar().clearMessage)

    def eventFilter(self, source, event):
        if source is self.label_panel.label_list.viewport():
            if event.type() == event.MouseButtonPress:
                item = self.label_panel.label_list.itemAt(event.pos())
                if event.button() == Qt.RightButton and item:
                    self.show_label_context_menu(item, event.globalPos())
                    return True
                elif not item or self.label_panel.label_list.currentItem() == item:
                    self.label_panel.clear_selection()
        return super().eventFilter(source, event)

    def clear_bbox_selection(self):
        self.label_panel.label_list.clearSelection()
        self.label_panel.set_current_label("")
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
        old_label = item.data(Qt.UserRole)
        new_label = self.label_handler.edit_label_dialog(old_label)
        if new_label:
            # Determine if we're in individual (non-group) mode by presence of index
            index = item.data(Qt.UserRole + 1)
            if index is not None:  # Individual annotation item
                # Select the annotation then rename via handler API
                self.ann_handler.select_annotation(index)
                self.ann_handler.rename_selected_annotation(new_label)
            else:  # Group mode item: bulk rename
                self.ann_handler.rename_annotations_by_label(old_label, new_label)

    def delete_label(self, item):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirm Delete")
        index = item.data(Qt.UserRole + 1)
        if index is not None:  # Individual mode
            msg_box.setText(f"Delete annotation '{item.text()}'?")
        else:
            label = item.data(Qt.UserRole)
            count = sum(1 for ann in (self.ann_handler.annotations or []) if getattr(ann, 'label', ann.get('label') if isinstance(ann, dict) else None) == label)
            msg_box.setText(f"Delete all {count} annotations with label '{label}'?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        if msg_box.exec_() == QMessageBox.Yes:
            if index is not None and index >= 0:
                # Only allow deletion of currently selected annotation per new logic
                if self.ann_handler.selected_index != index:
                    # Attempt to select it first; if fails abort
                    try:
                        self.ann_handler.select_annotation(index)
                    except IndexError:
                        self.logger.warning(f"[BBoxAnnotationTool] Annotation index {index} invalid for deletion", "Annotations")
                        return
                # Proceed to delete selected
                self.ann_handler.delete_selected_annotation()
            else:
                # Bulk delete by label (group mode)
                label = item.data(Qt.UserRole)
                self.ann_handler.delete_annotations_by_label(label)
            # Refresh UI lists
            self.label_handler.update_label_list(
                self.label_panel.label_list,
                self.label_panel.group_labels_cb.isChecked()
            )
            self.label_panel.clear_selection()
            self.update_display()

    def navigate_to_image(self, direction):
        """Navigate to next/previous image using ImageHandler
        direction: 1 for next, -1 for previous"""
        if not self.ann_handler.check_unsaved_changes():
            return
        
        # Check if we have images available
        if not self.image_handler.image_paths:
            self.logger.debug("[BBoxAnnotationTool] No images available for navigation", "Navigation")
            return
            
        try:
            if direction == 1:
                self.image_handler.go_to_next_image()
            elif direction == -1:
                self.image_handler.go_to_previous_image()
        except (ValueError, IndexError) as e:
            # No more images in that direction or no images loaded
            self.logger.debug(f"[BBoxAnnotationTool] Navigation failed: {str(e)}", "Navigation")

    def on_image_changed(self, image):
        """Handle image change from ImageHandler."""
        self.update_display()
        if image is not None:
            self.logger.debug(f"[BBoxAnnotationTool] Image loaded with shape: {image.shape}", "Image")

    def on_image_path_changed(self, image_path):
        """Handle image path change from ImageHandler."""
        if image_path:
            self.cancel_current_action()
            # Set annotation path which will trigger loading
            output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            ann_path = str(Path(output_dir) / f"{Path(image_path).stem}.json")
            self.ann_handler.current_ann_path = ann_path
            self.label_panel.update_used_labels(self.label_handler.get_all_unique_labels())
            
            # Update file list selection to match current image
            if self.image_handler.image_paths:
                for i in range(self.label_panel.file_list.count()):
                    item = self.label_panel.file_list.item(i)
                    if item.text() == Path(image_path).name:
                        self.label_panel.file_list.setCurrentRow(i)
                        break
        else:
            self.ann_handler.reset()

    def on_image_paths_changed(self, image_paths):
        """Handle image paths change from ImageHandler."""
        if image_paths:
            # Get annotated files
            annotated_files = set()
            output_dir = self.settings.value("output_dir", os.path.join(os.getcwd(), "output"))
            for file_path in image_paths:
                ann_path = str(Path(output_dir) / f"{Path(file_path).stem}.json")
                if Path(ann_path).exists():
                    annotated_files.add(file_path)
            
            self.label_panel.update_file_list(image_paths, annotated_files)
    
def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationVersion(__version__)  # Set our application version
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon_original.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = BBoxAnnotationTool()
    window.logger.info("=== Application Started ===", "Session")
    window.logger.info(f"Python Version: {sys.version}", "System")
    window.logger.info(f"Application Version: {QApplication.applicationVersion()}", "System")
    window.logger.info(f"Qt Version: {qVersion()}", "System")
    window.logger.info(f"PyQt5 Version: {PYQT_VERSION_STR}", "System")
    window.logger.info(f"OpenCV Version: {cv2.__version__}", "System")
    
    # Register cleanup
    app.aboutToQuit.connect(lambda: window.logger.info("=== Application Shutting Down ===", "Session"))
    
    window.show()
    sys.exit(app.exec_())
