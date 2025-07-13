# Application Logging

The application maintains detailed logs of all operations for debugging and monitoring purposes.

## Log Location
Logs are stored in: `~/.bbox_ann_tool/logs/`
- Daily log files: `bbox_tool_YYYY-MM-DD.log`
- Each session starts with a session header

## Log Levels

### ERROR
Critical issues that prevent normal operation:
- File read/write failures
- Image loading errors
- JSON parsing errors

### WARNING
Non-critical issues that might affect functionality:
- Invalid bounding box coordinates
- Missing icon files
- Unsupported file types

### INFO
Normal operational events:
- Application start/stop
- File operations (open, save)
- Directory changes
- Annotation modifications
- Mode changes
- Settings updates

### DEBUG
Detailed information for debugging:
- Mouse coordinates
- Bounding box calculations
- UI event processing
- Settings values

## Viewing Logs
Logs can be viewed directly in the application:
1. Open the "Logging" menu
2. Select "View Logs"
3. Use the log viewer dialog to:
   - Filter by log level
   - Search for specific text
   - Export filtered logs

## Log Format
```
[TIMESTAMP] [LEVEL] [CATEGORY] [COMPONENT] Message

Examples:
[2025-07-12 10:15:30] [INFO] [Session] [BBoxAnnotationTool] Application Started
[2025-07-12 10:15:35] [INFO] [FileOps] [AnnotationHandler] Loading annotations from: example.json
[2025-07-12 10:15:40] [INFO] [UI] [LabelHandler] Updated label list: 5 items
```

## Log Components

### Main Components

#### BBoxAnnotationTool
The main application window, handles:
- Application lifecycle events
- UI interactions
- Image loading and display
- Overall application state

#### AnnotationHandler
Manages annotation data and operations:
- Loading/saving annotations
- BBOX modifications
- Selection state
- Annotation validation

#### LabelHandler
Handles label-related functionality:
- Label list management
- Label editing
- Label validation
- Group operations

#### DrawingController
Handles drawing mode operations:
- Logging of bbox creation
- Drawing state tracking
- Coordinate validation

#### EditingController
Handles editing mode operations:
- Logging of bbox modifications
- Control point interactions
- Resize and move operations

### Log Categories

#### Session
Tracks application lifecycle:
- Application start
- Application shutdown
- Version information

#### System
Records system information at startup:
- Python version
- Application version
- Qt version
- PyQt5 version
- OpenCV version

#### FileOps
Tracks file operations:
- Opening/saving files
- Directory changes
- Image loading
- Annotation file handling

#### UI
User interface events:
- Mode changes
- Window resizing
- Settings updates
- Display updates

#### Annotations
Annotation-related operations:
- Creating bounding boxes (DrawingController)
- Editing coordinates (EditingController)
- Label assignments
- Deletion operations

#### Input
User input handling:
- Mouse events
- Keyboard shortcuts
- Drawing operations

## Debugging with Logs
When debugging issues:
1. Look for the component name in brackets (e.g., [BBoxAnnotationTool], [AnnotationHandler])
2. Check the category to understand the type of operation
3. Follow the sequence of events across components
4. Use log levels to filter severity
