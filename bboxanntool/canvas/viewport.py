from __future__ import annotations
import cv2
import numpy as np
import numpy.typing as npt
from PyQt5.QtCore import QObject, pyqtSignal
from ..bbox import BBox

class Viewport(QObject):
    modified = pyqtSignal()

    def __init__(
        self,
        size: npt.NDArray[np.int32],
        bgColor: tuple[int, int, int] = (0, 0, 0),
        parent: QObject | None = None
    ):
        super().__init__(parent)

        self._size = size
        """
        Size of the space allocated to the Widget in the GUI.
        This is the size of the viewport in pixels, not the size of the canvas.
        """

        self._bgColor = bgColor
        """
        Background color of the viewport.
        This is used to fill the viewport when the canvas is smaller than the viewport.
        The color is in BGR format.
        """

        # Non-constructor attributes        
        self._canvasSize: npt.NDArray[np.int32] | None = None
        """
        Size of canvas coordinate system that is used to draw stuff.
        The Canvas is scaled according to the zoomScale, offset to the region of interest,
        cropped, and then padded to fit the viewport.
        """
        self._zoomScale: float | None = None
        """
        Cumulative scale magnification calculated when zooming in or out.
        """
        self._offset: npt.NDArray[np.int32] | None = None
        """
        Offset in pixels from the top-left corner of the canvas to the center of the viewport.
        """
    
    @property
    def size(self) -> npt.NDArray[np.int32] | None:
        """
        Size of the space allocated to the Widget in the GUI.
        This is the size of the viewport in pixels, not the size of the canvas.
        """
        return self._size
    
    @size.setter
    def size(self, value: npt.NDArray[np.int32]):
        if value is not None:
            if not isinstance(value, np.ndarray):
                raise TypeError("Size must be a numpy array.")
            if value.dtype != np.int32:
                raise TypeError("Size must be a numpy array of type int32.")
            if value.shape != (2,):
                raise ValueError("Size must be a 1D array with two elements.")

        if not np.array_equal(self._size, value):
            self._size = value
            self.modified.emit()

    @property
    def bgColor(self) -> tuple[int, int, int]:
        """
        Background color of the viewport.
        This is used to fill the viewport when the canvas is smaller than the viewport.
        The color is in BGR format.
        """
        return self._bgColor
    
    @bgColor.setter
    def bgColor(self, value: tuple[int, int, int]):
        if not isinstance(value, tuple):
            raise TypeError("Background color must be a tuple.")
        if len(value) != 3:
            raise ValueError("Background color must be a tuple of three elements.")
        if not all(isinstance(c, int) for c in value):
            raise TypeError("All elements of background color must be integers.")
        if not all(0 <= c <= 255 for c in value):
            raise ValueError("All elements of background color must be in the range [0, 255].")
        if self._bgColor != value:
            self._bgColor = value
            self.modified.emit()

    @property
    def canvasSize(self) -> npt.NDArray[np.int32]:
        """
        Size of canvas coordinate system that is used to draw stuff.
        The Canvas is scaled according to the zoomScale, offset to the region of interest,
        cropped, and then padded to fit the viewport.

        Readonly.
        """
        if self._canvasSize is None:
            raise ValueError("Cannot access canvas size before setting up the canvas for an image.")
        return self._canvasSize
    
    @property
    def zoomScale(self) -> float:
        """
        Cumulative scale magnification calculated when zooming in or out.

        Readonly.
        """
        if self._zoomScale is None:
            raise ValueError("Cannot access zoom scale before setting up the canvas for an image.")
        return self._zoomScale

    @property
    def offset(self) -> npt.NDArray[np.int32]:
        """
        Offset in pixels from the top-left corner of the canvas to the center of the viewport.

        Readonly.
        """
        if self._offset is None:
            raise ValueError("Cannot access offset before setting up the canvas for an image.")
        return self._offset

    def setup_canvas_for_image(self, image: npt.NDArray[np.uint8] | None):
        if image is None:
            self._canvasSize = None
            self._zoomScale = None
            self._offset = None
        else:
            _val = np.array(image.shape[:2][::-1], dtype=np.int32)
            self._canvasSize = _val
            # compute zoomScale so whole image fits inside viewport
            vw, vh = self._size.astype(np.float32)
            iw, ih = self._canvasSize.astype(np.float32)
            if iw > 0 and ih > 0:
                scale_w = vw / iw
                scale_h = vh / ih
                self._zoomScale = min(scale_w, scale_h)  # may be <1 (zoomed out) or >1 (zoomed in)
            else:
                self._zoomScale = 1.0
            # center viewport on image
            self._offset = (self._canvasSize / 2).astype(np.int32)
        self.modified.emit()

    @property
    def roi(self) -> BBox:
        """
        Region of interest in the canvas, defined by the current zoom scale and offset.
        This is the area that will be rendered to the viewport.
        """
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            raise ValueError("Canvas is not set up for rendering. Call setup_canvas_for_image first.")
        
        # Calculate the region of interest in the canvas
        roi_x = int(self._offset[0] - (self.size[0] / (2 * self._zoomScale)))
        roi_y = int(self._offset[1] - (self.size[1] / (2 * self._zoomScale)))
        roi_width = int(self.size[0] / self._zoomScale)
        roi_height = int(self.size[1] / self._zoomScale)

        # Ensure ROI is within canvas bounds
        roi_x = max(0, min(roi_x, self.canvasSize[0] - roi_width))
        roi_y = max(0, min(roi_y, self.canvasSize[1] - roi_height))

        return BBox(
            p0=np.array([roi_x, roi_y], dtype=np.float32),
            p1=np.array([roi_x + roi_width, roi_y + roi_height], dtype=np.float32)
        )

    def image_to_viewport_coords(self, p: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Convert a point (x,y) in image/canvas coordinates to viewport pixel coordinates.
        Uses same scale/padding logic as crop_and_resize so the mapping matches what is displayed.
        """
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            raise ValueError("Canvas not set up.")
        if p.shape != (2,):
            raise ValueError("Point must be shape (2,)")
        roi = self.roi
        roi_x, roi_y = roi.p0.astype(np.float32)
        roi_w = roi.width
        roi_h = roi.height
        # scale chosen to fit entire ROI inside viewport preserving aspect
        vw, vh = self.size.astype(np.float32)
        scale = min(vw / roi_w, vh / roi_h)
        pad_x = (vw - roi_w * scale) / 2.0
        pad_y = (vh - roi_h * scale) / 2.0
        vx = (p[0] - roi_x) * scale + pad_x
        vy = (p[1] - roi_y) * scale + pad_y
        return np.array([vx, vy], dtype=np.float32)

    def viewport_to_image_coords(self, p: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Convert a point (x,y) in viewport pixel coordinates to image/canvas coordinates.
        Inverse of image_to_viewport_coords (within displayed region)."""
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            raise ValueError("Canvas not set up.")
        if p.shape != (2,):
            raise ValueError("Point must be shape (2,)")
        roi = self.roi
        roi_x, roi_y = roi.p0.astype(np.float32)
        roi_w = roi.width
        roi_h = roi.height
        vw, vh = self.size.astype(np.float32)
        scale = min(vw / roi_w, vh / roi_h)
        pad_x = (vw - roi_w * scale) / 2.0
        pad_y = (vh - roi_h * scale) / 2.0
        ix = (p[0] - pad_x) / scale + roi_x
        iy = (p[1] - pad_y) / scale + roi_y
        return np.array([ix, iy], dtype=np.float32)

    def crop_and_resize(self, img: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
        """
        Crop the image to the region of interest defined by the current zoom scale and offset,
        resize it, and pad it to fit the viewport size.
        Returns a numpy array of the resulting image.
        """
        # Create a blank image with the background color
        result = np.full((self.size[1], self.size[0], 3), self.bgColor, dtype=np.uint8)
        
        # Calculate the region of interest in the canvas
        roi = self.roi

        # Crop the canvas image and resize it to fit the viewport
        cropped_image = roi.crop(img)
        H, W = cropped_image.shape[:2]
        if H == 0 or W == 0:
            raise ValueError(f"Attempted to crop {roi} from an image of shape {img.shape}, resulting in an empty crop of shape {cropped_image.shape}.")
        wScale = self.size[0] / W
        hScale = self.size[1] / H
        scale = min(wScale, hScale)
        targetSize = (int(W * scale), int(H * scale))
        cropped_image = cv2.resize(
            cropped_image, targetSize,
            interpolation=cv2.INTER_LINEAR
        )
        H, W = cropped_image.shape[:2]
        wPad = (self.size[0] - W) // 2
        hPad = (self.size[1] - H) // 2
        if wPad < 0 or hPad < 0:
            x0 = max(0, -wPad)
            y0 = max(0, -hPad)
            x1 = x0 + self.size[0]
            y1 = y0 + self.size[1]
            cropped_image = cropped_image[y0:y1, x0:x1]
            H, W = cropped_image.shape[:2]
            wPad = max(0, wPad)
            hPad = max(0, hPad)
        result[hPad:hPad+H, wPad:wPad+W] = cropped_image
        return result

    def zoom(self, magnification: float, center: npt.NDArray[np.float32] | None = None):
        """
        Zoom in or out of the canvas.
        :param magnification: The zoom factor. > 1 to zoom in, < 1 to zoom out.
        :param center: The center point of the zoom. If None, zooms around the center of the viewport.
        """
        if magnification <= 0:
            raise ValueError("Magnification must be greater than 0.")
        if magnification == 1:
            return
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            raise ValueError("Canvas is not set up for zooming. Call setup_canvas_for_image first.")
        if center is None:
            center = np.array([self.size[0] / 2, self.size[1] / 2], dtype=np.float32)
        # canvas coord of focal point before zoom
        roi_half = (self.size / (2 * self._zoomScale))
        center_canvas = self._offset - roi_half + (center / self._zoomScale)
        # apply zoom
        self._zoomScale *= magnification
        # recompute offset so focal point stays under cursor
        roi_half_new = (self.size / (2 * self._zoomScale))
        self._offset = (center_canvas - (center / self._zoomScale) + roi_half_new).astype(np.int32)
        self._clamp_offset()
        self.modified.emit()

    def _clamp_offset(self):
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            return
        half = (self.size / (2 * self._zoomScale)).astype(np.int32)
        min_off = half
        max_off = self._canvasSize - half
        max_off = np.maximum(min_off, max_off)  # handle small images
        self._offset = np.clip(self._offset, min_off, max_off)

    def set_offset(self, value: npt.NDArray[np.float32]):
        """Set offset (canvas center) using float precision, clamp to valid range, emit modified if changed."""
        if self._canvasSize is None or self._zoomScale is None:
            return
        value = value.astype(np.float32)
        half = self.size.astype(np.float32) / (2 * self._zoomScale)
        min_off = half
        max_off = self._canvasSize.astype(np.float32) - half
        max_off = np.maximum(min_off, max_off)  # handle very small images
        clamped = np.clip(value, min_off, max_off)
        new_offset = clamped.astype(np.int32)
        if self._offset is None or not np.array_equal(new_offset, self._offset):
            self._offset = new_offset
            self.modified.emit()

    def pan(self, dx: int, dy: int):
        """
        Pan the canvas by a certain amount.
        :param dx: The amount to pan in the x direction.
        :param dy: The amount to pan in the y direction.
        """
        if self._canvasSize is None or self._zoomScale is None or self._offset is None:
            raise ValueError("Canvas is not set up for panning. Call setup_canvas_for_image first.")
        delta = np.array([dx, dy], dtype=np.float32) / self._zoomScale
        # subtract because dragging mouse right should move image left (content follows cursor anchor)
        self._offset = (self._offset - delta).astype(np.int32)
        self._clamp_offset()
        self.modified.emit()
