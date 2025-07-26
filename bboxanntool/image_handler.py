import os
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import cv2

from .logger import logger

class ImageHandler(QObject):
    # Signals
    image_directory_changed = pyqtSignal(str)  # Emitted when the image directory changes
    image_paths_changed = pyqtSignal(list)  # Emitted when the list of image paths changes
    image_index_changed = pyqtSignal(int)  # Emitted when the image index changes
    current_image_path_changed = pyqtSignal(str)  # Emitted when the current image path changes
    current_image_changed = pyqtSignal(np.ndarray)  # Emitted
    state_reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # State variables
        self._image_directory: str | None = None
        self._image_paths: list[str] | None = None
        self._image_index: int | None = None
        self._current_image_path: str | None = None
        self._current_image: np.ndarray | None = None

        # Connections
        self.image_directory_changed.connect(
            lambda value: logger.debug(f"[ImageHandler] Changed image directory: {value}")
        )
        self.image_paths_changed.connect(
            lambda paths: logger.debug(f"[ImageHandler] Image paths updated: {len(paths)} images found")
        )
        self.current_image_path_changed.connect(
            lambda path: logger.debug(f"[ImageHandler] Current image path changed: {path}")
        )
        self.current_image_changed.connect(
            lambda img: logger.debug(f"[ImageHandler] Current image loaded with shape: {img.shape if img is not None else 'None'}")
        )

        logger.debug("[ImageHandler] Initialized", "Init")
    
    def _reset(self):
        """Reset the image handler state."""
        self._image_directory = None
        self._image_paths = None
        self._image_index = None
        self._current_image_path = None
        self._current_image = None
    
    def reset(self):
        """Reset the image handler state."""
        self._reset()
        self.state_reset.emit()

    @property
    def image_directory(self) -> str | None:
        return self._image_directory
    
    @image_directory.setter
    def image_directory(self, value: str | None):
        if not os.path.isdir(value):
            logger.error(f"[ImageHandler] Invalid image directory: {value}", "Error")
            raise ValueError(f"Invalid image directory: {value}")
        self._reset()
        self._image_directory = value
        self._load_image_paths()
        if len(self._image_paths) == 0:
            logger.warning("[ImageHandler] No images found in the specified directory", "Warning")

        self.image_directory_changed.emit(value)

    def _load_image_paths(self):
        self._image_paths = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif']:
            self._image_paths.extend(Path(self._image_directory).glob(ext))
            self._image_paths.extend(Path(self._image_directory).glob(ext.upper()))
        self._image_paths = [str(f) for f in self._image_paths]
        self._image_paths.sort()

        self.image_paths_changed.emit(self._image_paths)
    
    @property
    def image_paths(self) -> list[str] | None:
        """List of image paths in the current directory."""
        return self._image_paths
    
    @property
    def image_index(self) -> int | None:
        """Index of the currently selected image."""
        return self._image_index
    
    @image_index.setter
    def image_index(self, value: int | None):
        if value is None or (
            self._image_paths is not None
            and 0 <= value < len(self._image_paths)
        ):
            self._image_index = value
            if value is not None:
                self.current_image_path = self._image_paths[value]
            else:
                self.current_image_path = None
            self.image_index_changed.emit(value)
        else:
            if self._image_paths is not None:
                logger.error(f"[ImageHandler] Invalid image index: {value}. {len(self.image_paths)=}", "Error")
                raise IndexError(f"Invalid image index: {value}")
            else:
                logger.error("[ImageHandler] No image paths available to set index", "Error")
                raise ValueError("No image paths available to set index")

    def go_to_first_image(self):
        """Go to the first image in the list."""
        if self._image_paths:
            self.image_index = 0
        else:
            logger.warning("[ImageHandler] Can't go to first image when none are available.", "Warning")

    def go_to_last_image(self):
        """Go to the last image in the list."""
        if self._image_paths:
            self.image_index = len(self._image_paths) - 1
        else:
            logger.warning("[ImageHandler] Can't go to last image when none are available.", "Warning")

    def go_to_next_image(self):
        """Go to the next image in the list."""
        if not self._image_paths:
            logger.warning("[ImageHandler] Can't go to next image when none are available.", "Warning")
            return
            
        if self._image_index is None:
            # If no image is currently selected, start with the first one
            self.image_index = 0
        elif self._image_index < len(self._image_paths) - 1:
            self.image_index += 1
        else:
            logger.debug("[ImageHandler] Already at the last image.", "Navigation")

    def go_to_previous_image(self):
        """Go to the previous image in the list."""
        if not self._image_paths:
            logger.warning("[ImageHandler] Can't go to previous image when none are available.", "Warning")
            return
            
        if self._image_index is None:
            # If no image is currently selected, start with the last one
            self.image_index = len(self._image_paths) - 1
        elif self._image_index > 0:
            self.image_index -= 1
        else:
            logger.debug("[ImageHandler] Already at the first image.", "Navigation")

    @property
    def current_image_path(self) -> str | None:
        """Path of the currently loaded image."""
        return self._current_image_path
    
    @current_image_path.setter
    def current_image_path(self, value: str | None):
        if value is not None and not os.path.isfile(value):
            logger.error(f"[ImageHandler] Invalid image path: {value}", "Error")
            raise ValueError(f"Invalid image path: {value}")
        self._current_image_path = value
        self._load_current_image()

        self.current_image_path_changed.emit(value)
    
    def _load_current_image(self):
        """Load the current image from the specified path."""
        if self._current_image_path is None:
            self._current_image = None
            return
        
        try:
            self._current_image = cv2.imread(self._current_image_path)
            if self._current_image is None:
                logger.error(f"[ImageHandler] Failed to load image: {self._current_image_path}", "Error")
                raise ValueError(f"Failed to load image: {self._current_image_path}")
            self.current_image_changed.emit(self._current_image)
        except Exception as e:
            logger.error(f"[ImageHandler] Error loading image: {e}", "Error")
            raise e
    
    @property
    def current_image(self) -> np.ndarray | None:
        """Current image as a NumPy array."""
        return self._current_image
