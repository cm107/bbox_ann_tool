# Controls and Shortcuts

## Global Keyboard Shortcuts
- `Ctrl+I`: Open Image
- `Ctrl+D`: Open Image Directory
- `Ctrl+O`: Change Output Directory
- `Ctrl+S`: Save Annotation
- `D`: Switch to Draw Mode
- `E`: Switch to Edit Mode
- `Esc`: Cancel current selection/action

## Navigation Shortcuts
- `Right Arrow` or `Down Arrow`: Next image
- `Left Arrow` or `Up Arrow`: Previous image

Note: Keyboard shortcuts work anywhere in the application unless a text input field has focus.

## Mouse Controls

### Draw Mode
- Left Click + Drag: Draw a new bounding box
- Release: Complete the bbox drawing (requires a label to be entered)

### Edit Mode
All bounding boxes can be edited in Edit Mode:

- Click and drag corner points: Resize the bbox from that corner
- Click and drag center point: Move the entire bbox
- Click outside any bbox: Clear selection

## Selection
- Click a label in the "Labels in Image" list to highlight the corresponding bbox
- Click empty space in the list to clear selection
- Right-click a label for additional options:
  - Edit Label
  - Delete
