import os
from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image

try:
    import tensorflow as tf  # type: ignore
    from tensorflow.keras.models import load_model  # type: ignore
except ImportError:  # TensorFlow not installed, fall back to stub
    tf = None
    load_model = None


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "resnet50_disease_model.h5"


CLASSES = [
    "Healthy",
    "Leaf Blight",
    "Bacterial Spot",
    "Rust",
    "Powdery Mildew",
]


_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if tf is not None and load_model is not None and MODEL_PATH.exists():
        _model = load_model(str(MODEL_PATH))
    return _model


_TREATMENTS: Dict[str, Dict[str, str]] = {
    "Healthy": {
        "treatment": "No treatment required. Maintain regular irrigation and monitoring.",
        "pesticide": "None",
    },
    "Leaf Blight": {
        "treatment": "Remove affected leaves and avoid overhead irrigation.",
        "pesticide": "Copper oxychloride or Mancozeb as per local recommendation.",
    },
    "Bacterial Spot": {
        "treatment": "Use disease-free seeds and practice crop rotation.",
        "pesticide": "Copper-based bactericides as advised by local extension officers.",
    },
    "Rust": {
        "treatment": "Destroy crop residues and use resistant varieties.",
        "pesticide": "Systemic fungicides like Propiconazole (follow label dose).",
    },
    "Powdery Mildew": {
        "treatment": "Improve air circulation and avoid excess nitrogen.",
        "pesticide": "Wettable sulphur or systemic fungicides as recommended.",
    },
}


def _stub_predict(img_path: str) -> Dict[str, object]:
    """Brightness-based stub so the app runs without TensorFlow model."""

    try:
        img = Image.open(img_path).convert("L").resize((128, 128))
    except Exception:
        return {
            "disease": "Unknown",
            "confidence": 0.0,
            "suggestion": "Could not read image. Please try another photo.",
        }

    arr = np.asarray(img, dtype="float32") / 255.0
    mean_brightness = float(arr.mean())

    if mean_brightness > 0.7:
        label = "Healthy"
        conf = 0.8
    elif mean_brightness > 0.5:
        label = "Leaf Blight"
        conf = 0.6
    elif mean_brightness > 0.3:
        label = "Bacterial Spot"
        conf = 0.6
    elif mean_brightness > 0.15:
        label = "Rust"
        conf = 0.6
    else:
        label = "Powdery Mildew"
        conf = 0.6

    info = _TREATMENTS.get(label, {})
    return {
        "disease": label,
        "confidence": conf,
        "suggestion": info.get("treatment", "Consult local agri officer."),
        "pesticide": info.get("pesticide", "As per local recommendations."),
    }


def predict_disease(img_path: str) -> Dict[str, object]:
    """Predict disease using ResNet50 model if available, else stub.

    Returns a dict: {disease, confidence, suggestion, pesticide}.
    """

    model = _load_model()
    if model is None:
        return _stub_predict(img_path)

    img = Image.open(img_path).resize((224, 224))
    arr = np.asarray(img, dtype="float32") / 255.0
    arr = np.expand_dims(arr, axis=0)

    preds = model.predict(arr)
    idx = int(np.argmax(preds[0]))
    prob = float(preds[0][idx])

    label = CLASSES[idx] if 0 <= idx < len(CLASSES) else "Unknown"
    info = _TREATMENTS.get(label, {})
    return {
        "disease": label,
        "confidence": prob,
        "suggestion": info.get("treatment", "Consult local agri officer."),
        "pesticide": info.get("pesticide", "As per local recommendations."),
    }
