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
[TIMESTAMP] [LEVEL] [COMPONENT] Message

Examples:
[2025-07-12 10:15:30] [INFO] [Session] === Application Started ===
[2025-07-12 10:15:30] [INFO] [System] Python Version: 3.12.2
[2025-07-12 10:15:30] [INFO] [System] Application Version: 0.1.0
[2025-07-12 10:15:30] [INFO] [System] Qt Version: 5.15.17
[2025-07-12 10:15:30] [INFO] [System] PyQt5 Version: 5.15.11
[2025-07-12 10:15:30] [INFO] [System] OpenCV Version: 4.9.0
[2025-07-12 10:15:30] [INFO] [FileOps] Saved annotations to: example.json
[2025-07-12 10:20:45] [INFO] [Session] === Application Shutting Down ===
```

## Log Components

### Session
Tracks application lifecycle:
- Application start
- Application shutdown

### System
Records system information at startup:
- Python version
- Application version
- Qt version
- PyQt5 version
- OpenCV version

### FileOps
Tracks file operations:
- Opening/saving files
- Directory changes
- Image loading

### UI
User interface events:
- Mode changes
- Window resizing
- Settings updates

### Annotations
Annotation-related operations:
- Creating bounding boxes
- Editing labels
- Deleting annotations

### Input
User input handling:
- Mouse events
- Keyboard shortcuts
