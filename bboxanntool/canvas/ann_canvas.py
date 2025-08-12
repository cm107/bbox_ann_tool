from __future__ import annotations
import cv2
import numpy as np
import numpy.typing as npt
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage, QPixmap

from .canvas import Canvas

class AnnotationCanvas(Canvas):
    """Canvas capable of rendering annotations respecting the current Viewport.

    Features:
    - Ctrl + Mouse Wheel: zoom in/out around cursor
    - Ctrl + Left Mouse Drag: pan
    - Left mouse (no Ctrl) used for drawing / editing (delegated to controllers)
    - Annotations stored in image coordinates; converted to viewport coords for rendering
    - Skip drawing annotations completely outside viewport; clip partially visible
    - Shows preview bbox while drawing or editing
    """

    def __init__(self,
                 settings,
                 drawing_controller=None,
                 editing_controller=None,
                 ann_handler=None,
                 label_handler=None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.settings = settings
        self.drawing_controller = drawing_controller
        self.editing_controller = editing_controller
        self.ann_handler = ann_handler
        self.label_handler = label_handler

        # State used for rendering
        self._annotations: list | None = None  # list of annotation.BBox objects
        self._selected_index: int | None = None
        self._selected_label: str | None = None
        self._group_mode: bool = False
        self._edit_mode: bool = False
        self._drag_preview_index: int | None = None
        self._drag_preview_bbox: list[int] | None = None  # [x1,y1,x2,y2] in image coords
        self._drawing_preview: tuple[tuple[int, int], tuple[int, int]] | None = None

        # Internal flag to track if we are panning (Ctrl + Left drag)
        self._panning = False

    # ---------------- Public API -----------------
    def set_scene_state(self,
                        annotations,
                        selected_index: int | None,
                        selected_label: str | None,
                        group_mode: bool,
                        edit_mode: bool,
                        drag_preview_index: int | None,
                        drag_preview_bbox: list[int] | None,
                        drawing_preview: tuple[tuple[int, int], tuple[int, int]] | None):
        self._annotations = annotations
        self._selected_index = selected_index
        self._selected_label = selected_label
        self._group_mode = group_mode
        self._edit_mode = edit_mode
        self._drag_preview_index = drag_preview_index
        self._drag_preview_bbox = drag_preview_bbox
        self._drawing_preview = drawing_preview
        # Re-render with new state
        self.render()

    # --------------- Event Handling ---------------
    def wheelEvent(self, event):  # noqa: N802
        # Only zoom when Ctrl is held
        if event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
        else:
            event.ignore()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            # Start panning via base class logic
            self._panning = True
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            # Convert viewport -> image coords
            try:
                img_pt = self.viewport.viewport_to_image_coords(
                    np.array([event.x(), event.y()], dtype=np.float32)
                )
            except ValueError:
                return
            ix, iy = int(img_pt[0]), int(img_pt[1])
            if self._edit_mode and self.editing_controller:
                selection = self.editing_controller.find_control_point((ix, iy), self.ann_handler.annotations)
                if selection is not None:
                    self.editing_controller.start_dragging((ix, iy), selection)
                    self.ann_handler.select_annotation(selection[0])
                    self._drag_preview_index = selection[0]
                    self.render()
            else:  # Drawing mode
                if self.drawing_controller:
                    label = self.label_handler.current_label if self.label_handler else None
                    if label:
                        self.drawing_controller.start_drawing((ix, iy))
                        self._drawing_preview = ((ix, iy), (ix, iy))
                        self.render()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._panning:
            super().mouseMoveEvent(event)
            return
        # Drawing / editing interaction
        try:
            img_pt = self.viewport.viewport_to_image_coords(
                np.array([event.x(), event.y()], dtype=np.float32)
            )
        except ValueError:
            return
        ix, iy = int(img_pt[0]), int(img_pt[1])

        updated = False
        if self.drawing_controller and self.drawing_controller.drawing:
            if self.drawing_controller.update_drawing((ix, iy)):
                self._drawing_preview = (self.drawing_controller.start_point, self.drawing_controller.end_point)
                updated = True
        elif self.editing_controller and self.editing_controller.dragging:
            if self.editing_controller.update_dragging((ix, iy), self.ann_handler.annotations):
                # Preview is handled via handler signal; just store local preview bbox if available
                if self.editing_controller.current_drag_bbox is not None and self._drag_preview_index is not None:
                    self._drag_preview_bbox = self.editing_controller.current_drag_bbox
                updated = True
        if updated:
            self.render()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self._panning:
            self._panning = False
            super().mouseReleaseEvent(event)
            return
        if event.button() == Qt.LeftButton:
            try:
                img_pt = self.viewport.viewport_to_image_coords(
                    np.array([event.x(), event.y()], dtype=np.float32)
                )
            except ValueError:
                return
            ix, iy = int(img_pt[0]), int(img_pt[1])
            if self.drawing_controller and self.drawing_controller.drawing:
                label = self.label_handler.current_label if self.label_handler else None
                if label:
                    self.drawing_controller.finish_drawing((ix, iy), label)
                self._drawing_preview = None
            elif self.editing_controller and self.editing_controller.dragging:
                self.editing_controller.finish_dragging()
                self._drag_preview_bbox = None
                self._drag_preview_index = None
        super().mouseReleaseEvent(event)
        self.render()

    # --------------- Rendering ---------------
    def render(self):  # noqa: N802
        """Render image + annotations using current viewport state."""
        if self._image is None:
            self.setPixmap(QPixmap())
            return

        # Base cropped/resized image (BGR) padded to viewport size
        base_img = self.viewport.crop_and_resize(self._image)
        if base_img is None:
            return
        overlay = base_img.copy()
        h, w = overlay.shape[:2]

        # Appearance settings
        bbox_color = self._qcolor_to_bgr(self.settings.value("bbox_color", "#FF0000"))
        sel_color = self._qcolor_to_bgr(self.settings.value("bbox_selected_color", "#00FF00"))
        label_color = self._qcolor_to_bgr(self.settings.value("label_color", "#000000"))
        line_width = int(self.settings.value("bbox_line_width", 2))
        label_scale = float(self.settings.value("label_font_size", 12)) / 24.0
        point_color = self._qcolor_to_bgr(self.settings.value("points_color", "#0000FF"))
        point_size = int(self.settings.value("points_size", 6))

        # Build list of bbox annotations
        annotations = []
        if self._annotations is not None:
            for idx, ann in enumerate(self._annotations):
                if not hasattr(ann, 'p0') or not hasattr(ann, 'p1'):
                    continue
                x1, y1 = ann.p0
                x2, y2 = ann.p1
                if self._drag_preview_index == idx and self._drag_preview_bbox is not None:
                    x1, y1, x2, y2 = self._drag_preview_bbox
                annotations.append((idx, ann.label, int(x1), int(y1), int(x2), int(y2)))

        # Include drawing preview
        if self._drawing_preview:
            (sx, sy), (ex, ey) = self._drawing_preview
            dx1, dy1, dx2, dy2 = min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)
            label = self._selected_label or ""
            annotations.append((-1, label, dx1, dy1, dx2, dy2))

        for idx, label, x1, y1, x2, y2 in annotations:
            # Use unclamped coords for visibility test
            p0_v = self.viewport.image_to_viewport_coords(np.array([x1, y1], dtype=np.float32), clamp=False)
            p1_v = self.viewport.image_to_viewport_coords(np.array([x2, y2], dtype=np.float32), clamp=False)
            vx1, vy1 = p0_v
            vx2, vy2 = p1_v
            if vx1 > vx2:
                vx1, vx2 = vx2, vx1
            if vy1 > vy2:
                vy1, vy2 = vy2, vy1
            # Skip if completely outside (no intersection with [0,w]x[0,h])
            if vx2 < 0 or vy2 < 0 or vx1 > w or vy1 > h:
                continue
            # Draw using unclamped coordinates (as requested, do not clip)
            ix1, iy1, ix2, iy2 = int(vx1), int(vy1), int(vx2), int(vy2)
            color = bbox_color
            if (self._group_mode and label == self._selected_label) or (not self._group_mode and idx == self._selected_index):
                color = sel_color
            cv2.rectangle(overlay, (ix1, iy1), (ix2, iy2), color, line_width)
            if label:
                ty = int(vy1) - 5
                cv2.putText(overlay, label, (int(vx1), ty), cv2.FONT_HERSHEY_SIMPLEX, label_scale, label_color, max(1, line_width // 2), cv2.LINE_AA)
            if self._edit_mode and idx >= 0:
                self._draw_control_points(overlay, ix1, iy1, ix2, iy2, point_color, point_size)

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)
        bytes_per_line = 3 * w
        qimage = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        self._last_qimage = qimage
        self.setPixmap(QPixmap.fromImage(qimage))
        self.update()

    @staticmethod
    def _qcolor_to_bgr(value: str) -> tuple[int, int, int]:
        value = value.strip()
        if value.startswith('#') and len(value) == 7:
            r = int(value[1:3], 16)
            g = int(value[3:5], 16)
            b = int(value[5:7], 16)
            return (b, g, r)
        return (0, 0, 0)

    @staticmethod
    def _draw_control_points(img, x1, y1, x2, y2, color, size):
        half = size // 2
        corners = [
            (x1, y1), (x2, y1), (x2, y2), (x1, y2)
        ]
        for (cx, cy) in corners:
            cv2.rectangle(img, (cx - half, cy - half), (cx + half, cy + half), color, -1)
        cv2.circle(img, ((x1 + x2) // 2, (y1 + y2) // 2), max(1, size // 2), color, -1)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.render()

    def clear(self):
        self._annotations = None
        self._drawing_preview = None
        self._drag_preview_bbox = None
        self._drag_preview_index = None
        self.setPixmap(QPixmap())
        self._image = None

    def refresh(self):
        self.render()
