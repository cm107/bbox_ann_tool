from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import numpy.typing as npt

@dataclass
class BBox:
    p0: npt.NDArray[np.float32]
    p1: npt.NDArray[np.float32]

    @property
    def x(self) -> float:
        return self.p0[0]
    
    @property
    def y(self) -> float:
        return self.p0[1]
    
    @property
    def cx(self) -> float:
        return (self.p0[0] + self.p1[0]) / 2
    
    @property
    def cy(self) -> float:
        return (self.p0[1] + self.p1[1]) / 2
    
    @property
    def center(self) -> npt.NDArray[np.float32]:
        return np.array([(self.p0[0] + self.p1[0]) / 2, (self.p0[1] + self.p1[1]) / 2], dtype=np.float32)

    @property
    def width(self) -> float:
        return self.p1[0] - self.p0[0]
    
    @property
    def height(self) -> float:
        return self.p1[1] - self.p0[1]

    def crop(self, image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
        """
        Crop the image to the bounding box defined by this BBox.
        """
        x0, y0 = self.p0.astype(int).tolist()
        x1, y1 = self.p1.astype(int).tolist()
        xmin, xmax = min(x0, x1), max(x0, x1)
        ymin, ymax = min(y0, y1), max(y0, y1)
        return image[ymin:ymax, xmin:xmax]
