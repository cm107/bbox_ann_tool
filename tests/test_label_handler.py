from pathlib import Path
import pytest
from pytestqt.qtbot import QtBot
from bboxanntool.label_handler import LabelHandler
from PyQt5.QtWidgets import QListWidget, QDialogButtonBox

@pytest.fixture
def handler(qtbot) -> LabelHandler:
    class DummySettings:
        def value(self, key, default=None):
            return "output"
    h = LabelHandler(settings=DummySettings())
    return h

def test_current_label_property(handler: LabelHandler, qtbot: QtBot) -> None:
    """Test current_label property and label_changed signal."""
    with qtbot.waitSignal(handler.label_changed, timeout=1000):
        handler.current_label = "cat"
    assert handler.current_label == "cat"
    with qtbot.waitSignal(handler.label_changed, timeout=1000):
        handler.current_label = "dog"
    assert handler.current_label == "dog"

def test_get_all_unique_labels_empty(tmp_path, qtbot: QtBot) -> None:
    """Test get_all_unique_labels returns empty list if no files exist."""
    class DummySettings:
        def value(self, key, default=None):
            return str(tmp_path)
    handler = LabelHandler(settings=DummySettings())
    assert handler.get_all_unique_labels() == []

def test_get_all_unique_labels(tmp_path: Path, qtbot: QtBot) -> None:
    """Test get_all_unique_labels returns all unique labels from annotation files."""
    # Create two annotation files
    data1 = {"annotations": [{"label": "cat", "bbox": [1,2,3,4]}, {"label": "dog", "bbox": [5,6,7,8]}]}
    data2 = {"annotations": [{"label": "cat", "bbox": [9,10,11,12]}, {"label": "bird", "bbox": [13,14,15,16]}]}
    file1 = tmp_path / "a.json"
    file2 = tmp_path / "b.json"
    file1.write_text(str(data1).replace("'", '"'))
    file2.write_text(str(data2).replace("'", '"'))
    class DummySettings:
        def value(self, key, default=None):
            return str(tmp_path)
    handler = LabelHandler(settings=DummySettings())
    labels = handler.get_all_unique_labels()
    assert set(labels) == {"cat", "dog", "bird"}

def make_dummy_button_box():
    class DummySignal:
        def connect(self, fn): pass
    class DummyButtonBox:
        accepted = DummySignal()
        rejected = DummySignal()
    return DummyButtonBox()

def monkeypatch_qdialogbuttonbox(monkeypatch):
    # Patch only the constructor, but preserve Ok/Cancel attributes
    dummy_ctor = lambda *a, **k: make_dummy_button_box()
    dummy_ctor.Ok = 1
    dummy_ctor.Cancel = 2
    monkeypatch.setattr("bboxanntool.label_handler.QDialogButtonBox", dummy_ctor)

def monkeypatch_qdialog(monkeypatch):
    class DummyDialog:
        def __init__(self): self._accepted = True
        def setWindowTitle(self, t): pass
        def setLayout(self, l): pass
        def exec_(self): return 1
        def accept(self): pass
        def reject(self): pass
    dummy_ctor = lambda: DummyDialog()
    monkeypatch.setattr("bboxanntool.label_handler.QDialog", dummy_ctor)
    import bboxanntool.label_handler as lh
    lh.QDialog.Accepted = 1

def test_edit_label_dialog_accept(monkeypatch, handler: LabelHandler, qtbot: QtBot) -> None:
    """Test edit_label_dialog returns new label and emits label_renamed if accepted."""
    class DummyDialog:
        def __init__(self): self._accepted = True
        def setWindowTitle(self, t): pass
        def setLayout(self, l): pass
        def exec_(self): return 1
        def accept(self): pass
        def reject(self): pass
    class DummyCombo:
        def __init__(self): self._text = "lion"
        def setEditable(self, b): pass
        def addItems(self, items): pass
        def setCurrentText(self, t): pass
        def currentText(self): return self._text
    class DummyVBox:
        def addWidget(self, w): pass
    monkeypatch.setattr("bboxanntool.label_handler.QDialog", lambda: DummyDialog())
    import bboxanntool.label_handler as lh
    lh.QDialog.Accepted = 1
    monkeypatch.setattr("bboxanntool.label_handler.QComboBox", lambda: DummyCombo())
    monkeypatch.setattr("bboxanntool.label_handler.QVBoxLayout", lambda: DummyVBox())
    monkeypatch_qdialogbuttonbox(monkeypatch)
    with qtbot.waitSignal(handler.label_renamed, timeout=1000):
        result = handler.edit_label_dialog("cat")
    assert result == "lion"

def test_edit_label_dialog_cancel(monkeypatch, handler: LabelHandler, qtbot: QtBot) -> None:
    """Test edit_label_dialog returns None if dialog is cancelled."""
    class DummyDialog:
        def __init__(self): self._accepted = False
        def setWindowTitle(self, t): pass
        def setLayout(self, l): pass
        def exec_(self): return 0
        def accept(self): pass
        def reject(self): pass
    class DummyCombo:
        def __init__(self): self._text = "lion"
        def setEditable(self, b): pass
        def addItems(self, items): pass
        def setCurrentText(self, t): pass
        def currentText(self): return self._text
    class DummyVBox:
        def addWidget(self, w): pass
    monkeypatch.setattr("bboxanntool.label_handler.QDialog", lambda: DummyDialog())
    import bboxanntool.label_handler as lh
    lh.QDialog.Accepted = 1
    monkeypatch.setattr("bboxanntool.label_handler.QComboBox", lambda: DummyCombo())
    monkeypatch.setattr("bboxanntool.label_handler.QVBoxLayout", lambda: DummyVBox())
    monkeypatch_qdialogbuttonbox(monkeypatch)
    result = handler.edit_label_dialog("cat")
    assert result is None

def test_update_label_list_grouped(handler: LabelHandler, qtbot: QtBot) -> None:
    """Test update_label_list groups labels and shows counts."""
    class DummyAnnHandler:
        annotations = [
            {"label": "cat"}, {"label": "cat"}, {"label": "dog"}
        ]
    handler._ann_handler = DummyAnnHandler()
    label_list = QListWidget()
    handler.update_label_list(label_list, group_similar=True)
    assert label_list.count() == 2
    texts = [label_list.item(i).text() for i in range(label_list.count())]
    assert any("cat (2)" in t for t in texts)
    assert any("dog" in t for t in texts)

def test_update_label_list_individual(handler: LabelHandler, qtbot: QtBot) -> None:
    """Test update_label_list shows all annotations individually."""
    class DummyAnnHandler:
        annotations = [
            {"label": "cat"}, {"label": "dog"}, {"label": "cat"}
        ]
    handler._ann_handler = DummyAnnHandler()
    label_list = QListWidget()
    handler.update_label_list(label_list, group_similar=False)
    assert label_list.count() == 3
    texts = [label_list.item(i).text() for i in range(label_list.count())]
    assert any("cat #1" in t for t in texts)
    assert any("dog #2" in t for t in texts)
    assert any("cat #3" in t for t in texts)
