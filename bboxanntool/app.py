"""Main application window for BBox Annotation Tool."""

import sys
import cv2
import os
from pathlib import Path

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
            ann_handler=self.ann_handler
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
        self.ann_handler.setup()
        
        # Connect image handler signals
        self.image_handler.current_image_changed.connect(self.on_image_changed)
        self.image_handler.current_image_path_changed.connect(self.on_image_path_changed)
        self.image_handler.image_paths_changed.connect(self.on_image_paths_changed)
        
        # Connect handler signals
        self.ann_handler.annotations_changed.connect(self.on_annotations_changed)
        self.ann_handler.bbox_modified.connect(self.update_display)
        self.ann_handler.selection_changed.connect(self.on_annotation_selected)
        self.ann_handler.unsaved_changes.connect(self.on_unsaved_changes)
        
        self.label_handler.label_changed.connect(self.on_label_changed)
        self.label_handler.label_renamed.connect(self.ann_handler.rename_label)
        
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
        self.drawing_controller.bbox_created.connect(self.ann_handler.add_annotation)
        self.editing_controller.bbox_modified.connect(self.ann_handler.update_annotation)

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
        if self.ann_handler.save_annotations():
            # Update file list icon
            image_path = self.image_handler.current_image_path
            if image_path:
                for i in range(self.label_panel.file_list.count()):
                    item = self.label_panel.file_list.item(i)
                    if item.text() == Path(image_path).name:
                        item.setIcon(QIcon.fromTheme("dialog-ok"))
                        break
                
                self.logger.status(f"[BBoxAnnotationTool] Saved annotations for {Path(image_path).name}")
                self.logger.info(f"[BBoxAnnotationTool] Saved annotations to {self.ann_handler.get_annotation_path()}", "FileOps")

    def update_display(self):
        """Update the display with current annotations."""
        current_image = self.image_handler.current_image
        if current_image is None:
            self.image_panel.display_image(None)
            return

        # Handle preview during drawing
        if self.drawing_controller.drawing:
            start_point, end_point = self.drawing_controller.get_current_bbox()
            preview = self.renderer.render_preview(
                current_image,
                self.ann_handler.annotations,
                start_point,
                end_point,
                self.label_panel.get_current_label()
            )
            self.image_panel.display_image(preview)
            return

        # Normal display with annotations
        image = self.renderer.render_image(
            current_image,
            self.ann_handler.annotations,
            self.label_handler.current_label,
            self.ann_handler.selected_index,
            self.label_panel.group_labels_cb.isChecked(),
            self.editing_controller.dragging or self.image_panel.mode_selector.currentText() == "Edit Mode"
        )
        self.image_panel.display_image(image)

    def set_mode(self, edit_mode):
        """Set the current mode (edit/draw)."""
        self.image_panel.set_mode(edit_mode)
        self.cancel_current_action()
        mode = "Edit" if edit_mode else "Draw"
        self.logger.status(f"[BBoxAnnotationTool] Switched to {mode} Mode")

    def cancel_current_action(self):
        """Cancel the current drawing/editing action."""
        if self.drawing_controller.drawing:
            self.drawing_controller.drawing = False
        if self.editing_controller.dragging:
            self.editing_controller.finish_dragging()
        self.label_panel.clear_selection()
        self.update_display()

    def select_existing_label(self, label):
        """Select an existing label from the list."""
        self.label_handler.current_label = label
        self.label_panel.set_current_label(label)

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
            if item.data(Qt.UserRole + 1) is not None:  # Individual mode
                self.ann_handler.update_annotation(
                    item.data(Qt.UserRole + 1), 
                    label=new_label
                )
            else:  # Group mode
                self.ann_handler.rename_label(old_label, new_label)

    def delete_label(self, item):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Confirm Delete")
        
        index = item.data(Qt.UserRole + 1)
        if index is not None:  # Individual mode
            msg_box.setText(f"Delete annotation '{item.text()}'?")
        else:  # Group mode
            label = item.data(Qt.UserRole)
            count = sum(1 for ann in self.ann_handler.annotations if ann["label"] == label)
            msg_box.setText(f"Delete all {count} annotations with label '{label}'?")
        
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        if msg_box.exec_() == QMessageBox.Yes:
            if index is not None and index >= 0:  # Individual mode and valid index
                # Get the text before deleting the annotation, as the item might be deleted
                # by the signal chain
                item_text = item.text()
                self.ann_handler.delete_annotation(index)
                self.logger.status(f"[BBoxAnnotationTool] Deleted annotation: {item_text}")
                self.logger.info(f"[BBoxAnnotationTool] Deleted single annotation: {item_text}", "Annotations")
            elif index is None:  # Group mode
                label = item.data(Qt.UserRole)
                count_before = len(self.ann_handler.annotations)
                self.ann_handler.delete_annotations_by_label(label)
                count_deleted = count_before - len(self.ann_handler.annotations)
                self.logger.status(f"[BBoxAnnotationTool] Deleted {count_deleted} annotations with label: {label}")
                self.logger.info(f"[BBoxAnnotationTool] Deleted {count_deleted} annotations with label: {label}", "Annotations")

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

    def on_annotation_selected(self, index, label):
        """Handle selection change from AnnotationHandler"""
        if index >= 0:
            # Update label list selection
            for i in range(self.label_panel.label_list.count()):
                item = self.label_panel.label_list.item(i)
                if item.data(Qt.UserRole + 1) == index:
                    self.label_panel.label_list.setCurrentItem(item)
                    break
        else:
            self.label_panel.label_list.clearSelection()
        self.update_display()
    
    def on_unsaved_changes(self, has_changes):
        """Handle unsaved changes state from AnnotationHandler"""
        self.setWindowTitle(f"BBox Annotation Tool {'*' if has_changes else ''}")
    
    def on_label_changed(self, label):
        """Handle current label change from LabelHandler"""
        self.label_panel.set_current_label(label)
    
    def on_image_changed(self, image):
        """Handle image change from ImageHandler."""
        self.update_display()
        if image is not None:
            self.logger.debug(f"[BBoxAnnotationTool] Image loaded with shape: {image.shape}", "Image")

    def on_image_path_changed(self, image_path):
        """Handle image path change from ImageHandler."""
        if image_path:
            self.cancel_current_action()
            self.ann_handler.load_annotations(image_path)
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
            for file_path in image_paths:
                if Path(self.ann_handler.get_annotation_path(file_path)).exists():
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
