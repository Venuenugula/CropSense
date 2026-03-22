import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm
import os, json, matplotlib.pyplot as plt

# ─── CONFIG ─────────────────────────────────────────────────────────────────
DATA_DIR = "data/color"
SAVE_DIR    = "model"
BATCH_SIZE  = 32
EPOCHS      = 15
LR          = 1e-4
IMG_SIZE    = 224
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Crops we care about — filter only these from PlantVillage
TARGET_CROPS = [
    "Corn_(maize)",
    "Tomato",
    "Potato",
    "Grape",
    "Apple",
    "Pepper,_bell",
    "Peach",
]

print(f"Training on: {DEVICE}")

# ─── TRANSFORMS ─────────────────────────────────────────────────────────────
train_transforms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

val_transforms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

# ─── DATASET ────────────────────────────────────────────────────────────────
def filter_dataset(data_dir):
    """Keep only classes that match our target crops."""
    full = datasets.ImageFolder(data_dir)
    filtered_classes = [
        c for c in full.classes
        if any(crop.lower() in c.lower() for crop in TARGET_CROPS)
    ]
    print(f"\nFound {len(filtered_classes)} disease classes:")
    for c in filtered_classes:
        print(f"  {c}")

    filtered_idx = [
        i for i, (_, label) in enumerate(full.samples)
        if full.classes[label] in filtered_classes
    ]

    class_to_idx = {c: i for i, c in enumerate(filtered_classes)}
    filtered_samples = [
        (path, class_to_idx[full.classes[label]])
        for path, label in full.samples
        if full.classes[label] in filtered_classes
    ]

    full.samples  = filtered_samples
    full.targets  = [s[1] for s in filtered_samples]
    full.classes  = filtered_classes
    full.class_to_idx = class_to_idx
    return full

print("\nLoading dataset...")
full_dataset = filter_dataset(DATA_DIR)
print(f"Total images: {len(full_dataset)}")

train_size = int(0.8 * len(full_dataset))
val_size   = len(full_dataset) - train_size
train_ds, val_ds = random_split(full_dataset, [train_size, val_size])

train_ds.dataset.transform = train_transforms
val_ds.dataset.transform   = val_transforms

train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE,
                          shuffle=True,  num_workers=2, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE,
                          shuffle=False, num_workers=2, pin_memory=True)

NUM_CLASSES = len(full_dataset.classes)
print(f"Classes: {NUM_CLASSES}  |  Train: {train_size}  |  Val: {val_size}")

# ─── MODEL ──────────────────────────────────────────────────────────────────
model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, NUM_CLASSES)
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

# ─── TRAINING LOOP ──────────────────────────────────────────────────────────
history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
best_val_acc = 0.0

for epoch in range(1, EPOCHS + 1):
    # Train
    model.train()
    train_loss, train_correct, train_total = 0.0, 0, 0
    for images, labels in tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS} [Train]"):
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        train_loss    += loss.item() * images.size(0)
        preds          = outputs.argmax(dim=1)
        train_correct += (preds == labels).sum().item()
        train_total   += labels.size(0)

    scheduler.step()

    # Validate
    model.eval()
    val_loss, val_correct, val_total = 0.0, 0, 0
    with torch.no_grad():
        for images, labels in tqdm(val_loader, desc=f"Epoch {epoch}/{EPOCHS} [Val]"):
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            loss    = criterion(outputs, labels)
            val_loss    += loss.item() * images.size(0)
            preds        = outputs.argmax(dim=1)
            val_correct += (preds == labels).sum().item()
            val_total   += labels.size(0)

    t_loss = train_loss / train_total
    v_loss = val_loss   / val_total
    t_acc  = train_correct / train_total * 100
    v_acc  = val_correct   / val_total   * 100

    history["train_loss"].append(t_loss)
    history["val_loss"].append(v_loss)
    history["train_acc"].append(t_acc)
    history["val_acc"].append(v_acc)

    print(f"\nEpoch {epoch:02d} | "
          f"Train Loss: {t_loss:.4f} Acc: {t_acc:.2f}% | "
          f"Val Loss: {v_loss:.4f} Acc: {v_acc:.2f}%")

    if v_acc > best_val_acc:
        best_val_acc = v_acc
        torch.save(model.state_dict(), f"{SAVE_DIR}/best_model.pt")
        print(f"  Saved best model — Val Acc: {v_acc:.2f}%")

# ─── SAVE ARTIFACTS ─────────────────────────────────────────────────────────
with open(f"{SAVE_DIR}/class_names.json", "w") as f:
    json.dump(full_dataset.classes, f, indent=2)
print(f"\nClass names saved to {SAVE_DIR}/class_names.json")

# Plot training curves
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
ax1.plot(history["train_loss"], label="Train Loss")
ax1.plot(history["val_loss"],   label="Val Loss")
ax1.set_title("Loss"); ax1.legend(); ax1.set_xlabel("Epoch")
ax2.plot(history["train_acc"], label="Train Acc")
ax2.plot(history["val_acc"],   label="Val Acc")
ax2.set_title("Accuracy (%)"); ax2.legend(); ax2.set_xlabel("Epoch")
plt.tight_layout()
plt.savefig(f"{SAVE_DIR}/training_curves.png", dpi=120)
print(f"Training curves saved.")
print(f"\nBest Val Accuracy: {best_val_acc:.2f}%")
print("Phase 1 training complete!")