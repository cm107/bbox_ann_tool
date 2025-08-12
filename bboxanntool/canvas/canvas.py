from __future__ import annotations
import cv2
import numpy as np
import numpy.typing as npt
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from .viewport import Viewport

class Canvas(QLabel):
    imageChanged = pyqtSignal(np.ndarray)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._image: npt.NDArray[np.uint8] | None = None
        self._viewport: Viewport | None = None

        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(500, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable mouse tracking to handle zoom and pan interactions
        self.setMouseTracking(True)

        # Mouse-related
        # Drag state: only keep image anchor point
        self._dragAnchorImage: npt.NDArray[np.float32] | None = None
        self._last_qimage: QImage | None = None  # keep reference so data not freed

    @property
    def viewport(self) -> Viewport:
        if self._viewport is None:
            size = self.size()
            size = np.array([size.width(), size.height()], dtype=np.int32)
            self._viewport = Viewport(size=size, bgColor=(0, 0, 0), parent=self)
            self._viewport.modified.connect(self.render)
        return self._viewport

    @property
    def image(self) -> npt.NDArray[np.uint8]:
        if self._image is not None:
            return self._image
        else:
            return np.zeros((500, 500, 3), dtype=np.uint8)

    @image.setter
    def image(self, value: npt.NDArray[np.uint8] | None):
        self._image = value
        self.viewport.setup_canvas_for_image(value)  # emits modified -> render
        self.imageChanged.emit(self._image)

    def render(self):
        if self._image is None:
            return
        rendered_image = self.viewport.crop_and_resize(self._image)
        # Convert BGR->RGB and ensure contiguous memory
        rgb = cv2.cvtColor(rendered_image, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        h, w, _ = rgb.shape
        bytes_per_line = 3 * w
        qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        # Detach to own memory so numpy buffer lifetime not an issue
        qimage = qimage.copy()
        self._last_qimage = qimage
        qpixmap = QPixmap.fromImage(qimage)
        self.setPixmap(qpixmap)
        self.update()

    def wheelEvent(self, event):
        """
        Handle mouse wheel events for zooming in and out.
        """
        if self._image is None:
            return

        # Determine the zoom factor
        delta = event.angleDelta().y()
        if delta == 0:
            return

        # Typical zoom step
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Get mouse position relative to the widget
        pos = event.pos()
        center = np.array([pos.x(), pos.y()], dtype=np.float32)

        # Adjust zoom in the viewport (signal triggers render)
        self.viewport.zoom(zoom_factor, center=center)

    def mousePressEvent(self, event):
        """
        Handle mouse press events for panning.
        """
        if event.button() == Qt.LeftButton:
            start_v = np.array([event.x(), event.y()], dtype=np.float32)
            try:
                self._dragAnchorImage = self.viewport.viewport_to_image_coords(start_v)
            except ValueError:
                self._dragAnchorImage = None
    
    def mouseMoveEvent(self, event):
        """
        Handle mouse move events for panning.
        """
        if self._dragAnchorImage is not None:
            cursor_v = np.array([event.x(), event.y()], dtype=np.float32)
            zs = self.viewport.zoomScale
            size_f = self.viewport.size.astype(np.float32)
            new_offset = self._dragAnchorImage - (cursor_v - size_f / 2.0) / zs
            self.viewport.set_offset(new_offset)
    
    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events to stop panning.
        """
        if event.button() == Qt.LeftButton:
            self._dragAnchorImage = None
    
    def resizeEvent(self, event):
        """
        Handle resize events to adjust the viewport size.
        """
        super().resizeEvent(event)
        size = np.array([self.width(), self.height()], dtype=np.int32)
        self.viewport.size = size  # emits modified -> render
