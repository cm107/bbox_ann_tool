import json
import os
from typing import TypeVar
import numpy as np


ANN = TypeVar("ANN", bound='Annotation')

class Annotation:
    def __init__(self, label: str):
        self.label = label
    
    def to_dict(self):
        _dict = self.__dict__.copy()
        for key, val in _dict.items():
            if isinstance(val, np.ndarray):
                _dict[key] = val.tolist()
        _dict['shape'] = type(self).__name__
        assert _dict['shape'] != 'Annotation', "Base Annotation class cannot be instantiated directly"
        return _dict

    @classmethod
    def from_dict(cls, _dict: dict):
        shape = _dict.pop('shape', None)
        if shape is None:
            raise ValueError("Invalid annotation dictionary: missing 'shape' key")
        elif shape == 'Annotation':
            raise NotImplementedError("Base Annotation class cannot be instantiated directly")
        elif shape == 'BBox':
            return BBox.from_dict(_dict)
        else:
            raise ValueError(f"Unknown annotation shape: {shape}")

class Annotations(list[ANN]):
    def __init__(self, items: list[ANN]):
        super().__init__(items)

    def to_dict(self):
        return [ann.to_dict() for ann in self]

    @classmethod
    def from_dict(cls, ann_list: list[dict]):
        annotations = []
        for ann in ann_list:
            if not isinstance(ann, dict):
                raise ValueError(f"Invalid annotation format: expected dict, got {type(ann)}: {ann}")
            elif 'shape' in ann:
                # New format with shape key
                annotations.append(Annotation.from_dict(ann))
            elif 'bbox' in ann and 'label' in ann:
                # Old format with bbox and label keys - convert to BBox
                label = ann.get('label', '')
                bbox = ann.get('bbox', [0, 0, 0, 0])
                if len(bbox) >= 4:
                    import numpy as np
                    p0 = np.array([bbox[0], bbox[1]], dtype=np.float32)
                    p1 = np.array([bbox[2], bbox[3]], dtype=np.float32)
                    annotations.append(BBox(label, p0, p1))
            else:
                raise ValueError(f"Invalid annotation format: missing required keys in {ann}")
        return cls(annotations)

    def bboxes(self):
        """Return only BBox annotations"""
        return [ann for ann in self if isinstance(ann, BBox)]

    def save(self, path: str):
        json.dump(self.to_dict(), open(path, 'w'), indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Annotation file not found: {path}")
        data = json.load(open(path, 'r'))
        
        # Handle different JSON formats
        if isinstance(data, list):
            # Direct list format
            ann_list = data
        elif isinstance(data, dict) and "annotations" in data:
            # Old format with "annotations" key
            ann_list = data["annotations"]
        else:
            raise ValueError(f"Invalid annotation file format: {path}")
            
        return cls.from_dict(ann_list)

class BBox(Annotation):
    def __init__(self, label: str, p0: np.ndarray, p1: np.ndarray):
        super().__init__(label)
        self.p0 = p0
        self.p1 = p1

    @classmethod
    def from_dict(cls, _dict: dict):
        label = _dict.get('label', '')
        p0 = np.array(_dict.get('p0', [0, 0]), dtype=np.float32)
        p1 = np.array(_dict.get('p1', [0, 0]), dtype=np.float32)
        return cls(label, p0, p1)
