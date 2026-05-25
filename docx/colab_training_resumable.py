# Smart Vision System - Resumable Colab Training Script
# Designed for Google Colab + T4 GPU + Google Drive Persistence

# 1. Mount Google Drive to save progress permanently
from google.colab import drive
drive.mount('/content/drive')

# 2. Setup folders in your Drive
import os
# This folder will be created in your Google Drive
drive_path = "/content/drive/MyDrive/SVS_Project"
os.makedirs(drive_path, exist_ok=True)

# 3. Install necessary libraries
!pip install ultralytics roboflow

import yaml
from roboflow import Roboflow
from ultralytics import YOLO

# 4. Download dataset directly from Roboflow
rf = Roboflow(api_key="5jgnPDhEpqYl0Q2t58h2")
project = rf.workspace("ir-uz1qh").project("weapon-detection-jqd3x")
version = project.version(1)
dataset = version.download("yolov8")

# 5. Fix configuration paths
dataset_path = dataset.location
yaml_file = os.path.join(dataset_path, "data.yaml")

with open(yaml_file, 'r') as f:
    data = yaml.safe_load(f)

data['path'] = dataset_path
# Ensure splits point to correct subfolders
data['train'] = 'train/images'
data['val'] = 'valid/images'
data['test'] = 'test/images'

with open(yaml_file, 'w') as f:
    yaml.dump(data, f)

# 6. RESUMABLE LOGIC
# This checks if a previous training run exists in your Google Drive
checkpoint_path = os.path.join(drive_path, "svs_weapon_detection/weights/last.pt")

if os.path.exists(checkpoint_path):
    print(f"--- RESUMING SESSION ---")
    print(f"Found existing checkpoint at {checkpoint_path}")
    model = YOLO(checkpoint_path)
    resume_flag = True
else:
    print("--- STARTING FRESH SESSION ---")
    model = YOLO('yolov8n.pt')
    resume_flag = False

# 7. Start/Resume High-Performance Training
model.train(
    data=yaml_file,
    epochs=50,
    imgsz=640,         # High resolution
    batch=32,          # Optimized for T4 GPU (16GB VRAM)
    device=0,          # Force GPU
    project=drive_path, # SAVE EVERYTHING TO GOOGLE DRIVE
    name='svs_weapon_detection',
    resume=resume_flag, # Automatically picks up from the last epoch
    patience=15,       # Anti-overfitting
    close_mosaic=10    # Final sharpening
)

# After training finishes, your BEST model will be in your Google Drive at:
# /MyDrive/SVS_Project/svs_weapon_detection/weights/best.pt
