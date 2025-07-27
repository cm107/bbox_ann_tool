from pytestqt.qtbot import QtBot
import pytest
import tempfile
from pathlib import Path
import numpy as np
from bboxanntool.ann_handler import AnnotationHandler
from bboxanntool.annotation import BBox

@pytest.fixture
def handler() -> AnnotationHandler:
    """Fixture that provides an AnnotationHandler with dummy settings."""
    class DummySettings:
        def value(self, key, default=None):
            if key == "output_dir":
                return tempfile.gettempdir()
            return default
    return AnnotationHandler(settings=DummySettings())

@pytest.fixture
def sample_annotation():
    """Fixture that provides a sample BBox annotation."""
    return BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))

def test_initialization(handler: AnnotationHandler) -> None:
    """Test that AnnotationHandler initializes correctly."""
    assert handler.current_ann_path is None
    assert handler.selected_index is None
    assert not handler.has_unsaved_changes

def test_set_current_ann_path(handler: AnnotationHandler, qtbot: QtBot, tmp_path) -> None:
    """Test setting the current annotation path."""
    ann_path = str(tmp_path / "test.json")
    with qtbot.waitSignal(handler.current_ann_path_changed, timeout=1000):
        handler.current_ann_path = ann_path
    assert handler.current_ann_path == ann_path

def test_add_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test adding an annotation."""
    # Set up annotation path first
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    
    # Add annotation
    with qtbot.waitSignal(handler.annotations_changed, timeout=1000):
        handler.add_annotation(sample_annotation)
    
    assert len(handler._annotations) == 1
    assert handler._annotations[0].label == "cat"
    assert handler.has_unsaved_changes

def test_select_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test selecting an annotation."""
    # Set up annotation path and add annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    
    # Select annotation
    with qtbot.waitSignal(handler.annotation_selected, timeout=1000):
        handler.select_annotation(0)
    
    assert handler.selected_index == 0
    assert handler.selected_annotation.label == "cat"

def test_unselect_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test unselecting an annotation."""
    # Set up annotation path, add and select annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Unselect annotation
    with qtbot.waitSignal(handler.annotation_unselected, timeout=1000):
        handler.select_annotation(None)
    
    assert handler.selected_index is None
    assert handler.selected_annotation is None

def test_rename_selected_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test renaming the selected annotation."""
    # Set up annotation path, add and select annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Rename annotation
    with qtbot.waitSignal(handler.annotation_renamed, timeout=1000):
        handler.rename_selected_annotation("dog")
    
    assert handler.selected_annotation.label == "dog"
    assert handler.has_unsaved_changes

def test_edit_selected_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test editing the selected annotation."""
    # Set up annotation path, add and select annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Edit annotation
    new_p0 = np.array([10, 20], dtype=np.float32)
    with qtbot.waitSignal(handler.annotation_edited, timeout=1000):
        handler.edit_selected_annotation('p0', new_p0)
    
    assert np.array_equal(handler.selected_annotation.p0, new_p0)
    assert handler.has_unsaved_changes

def test_delete_selected_annotation(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test deleting the selected annotation."""
    # Set up annotation path, add and select annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Delete annotation
    with qtbot.waitSignal(handler.annotation_deleted, timeout=1000):
        handler.delete_selected_annotation()
    
    assert len(handler._annotations) == 0
    assert handler.selected_index is None
    assert handler.has_unsaved_changes

def test_delete_annotations_by_label(handler: AnnotationHandler, qtbot: QtBot, tmp_path) -> None:
    """Test deleting all annotations with a given label."""
    # Set up annotation path
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    
    # Add multiple annotations
    cat1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
    dog = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
    cat2 = BBox("cat", np.array([9, 10], dtype=np.float32), np.array([11, 12], dtype=np.float32))
    
    handler.add_annotation(cat1)
    handler.add_annotation(dog)
    handler.add_annotation(cat2)
    
    # Delete all "cat" annotations
    with qtbot.waitSignal(handler.annotation_deleted, timeout=1000):
        handler.delete_annotations_by_label("cat")
    
    assert len(handler._annotations) == 1
    assert handler._annotations[0].label == "dog"
    assert handler.has_unsaved_changes

def test_save_and_load_annotations(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test saving and loading annotations."""
    # Set up annotation path and add annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    
    # Save annotations
    with qtbot.waitSignal(handler.annotations_saved, timeout=1000):
        handler.save_annotations()
    
    assert not handler.has_unsaved_changes
    assert Path(ann_path).exists()
    
    # Create new handler and load annotations
    new_handler = AnnotationHandler(settings=handler.settings)
    new_handler.current_ann_path = ann_path
    
    assert len(new_handler._annotations) == 1
    assert new_handler._annotations[0].label == "cat"

def test_check_unsaved_changes(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path, monkeypatch) -> None:
    """Test check_unsaved_changes method."""
    # Set up annotation path
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    
    # No unsaved changes - should return True
    assert handler.check_unsaved_changes() is True
    
    # Add annotation to create unsaved changes
    handler.add_annotation(sample_annotation)
    assert handler.has_unsaved_changes
    
    # Mock QMessageBox to return Yes (proceed without saving)
    from PyQt5.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, 'exec_', lambda self: QMessageBox.Yes)
    assert handler.check_unsaved_changes() is True
    
    # Mock QMessageBox to return No (don't proceed)
    monkeypatch.setattr(QMessageBox, 'exec_', lambda self: QMessageBox.No)
    assert handler.check_unsaved_changes() is False

def test_reset(handler: AnnotationHandler, sample_annotation: BBox, qtbot: QtBot, tmp_path) -> None:
    """Test resetting the handler."""
    # Set up annotation path and add annotation
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Reset handler
    with qtbot.waitSignal(handler.state_reset, timeout=1000):
        handler.reset()
    
    assert handler.current_ann_path is None
    assert handler._annotations is None
    assert handler.selected_index is None
    assert not handler.has_unsaved_changes

def test_invalid_annotation_selection(handler: AnnotationHandler, tmp_path) -> None:
    """Test selecting an invalid annotation index."""
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    
    # Try to select annotation when none exist
    with pytest.raises(IndexError):
        handler.select_annotation(0)

def test_edit_nonexistent_attribute(handler: AnnotationHandler, sample_annotation: BBox, tmp_path) -> None:
    """Test editing a nonexistent attribute."""
    ann_path = str(tmp_path / "test.json")
    handler.current_ann_path = ann_path
    handler.add_annotation(sample_annotation)
    handler.select_annotation(0)
    
    # Try to edit nonexistent attribute
    with pytest.raises(AttributeError):
        handler.edit_selected_annotation('nonexistent', 'value')
