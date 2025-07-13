# Application Architecture

## Overview

The BBox Annotation Tool follows a modular architecture that separates concerns into specialized handler classes and controllers. This design improves maintainability and makes the code easier to understand and modify.

## Core Components

### BBoxAnnotationTool

The main application window class that:
- Creates and manages the UI
- Handles user input events
- Coordinates between different handlers and controllers
- Manages application-level settings and state
- Handles application-wide keyboard shortcuts

### AnnotationHandler

Responsible for all annotation-related operations:
- Managing the list of annotations for the current image
- Saving/loading annotations to/from files
- Creating, editing, and deleting annotations
- Tracking selected annotations
- Managing unsaved changes state

**Key Methods:**
- `load_annotations(image_path)`: Load annotations for a specific image
- `save_annotations()`: Save current annotations to file
- `add_annotation(bbox, label)`: Create a new annotation
- `update_annotation(index, bbox, label)`: Modify existing annotation
- `delete_annotation(index)`: Remove an annotation
- `select_annotation(index)`: Change the selected annotation

**Signals:**
- `annotations_changed`: Emitted when annotations list is modified
- `selection_changed`: Emitted when selected annotation changes
- `unsaved_changes`: Emitted when save state changes

### LabelHandler

Manages all label-related functionality:
- Maintaining current label state
- Managing the list of all used labels
- Handling label editing and deletion
- Coordinating label updates across annotations

**Key Methods:**
- `get_all_unique_labels()`: Get list of all labels used
- `edit_label_dialog(old_label)`: Show UI for editing a label
- `current_label` property: Get/set the active label

**Signals:**
- `label_changed`: Emitted when current label changes
- `label_deleted`: Emitted when a label is removed
- `label_renamed`: Emitted when a label is modified

### DrawingController

Manages drawing mode operations:
- Tracks the current drawing state
- Handles bbox creation workflow
- Validates drawing coordinates
- Emits signals when new bboxes are created

**Key Methods:**
- `start_drawing(point)`: Begin drawing a new bbox
- `update_drawing(point)`: Update current bbox coordinates
- `finish_drawing(point, label)`: Complete the bbox and create annotation
- `get_current_bbox()`: Get coordinates of bbox being drawn

**Signals:**
- `bbox_created`: Emitted when a new bbox is completed

### EditingController

Manages edit mode operations:
- Handles bbox modification
- Controls dragging and resizing operations
- Manages control points for bbox manipulation

**Key Methods:**
- `start_dragging(point, bbox_index, control_point)`: Begin drag operation
- `update_dragging(point, annotations)`: Update bbox during drag
- `finish_dragging()`: Complete the modification

**Signals:**
- `bbox_modified`: Emitted when a bbox is modified

### ImageRenderer

Handles all image rendering operations:
- Renders annotations on images
- Handles preview during drawing
- Manages appearance settings for visual elements
- Coordinates coordinate transformations

**Key Methods:**
- `render_image()`: Render image with current annotations
- `render_preview()`: Show live preview during drawing
- `apply_appearance_settings()`: Update visual styling

### UI Components

#### ImagePanel

Manages the image display area:
- Displays the current image
- Handles mouse interactions for drawing/editing
- Manages zoom and pan operations
- Emits navigation signals

**Key Signals:**
- `mode_changed`: When switching draw/edit modes
- `navigate_requested`: When image navigation is needed
- `update_needed`: When display needs refresh

#### LabelPanel

Manages the label interface:
- Shows list of annotations in current image
- Provides label selection interface
- Shows file list for navigation
- Manages label grouping options

**Key Features:**
- Label list with grouping support
- File navigation list
- Current label selection
- Label editing interface

## Signal Flow Architecture

### UI Event Flow
1. User interacts with UI (mouse/keyboard)
2. UI components emit signals
3. Main window coordinates between handlers
4. Controllers process operations
5. Handlers update state
6. ImageRenderer updates display

### Data Flow
1. AnnotationHandler manages data state
2. LabelHandler tracks label state
3. Controllers modify data through handlers
4. UI reflects changes through signals
5. ImageRenderer provides visual feedback

## File Structure

```
bboxanntool/
├── __init__.py
├── ann_handler.py     # Annotation management
├── app.py            # Main window and coordination
├── appearance.py     # Appearance settings
├── controllers.py    # Drawing and editing controllers
├── label_handler.py  # Label management
├── logger.py         # Logging system
├── rendering.py      # Image rendering
└── ui/
    ├── __init__.py
    ├── image_panel.py  # Image display component
    └── label_panel.py  # Label interface component
```

## Benefits of This Architecture

1. **Separation of Concerns**
   - Each component has a clear, single responsibility
   - Logic is separated into appropriate controllers
   - UI components are independent of business logic

2. **Reduced Complexity**
   - Main window focuses on coordination
   - Controllers handle specific interaction modes
   - Rendering is separated from state management

3. **Improved Maintainability**
   - Modular design makes changes easier
   - Clear boundaries between components
   - Each component can be tested independently

4. **Better State Management**
   - Clear ownership of different types of data
   - Well-defined signal paths for updates
   - Consistent state handling across components

5. **Enhanced Extensibility**
   - New features can be added in isolated components
   - UI can be modified without affecting logic
   - New controllers can be added for new modes
