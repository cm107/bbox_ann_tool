"""Appearance settings dialog for BBox Annotation Tool."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSpinBox, QColorDialog)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSettings
from pathlib import Path

class AppearanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Appearance Settings")
        self.settings = QSettings(str(Path.home() / ".bbox_ann_tool" / "settings.ini"), 
                                QSettings.Format.IniFormat)
        self.init_ui()

    def create_color_button(self, setting_name, label_text, default_color):
        """Creates a button with a color preview"""
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        
        # Create color preview
        preview = QLabel()
        preview.setFixedSize(20, 20)
        preview.setStyleSheet(f"background-color: {self.settings.value(setting_name, default_color)};")
        layout.addWidget(preview)
        
        # Create button
        button = QPushButton("Change")
        button.clicked.connect(lambda: self.change_color(setting_name, preview, label_text))
        layout.addWidget(button)
        layout.addStretch()
        
        return layout

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Color settings with previews
        layout.addLayout(self.create_color_button("bbox_color", "Normal BBox Color:", "#FF0000"))
        layout.addLayout(self.create_color_button("bbox_selected_color", "Selected BBox Color:", "#00FF00"))
        layout.addLayout(self.create_color_button("points_color", "Edit Points Color:", "#0000FF"))
        layout.addLayout(self.create_color_button("label_color", "Label Text Color:", "#000000"))
        
        # Bbox line width
        line_width_layout = QHBoxLayout()
        line_width_layout.addWidget(QLabel("BBox Line Width:"))
        self.line_width_spin = QSpinBox()
        self.line_width_spin.setRange(1, 10)
        self.line_width_spin.setValue(int(self.settings.value("bbox_line_width", 2)))
        self.line_width_spin.valueChanged.connect(self.change_line_width)
        line_width_layout.addWidget(self.line_width_spin)
        line_width_layout.addStretch()
        layout.addLayout(line_width_layout)
        
        # Edit points size
        points_size_layout = QHBoxLayout()
        points_size_layout.addWidget(QLabel("Edit Points Size:"))
        self.points_size_spin = QSpinBox()
        self.points_size_spin.setRange(3, 20)
        self.points_size_spin.setValue(int(self.settings.value("points_size", 6)))
        self.points_size_spin.valueChanged.connect(lambda v: self.change_numeric("points_size", v))
        points_size_layout.addWidget(self.points_size_spin)
        points_size_layout.addStretch()
        layout.addLayout(points_size_layout)
        
        # Label font size
        label_size_layout = QHBoxLayout()
        label_size_layout.addWidget(QLabel("Label Font Size:"))
        self.label_size_spin = QSpinBox()
        self.label_size_spin.setRange(8, 72)
        self.label_size_spin.setValue(int(self.settings.value("label_font_size", 12)))
        self.label_size_spin.valueChanged.connect(lambda v: self.change_numeric("label_font_size", v))
        label_size_layout.addWidget(self.label_size_spin)
        label_size_layout.addStretch()
        layout.addLayout(label_size_layout)
        
        # Theme settings
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_btn = QPushButton(self.settings.value("theme", "light").title())
        self.theme_btn.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_btn)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        layout.addStretch()
        self.setLayout(layout)

    def change_color(self, setting_name, preview, label_text):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings.setValue(setting_name, color.name())
            preview.setStyleSheet(f"background-color: {color.name()};")
            if self.parent():
                self.parent().update_display()

    def change_line_width(self, value):
        self.settings.setValue("bbox_line_width", value)
        if self.parent():
            self.parent().update_display()

    def change_numeric(self, setting_name, value):
        self.settings.setValue(setting_name, value)
        if self.parent():
            self.parent().update_display()

    def toggle_theme(self):
        current_theme = self.settings.value("theme", "light")
        new_theme = "dark" if current_theme == "light" else "light"
        self.settings.setValue("theme", new_theme)
        self.theme_btn.setText(new_theme.title())
        if self.parent():
            self.parent().apply_theme()
