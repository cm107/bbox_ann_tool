# Development Setup

## Package Installation

This project is structured as a Python package. To install it for development:

1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .
   ```

This will install the package in "editable" mode, meaning changes to the source code will be reflected immediately without requiring reinstallation.

## Package Structure

The project is organized as follows:

```
bbox_ann_tool/
├── bboxanntool/              # Main package directory
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Main application window
│   ├── appearance.py        # Appearance settings dialog
│   └── logger.py            # Logging functionality
├── assets/                  # Application assets
│   └── icon_original.png    # Application icon
├── docs/                    # Documentation
├── gui.py                   # Entry point script
├── setup.py                # Package setup file
└── README.md               # Project documentation
```

### Module Organization

- `bboxanntool/app.py`: Contains the main application window class `BBoxAnnotationTool`
- `bboxanntool/appearance.py`: Contains the appearance settings dialog
- `bboxanntool/logger.py`: Contains logging functionality and log viewer dialog
- `gui.py`: Main entry point script that starts the application

## Running the Application

After installation, you can run the application in two ways:

1. Using the entry point script:
   ```bash
   python gui.py
   ```

2. Using the installed console script:
   ```bash
   bboxanntool
   ```
