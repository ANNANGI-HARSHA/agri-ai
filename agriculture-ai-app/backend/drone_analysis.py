from pathlib import Path
from typing import Dict

import numpy as np

try:
    import cv2  # type: ignore
except ImportError:
    cv2 = None

from PIL import Image, ImageFilter


def _analyze_with_pillow(image_path: str) -> Dict[str, object]:
    img = Image.open(image_path).convert("L")
    edges = img.filter(ImageFilter.FIND_EDGES)
    arr = np.asarray(edges, dtype="float32")
    score = float(arr.mean())  # proxy for structure

    if score > 40:
        stress = "Possible crop stress detected"
    else:
        stress = "Field appears broadly healthy"

    return {"health_score": round(100 - min(score, 90), 2), "stress_result": stress}


def analyze_drone_image(image_path: str) -> Dict[str, object]:
    """Analyze drone image using OpenCV if available, else Pillow.

    Returns dict with health_score and stress_result.
    """

    if cv2 is None:
        return _analyze_with_pillow(image_path)

    img = cv2.imread(image_path)
    if img is None:
        return {"health_score": 0.0, "stress_result": "Unable to read image"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    stressed_area = float(edges.sum())

    # Simple normalization
    norm = stressed_area / (gray.shape[0] * gray.shape[1])
    if norm > 80:
        stress = "Severe stress and variability detected"
    elif norm > 40:
        stress = "Moderate crop stress detected"
    elif norm > 10:
        stress = "Mild stress in some patches"
    else:
        stress = "Field appears healthy"

    health_score = max(0.0, 100.0 - norm)
    return {"health_score": round(health_score, 2), "stress_result": stress}
