import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from pytestqt.qtbot import QtBot

from bboxanntool.image_handler import ImageHandler


@pytest.fixture
def handler(qtbot) -> ImageHandler:
    """Fixture that provides an ImageHandler instance."""
    h = ImageHandler()
    return h


@pytest.fixture
def temp_image_dir():
    """Create a temporary directory with test images."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create some dummy image files
        image_files = [
            "image1.png",
            "image2.jpg", 
            "image3.jpeg",
            "image4.bmp",
            "image5.gif",
            "IMAGE6.PNG",  # Test uppercase
            "not_image.txt"  # Should be ignored
        ]
        
        for filename in image_files:
            (temp_path / filename).touch()
        
        yield str(temp_path)


def test_initialization(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test ImageHandler initialization."""
    assert handler.image_directory is None
    assert handler.image_paths is None
    assert handler.image_index is None
    assert handler.current_image_path is None
    assert handler.current_image is None


def test_reset(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test reset functionality."""
    # Set some values
    handler._image_directory = "/some/path"
    handler._image_paths = ["image1.png", "image2.jpg"]
    handler._image_index = 1
    handler._current_image_path = "image1.png"
    handler._current_image = np.array([1, 2, 3])
    
    with qtbot.waitSignal(handler.state_reset, timeout=1000):
        handler.reset()
    
    assert handler.image_directory is None
    assert handler.image_paths is None
    assert handler.image_index is None
    assert handler.current_image_path is None
    assert handler.current_image is None


def test_image_directory_valid(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test setting a valid image directory."""
    with qtbot.waitSignal(handler.image_directory_changed, timeout=1000) as blocker:
        with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
            handler.image_directory = temp_image_dir
    
    assert blocker.args == [temp_image_dir]
    assert handler.image_directory == temp_image_dir
    assert handler.image_paths is not None
    assert len(handler.image_paths) == 6  # 6 image files (excluding .txt)
    
    # Check that files are sorted and include both case variations
    expected_files = ["IMAGE6.PNG", "image1.png", "image2.jpg", "image3.jpeg", "image4.bmp", "image5.gif"]
    actual_filenames = [Path(p).name for p in handler.image_paths]
    assert sorted(actual_filenames) == sorted(expected_files)


def test_image_directory_invalid(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test setting an invalid image directory."""
    invalid_path = "/nonexistent/directory"
    
    with pytest.raises(ValueError, match="Invalid image directory"):
        handler.image_directory = invalid_path


def test_image_directory_empty(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test setting a directory with no images."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a text file (should be ignored)
        (Path(temp_dir) / "not_image.txt").touch()
        
        with qtbot.waitSignal(handler.image_directory_changed, timeout=1000):
            with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
                handler.image_directory = temp_dir
        
        assert handler.image_paths == []


def test_image_index_valid(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test setting a valid image index."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000) as blocker:
            with qtbot.waitSignal(handler.current_image_path_changed, timeout=1000):
                handler.image_index = 1
        
        assert blocker.args == [1]
        assert handler.image_index == 1
        assert handler.current_image_path == handler.image_paths[1]


def test_image_index_invalid(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test setting an invalid image index."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    with pytest.raises(IndexError, match="Invalid image index"):
        handler.image_index = 999  # Out of bounds


def test_image_index_no_paths(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test setting image index when no paths are available."""
    with pytest.raises(ValueError, match="No image paths available"):
        handler.image_index = 0


def test_image_index_none(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test setting image index to None."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
        with qtbot.waitSignal(handler.current_image_path_changed, timeout=1000):
            handler.image_index = None
    
    # Verify the state is correct regardless of what was emitted
    assert handler.image_index is None
    assert handler.current_image_path is None


def test_go_to_first_image(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to the first image."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_first_image()
        
        assert handler.image_index == 0


def test_go_to_first_image_no_paths(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test going to first image when no paths are available."""
    # Should not raise an exception, just log a warning
    handler.go_to_first_image()
    assert handler.image_index is None


def test_go_to_last_image(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to the last image."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_last_image()
        
        assert handler.image_index == len(handler.image_paths) - 1


def test_go_to_last_image_no_paths(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test going to last image when no paths are available."""
    # Should not raise an exception, just log a warning
    handler.go_to_last_image()
    assert handler.image_index is None


def test_go_to_next_image(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to the next image."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Start at first image
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.image_index = 0
        
        # Go to next
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_next_image()
        
        assert handler.image_index == 1


def test_go_to_next_image_from_none(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to next image when no image is currently selected."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Go to next from None should go to first image
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_next_image()
        
        assert handler.image_index == 0


def test_go_to_next_image_at_end(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to next image when already at the end."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Start at last image
        last_index = len(handler.image_paths) - 1
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.image_index = last_index
        
        # Try to go to next (should stay at same index)
        handler.go_to_next_image()
        assert handler.image_index == last_index


def test_go_to_next_image_no_paths(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test going to next image when no paths are available."""
    # Should not raise an exception, just log a warning
    handler.go_to_next_image()
    assert handler.image_index is None


def test_go_to_previous_image(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to the previous image."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Start at second image
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.image_index = 1
        
        # Go to previous
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_previous_image()
        
        assert handler.image_index == 0


def test_go_to_previous_image_from_none(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to previous image when no image is currently selected."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Go to previous from None should go to last image
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.go_to_previous_image()
        
        assert handler.image_index == len(handler.image_paths) - 1


def test_go_to_previous_image_at_start(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test going to previous image when already at the start."""
    # Set up directory first
    with qtbot.waitSignal(handler.image_paths_changed, timeout=1000):
        handler.image_directory = temp_image_dir
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        # Start at first image
        with qtbot.waitSignal(handler.image_index_changed, timeout=1000):
            handler.image_index = 0
        
        # Try to go to previous (should stay at same index)
        handler.go_to_previous_image()
        assert handler.image_index == 0


def test_go_to_previous_image_no_paths(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test going to previous image when no paths are available."""
    # Should not raise an exception, just log a warning
    handler.go_to_previous_image()
    assert handler.image_index is None


def test_current_image_path_valid(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test setting a valid current image path."""
    image_path = str(Path(temp_image_dir) / "image1.png")
    
    # Mock cv2.imread to avoid actual image loading
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.array([1, 2, 3])
        
        with qtbot.waitSignal(handler.current_image_path_changed, timeout=1000) as blocker:
            with qtbot.waitSignal(handler.current_image_changed, timeout=1000):
                handler.current_image_path = image_path
        
        assert blocker.args == [image_path]
        assert handler.current_image_path == image_path
        assert handler.current_image is not None


def test_current_image_path_invalid(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test setting an invalid current image path."""
    invalid_path = "/nonexistent/image.png"
    
    with pytest.raises(ValueError, match="Invalid image path"):
        handler.current_image_path = invalid_path


def test_current_image_path_none(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test setting current image path to None."""
    with qtbot.waitSignal(handler.current_image_path_changed, timeout=1000):
        handler.current_image_path = None
    
    # Verify the state is correct regardless of what was emitted  
    assert handler.current_image_path is None
    assert handler.current_image is None


def test_load_current_image_success(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test successful image loading."""
    image_path = str(Path(temp_image_dir) / "image1.png")
    mock_image = np.array([[[255, 0, 0]], [[0, 255, 0]], [[0, 0, 255]]])
    
    # Mock cv2.imread to return a mock image
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = mock_image
        
        with qtbot.waitSignal(handler.current_image_changed, timeout=1000) as blocker:
            handler.current_image_path = image_path
        
        assert np.array_equal(blocker.args[0], mock_image)
        assert np.array_equal(handler.current_image, mock_image)


def test_load_current_image_failure(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test image loading failure."""
    image_path = str(Path(temp_image_dir) / "image1.png")
    
    # Mock cv2.imread to return None (load failure)
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = None
        
        with pytest.raises(ValueError, match="Failed to load image"):
            handler.current_image_path = image_path


def test_load_current_image_exception(handler: ImageHandler, temp_image_dir: str, qtbot: QtBot) -> None:
    """Test image loading when cv2.imread raises an exception."""
    image_path = str(Path(temp_image_dir) / "image1.png")
    
    # Mock cv2.imread to raise an exception
    with patch('cv2.imread') as mock_imread:
        mock_imread.side_effect = Exception("OpenCV error")
        
        with pytest.raises(Exception, match="OpenCV error"):
            handler.current_image_path = image_path


def test_signal_connections(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test that all signals are properly connected and emit correctly."""
    # Test image_directory_changed signal
    with tempfile.TemporaryDirectory() as temp_dir:
        with qtbot.waitSignal(handler.image_directory_changed, timeout=1000) as blocker:
            handler.image_directory = temp_dir
        assert blocker.args == [temp_dir]
    
    # Test state_reset signal
    with qtbot.waitSignal(handler.state_reset, timeout=1000):
        handler.reset()
    
    # Test current_image_path_changed signal with None
    with qtbot.waitSignal(handler.current_image_path_changed, timeout=1000):
        handler.current_image_path = None
    # Just verify the handler state is correct
    assert handler.current_image_path is None


def test_properties_read_only_behavior(handler: ImageHandler, qtbot: QtBot) -> None:
    """Test that read-only properties behave correctly."""
    # These should return the internal state
    assert handler.image_paths is None
    assert handler.image_index is None
    assert handler.current_image is None
    
    # Set some internal state
    handler._image_paths = ["test1.png", "test2.jpg"]
    handler._image_index = 1
    handler._current_image = np.array([1, 2, 3])
    
    # Properties should reflect the internal state
    assert handler.image_paths == ["test1.png", "test2.jpg"]
    assert handler.image_index == 1
    assert np.array_equal(handler.current_image, np.array([1, 2, 3]))
