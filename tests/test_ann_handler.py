from pytestqt.qtbot import QtBot
import pytest
from bboxanntool.ann_handler import AnnotationHandler

@pytest.fixture
def handler() -> AnnotationHandler:
    """Fixture that provides an AnnotationHandler with dummy settings and logger."""
    class DummySettings:
        def value(self, key, default=None):
            return default
    class DummyLogger:
        def debug(self, *a, **k): pass
        def error(self, *a, **k): pass
    return AnnotationHandler(settings=DummySettings(), logger=DummyLogger())

def test_add_annotation(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test that adding an annotation updates the list and emits the annotations_changed signal."""
    with qtbot.waitSignal(handler.annotations_changed, timeout=1000):
        handler.add_annotation([1, 2, 3, 4], "cat")
    assert len(handler.annotations) == 1
    assert handler.annotations[0]["label"] == "cat"
    assert handler.annotations[0]["bbox"] == [1, 2, 3, 4]

def test_update_annotation(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test that updating an annotation's bbox or label works and emits the bbox_modified signal."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    with qtbot.waitSignal(handler.bbox_modified, timeout=1000):
        handler.update_annotation(0, bbox=[5, 6, 7, 8])
    assert handler.annotations[0]["bbox"] == [5, 6, 7, 8]
    handler.update_annotation(0, label="dog")
    assert handler.annotations[0]["label"] == "dog"

def test_delete_annotation(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test that deleting an annotation removes it from the list and emits the annotations_changed signal."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.add_annotation([5, 6, 7, 8], "dog")
    with qtbot.waitSignal(handler.annotations_changed, timeout=1000):
        handler.delete_annotation(0)
    assert len(handler.annotations) == 1
    assert handler.annotations[0]["label"] == "dog"

def test_delete_annotations_by_label(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test deleting all annotations with a given label."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.add_annotation([5, 6, 7, 8], "dog")
    handler.add_annotation([9, 10, 11, 12], "cat")
    handler.select_annotation(1)
    with qtbot.waitSignals([handler.annotations_changed, handler.selection_changed], timeout=1000):
        handler.delete_annotations_by_label("cat")
    assert len(handler.annotations) == 1
    assert handler.annotations[0]["label"] == "dog"
    assert handler.selected_index is None

def test_rename_label(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test renaming all annotations with a given label."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.add_annotation([5, 6, 7, 8], "cat")
    handler.add_annotation([9, 10, 11, 12], "dog")
    handler.select_annotation(0)
    with qtbot.waitSignal(handler.annotations_changed, timeout=1000):
        handler.rename_label("cat", "lion")
    assert all(ann["label"] != "cat" for ann in handler.annotations)
    assert sum(ann["label"] == "lion" for ann in handler.annotations) == 2
    # selection_changed may or may not be emitted depending on selected_index

def test_select_annotation(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test selecting an annotation by index and clearing selection."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.add_annotation([5, 6, 7, 8], "dog")
    with qtbot.waitSignal(handler.selection_changed, timeout=1000):
        handler.select_annotation(1)
    assert handler.selected_index == 1
    with qtbot.waitSignal(handler.selection_changed, timeout=1000):
        handler.select_annotation(-1)
    assert handler.selected_index == -1

def test_check_unsaved_changes_true(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test check_unsaved_changes returns True if there are no unsaved changes."""
    handler.has_unsaved_changes = False
    assert handler.check_unsaved_changes() is True

def test_check_unsaved_changes_false_yes(monkeypatch, handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test check_unsaved_changes returns True if user clicks Yes in dialog."""
    handler.has_unsaved_changes = True
    monkeypatch.setattr("PyQt5.QtWidgets.QMessageBox.exec_", lambda self: 16384)  # QMessageBox.Yes
    assert handler.check_unsaved_changes() is True

def test_check_unsaved_changes_false_no(monkeypatch, handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test check_unsaved_changes returns False if user clicks No in dialog."""
    handler.has_unsaved_changes = True
    monkeypatch.setattr("PyQt5.QtWidgets.QMessageBox.exec_", lambda self: 65536)  # QMessageBox.No
    assert handler.check_unsaved_changes() is False

def test_update_invalid_index(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test updating an annotation with an invalid index does nothing and does not crash."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.update_annotation(5, bbox=[0, 0, 0, 0])  # Should not raise
    handler.update_annotation(-2, label="dog")  # Should not raise
    assert handler.annotations[0]["label"] == "cat"

def test_delete_invalid_index(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test deleting an annotation with an invalid index does nothing and does not crash."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.delete_annotation(5)  # Should not raise
    handler.delete_annotation(-2)  # Should not raise
    assert len(handler.annotations) == 1

def test_rename_label_not_found(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test renaming a label that does not exist does nothing and does not crash."""
    handler.add_annotation([1, 2, 3, 4], "cat")
    with qtbot.waitSignal(handler.annotations_changed, timeout=1000, raising=False) as sig:
        handler.rename_label("dog", "lion")
    assert handler.annotations[0]["label"] == "cat"
    assert sig.signal_triggered is False

def test_has_unsaved_changes_property(handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test has_unsaved_changes property and signal emission."""
    with qtbot.waitSignal(handler.unsaved_changes, timeout=1000):
        handler.has_unsaved_changes = True
    assert handler.has_unsaved_changes is True
    with qtbot.waitSignal(handler.unsaved_changes, timeout=1000):
        handler.has_unsaved_changes = False
    assert handler.has_unsaved_changes is False

def test_save_and_load_annotations(tmp_path, handler: AnnotationHandler, qtbot: QtBot) -> None:
    """Test saving and loading annotations to and from a file."""
    # Patch get_annotation_path to use a temp file
    test_file = tmp_path / "test_ann.json"
    handler.current_image_path = "dummy_image.png"
    handler.get_annotation_path = lambda image_path=None: str(test_file)
    # Add and save
    handler.add_annotation([1, 2, 3, 4], "cat")
    handler.add_annotation([5, 6, 7, 8], "dog")
    assert handler.save_annotations() is True
    # Create a new handler to load
    new_handler = AnnotationHandler(settings=handler.settings, logger=handler.logger)
    new_handler.get_annotation_path = lambda image_path=None: str(test_file)
    with qtbot.waitSignal(new_handler.annotations_changed, timeout=1000):
        new_handler.load_annotations("dummy_image.png")
    assert len(new_handler.annotations) == 2
    assert new_handler.annotations[0]["label"] == "cat"
    assert new_handler.annotations[1]["label"] == "dog"
    assert new_handler.annotations[0]["bbox"] == [1, 2, 3, 4]
    assert new_handler.annotations[1]["bbox"] == [5, 6, 7, 8]
