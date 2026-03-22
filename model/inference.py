import onnxruntime as ort
import numpy as np
from PIL import Image
import json

SAVE_DIR = "model"
IMG_SIZE = 224
MEAN     = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD      = np.array([0.229, 0.224, 0.225], dtype=np.float32)

with open(f"{SAVE_DIR}/class_names.json") as f:
    CLASS_NAMES = json.load(f)

sess = ort.InferenceSession(f"{SAVE_DIR}/crop_disease.onnx")

def preprocess(image: Image.Image) -> np.ndarray:
    image = image.convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    arr   = np.array(image, dtype=np.float32) / 255.0
    arr   = (arr - MEAN) / STD
    return arr.transpose(2, 0, 1)[np.newaxis]

def predict(image: Image.Image, top_k: int = 3) -> list[dict]:
    inp    = preprocess(image)
    logits = sess.run(["logits"], {"image": inp})[0][0]
    probs  = np.exp(logits) / np.exp(logits).sum()
    top    = np.argsort(probs)[::-1][:top_k]
    return [
        {
            "disease":    CLASS_NAMES[i],
            "confidence": round(float(probs[i]) * 100, 2),
        }
        for i in top
    ]

if __name__ == "__main__":
    from PIL import Image
    img = Image.new("RGB", (224, 224), color=(100, 150, 80))
    results = predict(img)
    print("Top predictions:")
    for r in results:
        print(f"  {r['disease']}: {r['confidence']}%")