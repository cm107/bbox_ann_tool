"""Controllers for mouse interaction modes."""

from PyQt5.QtCore import QObject, pyqtSignal
from .logger import logger

class DrawingController(QObject):
    """Controls drawing mode interactions."""
    bbox_created = pyqtSignal(list, str)  # bbox coordinates and label

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.drawing = False
        self.start_point = None
        self.end_point = None

    def start_drawing(self, point):
        """Start drawing a new bbox."""
        self.drawing = True
        self.start_point = point
        self.end_point = point

    def update_drawing(self, point):
        """Update the current drawing."""
        if self.drawing:
            self.end_point = point
            return True
        return False

    def finish_drawing(self, point, label):
        """Finish drawing and create the bbox if a label is provided."""
        if not self.drawing or not label:
            self.drawing = False
            return False

        self.drawing = False
        self.end_point = point
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        bbox = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        self.bbox_created.emit(bbox, label)
        if logger:
            logger.info(f"[DrawingController] Created bbox {bbox} with label '{label}'", "Annotations")
        return True

    def get_current_bbox(self):
        """Get the current bbox being drawn."""
        if not self.drawing or not all([self.start_point, self.end_point]):
            return None
        return self.start_point, self.end_point

class EditingController(QObject):
    """Controls edit mode interactions."""
    bbox_modified = pyqtSignal(int, list)  # bbox index and new coordinates

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.dragging = False
        self.drag_start = None
        self.selected_point = None
        self.point_size = int(settings.value("points_size", 6))
        self.initial_bbox = None  # Store initial bbox for logging

    def find_control_point(self, click_pos, annotations):
        """Find which control point was clicked."""
        click_x, click_y = click_pos
        
        for bbox_idx, bbox_data in enumerate(annotations):
            x1, y1, x2, y2 = bbox_data["bbox"]
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            points = [
                (x1, y1),  # Top-left (0)
                (x2, y1),  # Top-right (1)
                (x2, y2),  # Bottom-right (2)
                (x1, y2),  # Bottom-left (3)
                center     # Center (4)
            ]
            
            for point_idx, (px, py) in enumerate(points):
                if abs(px - click_x) <= self.point_size and abs(py - click_y) <= self.point_size:
                    return bbox_idx, point_idx
        
        return None

    def start_dragging(self, point, selection):
        """Start dragging a control point."""
        if selection is None:
            return False
        
        bbox_idx, point_idx = selection
        self.dragging = True
        self.drag_start = point
        self.selected_point = selection
        
        # Store initial bbox for logging
        if logger:
            point_names = ['top-left', 'top-right', 'bottom-right', 'bottom-left', 'center']
            self.initial_bbox = point_idx, point_names[point_idx]
        return True

    def update_dragging(self, point, annotations):
        """Update the dragged bbox."""
        if not self.dragging or self.selected_point is None:
            return False

        bbox_idx, point_idx = self.selected_point
        if bbox_idx >= len(annotations):
            return False

        bbox = annotations[bbox_idx]["bbox"]
        x1, y1, x2, y2 = bbox
        dx = point[0] - self.drag_start[0]
        dy = point[1] - self.drag_start[1]
        
        if point_idx == 4:  # Center point - move entire bbox
            x1, x2 = x1 + dx, x2 + dx
            y1, y2 = y1 + dy, y2 + dy
        else:  # Corner point - resize bbox
            if point_idx == 0:    # Top-left
                x1, y1 = point
            elif point_idx == 1:  # Top-right
                x2, y1 = point
            elif point_idx == 2:  # Bottom-right
                x2, y2 = point
            elif point_idx == 3:  # Bottom-left
                x1, y2 = point
        
        # Update bbox with new coordinates
        new_bbox = [
            min(x1, x2), min(y1, y2),
            max(x1, x2), max(y1, y2)
        ]
        self.bbox_modified.emit(bbox_idx, new_bbox)
        self.drag_start = point
        return True

    def finish_dragging(self):
        """Finish dragging operation."""
        if self.dragging and logger and self.initial_bbox:
            point_idx, point_name = self.initial_bbox
            if point_idx == 4:
                logger.info(f"[EditingController] Moved bbox {self.selected_point[0]} by dragging center point", "Annotations")
            else:
                logger.info(f"[EditingController] Resized bbox {self.selected_point[0]} by dragging {point_name} point", "Annotations")
        
        self.dragging = False
        self.drag_start = None
        self.selected_point = None
        self.initial_bbox = None
