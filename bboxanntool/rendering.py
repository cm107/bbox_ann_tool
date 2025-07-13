"""Image renderer for drawing annotations."""

import cv2
from PyQt5.QtGui import QColor

class ImageRenderer:
    def __init__(self, settings):
        self.settings = settings

    def render_image(self, original_image, annotations, selected_label=None, 
                    selected_index=None, group_mode=False, edit_mode=False):
        """Render the image with annotations."""
        if original_image is None:
            return None

        image_to_display = original_image.copy()
        bbox_color = QColor(self.settings.value("bbox_color", "#FF0000"))
        bgr_color = (bbox_color.blue(), bbox_color.green(), bbox_color.red())

        # Get appearance settings
        line_width = int(self.settings.value("bbox_line_width", 2))
        selected_color = QColor(self.settings.value("bbox_selected_color", "#00FF00"))
        selected_bgr = (selected_color.blue(), selected_color.green(), selected_color.red())
        label_color = QColor(self.settings.value("label_color", "#000000"))
        label_bgr = (label_color.blue(), label_color.green(), label_color.red())
        label_size = float(self.settings.value("label_font_size", 12)) / 24.0

        for i, bbox in enumerate(annotations):
            color = bgr_color
            # Highlight if either:
            # 1. In group mode and this bbox matches the selected label
            # 2. Not in group mode and this bbox is the selected index
            if (group_mode and bbox["label"] == selected_label) or (not group_mode and i == selected_index):
                color = selected_bgr
                
            x1, y1, x2, y2 = bbox["bbox"]
            cv2.rectangle(image_to_display, (x1, y1), (x2, y2), color, line_width)
            
            # Draw label
            cv2.putText(image_to_display, bbox["label"], (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, label_size, label_bgr, 
                       max(1, line_width // 2))
            
            # In edit mode, draw control points
            if edit_mode:
                self._draw_control_points(image_to_display, x1, y1, x2, y2)

        return image_to_display

    def render_preview(self, original_image, existing_annotations, start_point, 
                      end_point, current_label):
        """Render a preview during bbox drawing."""
        if original_image is None:
            return None

        temp_image = original_image.copy()
        bbox_color = QColor(self.settings.value("bbox_color", "#FF0000"))
        bgr_color = (bbox_color.blue(), bbox_color.green(), bbox_color.red())
        
        # Draw existing bboxes
        for bbox in existing_annotations:
            x1, y1, x2, y2 = bbox["bbox"]
            cv2.rectangle(temp_image, (x1, y1), (x2, y2), bgr_color, 2)
            cv2.putText(temp_image, bbox["label"], (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 1)
        
        # Draw current bbox
        x1, y1 = start_point
        x2, y2 = end_point
        cv2.rectangle(temp_image, (x1, y1), (x2, y2), bgr_color, 2)
        if current_label:
            cv2.putText(temp_image, current_label, (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_color, 1)
        
        return temp_image

    def _draw_control_points(self, image, x1, y1, x2, y2):
        """Draw control points for a bbox in edit mode."""
        points = [
            (x1, y1),  # Top-left
            (x2, y1),  # Top-right
            (x2, y2),  # Bottom-right
            (x1, y2),  # Bottom-left
            ((x1 + x2) // 2, (y1 + y2) // 2)  # Center
        ]
        
        point_color = QColor(self.settings.value("points_color", "#0000FF"))
        point_bgr = (point_color.blue(), point_color.green(), point_color.red())
        point_size = int(self.settings.value("points_size", 6))
        
        # Draw corner points as squares
        for px, py in points[:-1]:
            half = point_size // 2
            cv2.rectangle(image, 
                        (px - half, py - half),
                        (px + half, py + half),
                        point_bgr, -1)
        
        # Draw center point as circle
        cx, cy = points[-1]
        cv2.circle(image, (cx, cy), 
                  point_size // 2, point_bgr, -1)
