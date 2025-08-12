from __future__ import annotations
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QAction,
    QFileDialog,
    QStatusBar,
)
# Added for persistence
from pathlib import Path
import json
import os
from bboxanntool.canvas import Canvas

class MainWindow(QMainWindow):
    def __init__(self, imagePath: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Viewport Canvas Test")
        # config file for persisting last image
        self._config_file = Path(os.path.expanduser("~/.bbox_ann_tool_config.json"))
        self._canvas = Canvas(self)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self._canvas, stretch=1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central)

        self._status = QStatusBar(self)
        self.setStatusBar(self._status)

        self._create_actions()
        self._create_menu()
        self._load_initial_image(imagePath)

    def _create_actions(self):
        self._openAct = QAction("Open...", self)
        self._openAct.setShortcut("Ctrl+O")
        self._openAct.triggered.connect(self.open_image)

        self._quitAct = QAction("Quit", self)
        self._quitAct.setShortcut("Ctrl+Q")
        self._quitAct.triggered.connect(QApplication.instance().quit)

        self._resetAct = QAction("Reset View", self)
        self._resetAct.setShortcut("R")
        self._resetAct.triggered.connect(self.reset_view)

    def _create_menu(self):
        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addAction(self._openAct)
        fileMenu.addSeparator()
        fileMenu.addAction(self._quitAct)

        viewMenu = self.menuBar().addMenu("&View")
        viewMenu.addAction(self._resetAct)

    def _load_initial_image(self, path: str | None):
        img = None
        loaded_path: str | None = None
        # 1. explicit path argument
        if path:
            img = cv2.imread(path)
            if img is None:
                self._status.showMessage(f"Failed to load {path}, falling back.", 5000)
            else:
                loaded_path = path
        # 2. last session image
        if img is None and path is None:
            last = self._load_last_image()
            if last:
                tmp = cv2.imread(last)
                if tmp is not None:
                    img = tmp
                    loaded_path = last
                else:
                    self._status.showMessage(f"Failed to load last image '{last}', generating demo.", 5000)
        # 3. demo fallback
        if img is None:
            img = self._generate_demo_image(1200, 800)
        self._canvas.image = img  # signal driven render
        if loaded_path:
            self._save_last_image(loaded_path)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            self._status.showMessage(f"Failed to load {path}", 5000)
            return
        self._canvas.image = img  # signal driven render
        self._status.showMessage(f"Loaded {path}", 5000)
        self._save_last_image(path)

    def reset_view(self):
        if self._canvas.image is not None:
            self._canvas.viewport.setup_canvas_for_image(self._canvas.image)  # emits modified -> render
            self._status.showMessage("View reset", 2000)

    @staticmethod
    def _generate_demo_image(w: int, h: int) -> np.ndarray:
        x = np.linspace(0, 1, w, dtype=np.float32)
        y = np.linspace(0, 1, h, dtype=np.float32)
        xv, yv = np.meshgrid(x, y)
        r = (xv * 255).astype(np.uint8)
        g = (yv * 255).astype(np.uint8)
        b = (0.5 * (np.sin(10 * xv) * 0.5 + 0.5) * 255).astype(np.uint8)
        img = np.dstack([b, g, r])
        cv2.putText(img, "Demo Image", (40, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3, cv2.LINE_AA)
        return img

    def _save_last_image(self, path: str):
        try:
            data = {"last_image": path}
            self._config_file.write_text(json.dumps(data))
        except Exception as e:
            self._status.showMessage(f"Config save failed: {e}", 3000)

    def _load_last_image(self) -> str | None:
        try:
            if self._config_file.is_file():
                data = json.loads(self._config_file.read_text())
                cand = data.get("last_image")
                if cand and Path(cand).is_file():
                    return cand
        except Exception:
            pass
        return None

def main():
    app = QApplication(sys.argv)
    imgPath = sys.argv[1] if len(sys.argv) > 1 else None
    win = MainWindow(imgPath)
    win.resize(900, 700)
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
