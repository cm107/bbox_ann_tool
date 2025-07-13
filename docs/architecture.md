# Application Architecture

## Overview

The BBox Annotation Tool follows a modular architecture that separates concerns into specialized handler classes. This design improves maintainability and makes the code easier to understand and modify.

## Core Components

### BBoxAnnotationTool

The main application window class that:
- Creates and manages the UI
- Handles user input events
- Coordinates between different handlers
- Manages application-level settings and state

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

## Component Interactions

### Annotation Creation Flow
1. User draws a bbox in the UI
2. BBoxAnnotationTool gets current label from LabelHandler
3. BBoxAnnotationTool calls AnnotationHandler to create annotation
4. AnnotationHandler emits signals to update UI

### Label Update Flow
1. User edits a label via UI
2. BBoxAnnotationTool triggers LabelHandler dialog
3. LabelHandler emits label_renamed signal
4. AnnotationHandler updates affected annotations
5. UI updates reflect changes

### Save/Load Flow
1. User triggers save/load action
2. BBoxAnnotationTool delegates to AnnotationHandler
3. AnnotationHandler manages file operations
4. UI updates based on emitted signals

## Benefits of This Architecture

1. **Separation of Concerns**
   - Each handler has a specific responsibility
   - Changes to one component don't affect others
   - Easier to test individual components

2. **Reduced Complexity**
   - Main window class focuses on UI
   - Logic is organized by functionality
   - Clear boundaries between components

3. **Improved Maintainability**
   - Localized changes for new features
   - Better error isolation
   - Easier to add new functionality

4. **Better State Management**
   - Clear ownership of data
   - Predictable update patterns
   - Consistent state across UI
