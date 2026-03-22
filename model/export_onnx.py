import torch
import torch.nn as nn
from torchvision import models
from onnxruntime.quantization import quantize_dynamic, QuantType
import onnxruntime as ort
import numpy as np
import json, os

SAVE_DIR    = "model"
IMG_SIZE    = 224
DEVICE      = torch.device("cpu")

print("Loading class names...")
with open(f"{SAVE_DIR}/class_names.json") as f:
    class_names = json.load(f)
NUM_CLASSES = len(class_names)
print(f"Classes: {NUM_CLASSES}")

# ─── LOAD TRAINED MODEL ─────────────────────────────────────────────────────
print("Loading trained model...")
model = models.efficientnet_b0(weights=None)
model.classifier[1] = nn.Linear(
    model.classifier[1].in_features, NUM_CLASSES
)
model.load_state_dict(
    torch.load(f"{SAVE_DIR}/best_model.pt", map_location=DEVICE)
)
model.eval()

# ─── EXPORT TO ONNX ─────────────────────────────────────────────────────────
print("Exporting to ONNX...")
dummy_input = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
onnx_path   = f"{SAVE_DIR}/crop_disease_fp32.onnx"

torch.onnx.export(
    model,
    dummy_input,
    onnx_path,
    input_names=["image"],
    output_names=["logits"],
    dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
    opset_version=13,
)
print(f"FP32 model saved: {onnx_path}")

# ─── INT8 QUANTIZATION ──────────────────────────────────────────────────────
print("Applying INT8 dynamic quantization...")
quant_path = f"{SAVE_DIR}/crop_disease.onnx"
quantize_dynamic(
    model_input=onnx_path,
    model_output=quant_path,
    weight_type=QuantType.QInt8,
)
print(f"INT8 model saved: {quant_path}")

# ─── SIZE COMPARISON ────────────────────────────────────────────────────────
fp32_mb = os.path.getsize(onnx_path)  / 1024 / 1024
int8_mb = os.path.getsize(quant_path) / 1024 / 1024
print(f"\nModel size — FP32: {fp32_mb:.1f} MB → INT8: {int8_mb:.1f} MB "
      f"({(1 - int8_mb/fp32_mb)*100:.1f}% reduction)")

# ─── VERIFY ONNX INFERENCE ──────────────────────────────────────────────────
print("\nVerifying ONNX Runtime inference...")
sess = ort.InferenceSession(quant_path)
dummy = np.random.randn(1, 3, IMG_SIZE, IMG_SIZE).astype(np.float32)
out  = sess.run(["logits"], {"image": dummy})[0]
pred = np.argmax(out)
print(f"Test inference OK — predicted class index: {pred} ({class_names[pred]})")
print("\nPhase 1 export complete!")