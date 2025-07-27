"""Unit tests for annotation data classes."""

import json
import os
import tempfile
import pytest
import numpy as np
from pathlib import Path

from bboxanntool.annotation import Annotation, Annotations, BBox


class TestBBox:
    """Test cases for BBox class."""
    
    def test_bbox_initialization(self):
        """Test BBox initialization with basic parameters."""
        label = "cat"
        p0 = np.array([10, 20], dtype=np.float32)
        p1 = np.array([30, 40], dtype=np.float32)
        
        bbox = BBox(label, p0, p1)
        
        assert bbox.label == "cat"
        assert np.array_equal(bbox.p0, p0)
        assert np.array_equal(bbox.p1, p1)
        assert isinstance(bbox.p0, np.ndarray)
        assert isinstance(bbox.p1, np.ndarray)

    def test_bbox_to_dict(self):
        """Test BBox to_dict conversion."""
        label = "dog"
        p0 = np.array([5, 15], dtype=np.float32)
        p1 = np.array([25, 35], dtype=np.float32)
        
        bbox = BBox(label, p0, p1)
        result = bbox.to_dict()
        
        expected = {
            'label': 'dog',
            'p0': [5.0, 15.0],
            'p1': [25.0, 35.0],
            'shape': 'BBox'
        }
        
        assert result == expected
        assert isinstance(result['p0'], list)
        assert isinstance(result['p1'], list)

    def test_bbox_from_dict_complete(self):
        """Test BBox from_dict with complete data."""
        data = {
            'label': 'bird',
            'p0': [1.5, 2.5],
            'p1': [3.5, 4.5]
        }
        
        bbox = BBox.from_dict(data)
        
        assert bbox.label == "bird"
        assert np.array_equal(bbox.p0, np.array([1.5, 2.5], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([3.5, 4.5], dtype=np.float32))

    def test_bbox_from_dict_defaults(self):
        """Test BBox from_dict with missing data uses defaults."""
        data = {}
        
        bbox = BBox.from_dict(data)
        
        assert bbox.label == ""
        assert np.array_equal(bbox.p0, np.array([0, 0], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([0, 0], dtype=np.float32))

    def test_bbox_from_dict_partial(self):
        """Test BBox from_dict with partial data."""
        data = {
            'label': 'fish',
            'p0': [10, 20]
            # p1 missing
        }
        
        bbox = BBox.from_dict(data)
        
        assert bbox.label == "fish"
        assert np.array_equal(bbox.p0, np.array([10, 20], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([0, 0], dtype=np.float32))

    def test_bbox_roundtrip_conversion(self):
        """Test BBox to_dict and from_dict roundtrip conversion."""
        original = BBox("test", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        
        # Convert to dict and back
        data = original.to_dict()
        reconstructed = BBox.from_dict(data)
        
        assert reconstructed.label == original.label
        assert np.array_equal(reconstructed.p0, original.p0)
        assert np.array_equal(reconstructed.p1, original.p1)


class TestAnnotation:
    """Test cases for base Annotation class."""
    
    def test_annotation_cannot_be_instantiated_directly(self):
        """Test that base Annotation class cannot be used directly for to_dict."""
        # Note: We can still create instances for testing, but to_dict should fail
        ann = Annotation("test")
        
        with pytest.raises(AssertionError, match="Base Annotation class cannot be instantiated directly"):
            ann.to_dict()

    def test_annotation_from_dict_bbox_shape(self):
        """Test Annotation.from_dict with BBox shape."""
        data = {
            'label': 'cat',
            'p0': [10, 20],
            'p1': [30, 40],
            'shape': 'BBox'
        }
        
        result = Annotation.from_dict(data)
        
        assert isinstance(result, BBox)
        assert result.label == "cat"
        assert np.array_equal(result.p0, np.array([10, 20], dtype=np.float32))
        assert np.array_equal(result.p1, np.array([30, 40], dtype=np.float32))

    def test_annotation_from_dict_missing_shape(self):
        """Test Annotation.from_dict with missing shape key."""
        data = {
            'label': 'cat',
            'p0': [10, 20],
            'p1': [30, 40]
        }
        
        with pytest.raises(ValueError, match="Invalid annotation dictionary: missing 'shape' key"):
            Annotation.from_dict(data)

    def test_annotation_from_dict_base_annotation_shape(self):
        """Test Annotation.from_dict with 'Annotation' shape."""
        data = {
            'label': 'cat',
            'shape': 'Annotation'
        }
        
        with pytest.raises(NotImplementedError, match="Base Annotation class cannot be instantiated directly"):
            Annotation.from_dict(data)

    def test_annotation_from_dict_unknown_shape(self):
        """Test Annotation.from_dict with unknown shape."""
        data = {
            'label': 'cat',
            'shape': 'UnknownShape'
        }
        
        with pytest.raises(ValueError, match="Unknown annotation shape: UnknownShape"):
            Annotation.from_dict(data)


class TestAnnotations:
    """Test cases for Annotations collection class."""
    
    def test_annotations_initialization(self):
        """Test Annotations initialization."""
        bbox1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        bbox2 = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
        
        annotations = Annotations([bbox1, bbox2])
        
        assert len(annotations) == 2
        assert annotations[0] == bbox1
        assert annotations[1] == bbox2
        assert isinstance(annotations, list)

    def test_annotations_to_dict(self):
        """Test Annotations to_dict conversion."""
        bbox1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        bbox2 = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
        
        annotations = Annotations([bbox1, bbox2])
        result = annotations.to_dict()
        
        expected = [
            {'label': 'cat', 'p0': [1.0, 2.0], 'p1': [3.0, 4.0], 'shape': 'BBox'},
            {'label': 'dog', 'p0': [5.0, 6.0], 'p1': [7.0, 8.0], 'shape': 'BBox'}
        ]
        
        assert result == expected

    def test_annotations_from_dict_new_format(self):
        """Test Annotations from_dict with new format (shape key)."""
        data = [
            {'label': 'cat', 'p0': [1, 2], 'p1': [3, 4], 'shape': 'BBox'},
            {'label': 'dog', 'p0': [5, 6], 'p1': [7, 8], 'shape': 'BBox'}
        ]
        
        annotations = Annotations.from_dict(data)
        
        assert len(annotations) == 2
        assert isinstance(annotations[0], BBox)
        assert isinstance(annotations[1], BBox)
        assert annotations[0].label == "cat"
        assert annotations[1].label == "dog"

    def test_annotations_from_dict_old_format(self):
        """Test Annotations from_dict with old format (bbox key)."""
        data = [
            {'label': 'cat', 'bbox': [1, 2, 3, 4]},
            {'label': 'dog', 'bbox': [5, 6, 7, 8]}
        ]
        
        annotations = Annotations.from_dict(data)
        
        assert len(annotations) == 2
        assert isinstance(annotations[0], BBox)
        assert isinstance(annotations[1], BBox)
        assert annotations[0].label == "cat"
        assert annotations[1].label == "dog"
        assert np.array_equal(annotations[0].p0, np.array([1, 2], dtype=np.float32))
        assert np.array_equal(annotations[0].p1, np.array([3, 4], dtype=np.float32))

    def test_annotations_from_dict_old_format_short_bbox(self):
        """Test Annotations from_dict with old format but bbox too short."""
        data = [
            {'label': 'cat', 'bbox': [1, 2, 3]}  # Only 3 elements
        ]
        
        # Should be skipped silently due to len(bbox) >= 4 check
        annotations = Annotations.from_dict(data)
        assert len(annotations) == 0

    def test_annotations_from_dict_mixed_formats(self):
        """Test Annotations from_dict with mixed old and new formats."""
        data = [
            {'label': 'cat', 'bbox': [1, 2, 3, 4]},  # Old format
            {'label': 'dog', 'p0': [5, 6], 'p1': [7, 8], 'shape': 'BBox'}  # New format
        ]
        
        annotations = Annotations.from_dict(data)
        
        assert len(annotations) == 2
        assert annotations[0].label == "cat"
        assert annotations[1].label == "dog"

    def test_annotations_from_dict_invalid_format(self):
        """Test Annotations from_dict with invalid format."""
        data = [
            {'invalid': 'data'}  # Missing both 'shape' and 'bbox'/'label'
        ]
        
        with pytest.raises(ValueError, match="Invalid annotation format: missing required keys"):
            Annotations.from_dict(data)

    def test_annotations_from_dict_non_dict_item(self):
        """Test Annotations from_dict with non-dict item."""
        data = [
            "not a dict"
        ]
        
        with pytest.raises(ValueError, match="Invalid annotation format: expected dict, got <class 'str'>"):
            Annotations.from_dict(data)

    def test_annotations_bboxes_filter(self):
        """Test Annotations bboxes() method."""
        bbox1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        bbox2 = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
        
        annotations = Annotations([bbox1, bbox2])
        bboxes = annotations.bboxes()
        
        assert len(bboxes) == 2
        assert bboxes[0] == bbox1
        assert bboxes[1] == bbox2

    def test_annotations_save_and_load(self):
        """Test Annotations save and load functionality."""
        bbox1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        bbox2 = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
        
        annotations = Annotations([bbox1, bbox2])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Save annotations
            annotations.save(tmp_path)
            
            # Verify file exists and has content
            assert os.path.isfile(tmp_path)
            
            # Load annotations
            loaded_annotations = Annotations.load(tmp_path)
            
            # Verify loaded data
            assert len(loaded_annotations) == 2
            assert loaded_annotations[0].label == "cat"
            assert loaded_annotations[1].label == "dog"
            assert np.array_equal(loaded_annotations[0].p0, np.array([1, 2], dtype=np.float32))
            assert np.array_equal(loaded_annotations[0].p1, np.array([3, 4], dtype=np.float32))
            
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_annotations_load_direct_list_format(self):
        """Test Annotations load with direct list format."""
        data = [
            {'label': 'cat', 'p0': [1, 2], 'p1': [3, 4], 'shape': 'BBox'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            loaded_annotations = Annotations.load(tmp_path)
            
            assert len(loaded_annotations) == 1
            assert loaded_annotations[0].label == "cat"
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_annotations_load_old_format_with_annotations_key(self):
        """Test Annotations load with old format containing 'annotations' key."""
        data = {
            "annotations": [
                {'label': 'cat', 'bbox': [1, 2, 3, 4]}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            loaded_annotations = Annotations.load(tmp_path)
            
            assert len(loaded_annotations) == 1
            assert loaded_annotations[0].label == "cat"
            assert np.array_equal(loaded_annotations[0].p0, np.array([1, 2], dtype=np.float32))
            assert np.array_equal(loaded_annotations[0].p1, np.array([3, 4], dtype=np.float32))
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_annotations_load_nonexistent_file(self):
        """Test Annotations load with nonexistent file."""
        with pytest.raises(FileNotFoundError, match="Annotation file not found"):
            Annotations.load("/nonexistent/file.json")

    def test_annotations_load_invalid_format(self):
        """Test Annotations load with invalid file format."""
        data = "invalid json content"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="Invalid annotation file format"):
                Annotations.load(tmp_path)
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_annotations_roundtrip_conversion(self):
        """Test complete roundtrip conversion: create -> to_dict -> from_dict."""
        original_bbox1 = BBox("cat", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        original_bbox2 = BBox("dog", np.array([5, 6], dtype=np.float32), np.array([7, 8], dtype=np.float32))
        
        original_annotations = Annotations([original_bbox1, original_bbox2])
        
        # Convert to dict and back
        data = original_annotations.to_dict()
        reconstructed_annotations = Annotations.from_dict(data)
        
        assert len(reconstructed_annotations) == len(original_annotations)
        
        for orig, recon in zip(original_annotations, reconstructed_annotations):
            assert orig.label == recon.label
            assert np.array_equal(orig.p0, recon.p0)
            assert np.array_equal(orig.p1, recon.p1)

    def test_annotations_empty_list(self):
        """Test Annotations with empty list."""
        annotations = Annotations([])
        
        assert len(annotations) == 0
        assert annotations.to_dict() == []
        assert annotations.bboxes() == []

    def test_annotations_from_dict_empty_list(self):
        """Test Annotations from_dict with empty list."""
        annotations = Annotations.from_dict([])
        
        assert len(annotations) == 0
        assert isinstance(annotations, Annotations)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_bbox_with_zero_coordinates(self):
        """Test BBox with zero coordinates."""
        bbox = BBox("empty", np.array([0, 0], dtype=np.float32), np.array([0, 0], dtype=np.float32))
        
        assert bbox.label == "empty"
        assert np.array_equal(bbox.p0, np.array([0, 0], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([0, 0], dtype=np.float32))

    def test_bbox_with_negative_coordinates(self):
        """Test BBox with negative coordinates."""
        bbox = BBox("negative", np.array([-10, -20], dtype=np.float32), np.array([-5, -15], dtype=np.float32))
        
        assert bbox.label == "negative"
        assert np.array_equal(bbox.p0, np.array([-10, -20], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([-5, -15], dtype=np.float32))

    def test_bbox_with_empty_label(self):
        """Test BBox with empty label."""
        bbox = BBox("", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        
        assert bbox.label == ""
        assert np.array_equal(bbox.p0, np.array([1, 2], dtype=np.float32))
        assert np.array_equal(bbox.p1, np.array([3, 4], dtype=np.float32))

    def test_bbox_with_very_long_label(self):
        """Test BBox with very long label."""
        long_label = "a" * 1000
        bbox = BBox(long_label, np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        
        assert bbox.label == long_label
        assert len(bbox.label) == 1000

    def test_bbox_with_special_characters_in_label(self):
        """Test BBox with special characters in label."""
        special_label = "café_dog-123@test.com"
        bbox = BBox(special_label, np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        
        assert bbox.label == special_label

    def test_annotations_save_ensures_ascii_false(self):
        """Test that Annotations.save preserves Unicode characters."""
        bbox = BBox("café", np.array([1, 2], dtype=np.float32), np.array([3, 4], dtype=np.float32))
        annotations = Annotations([bbox])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            annotations.save(tmp_path)
            
            # Read the file and check that Unicode is preserved
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "café" in content  # Should not be escaped
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
