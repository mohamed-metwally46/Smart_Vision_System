# ── Smart Vision System — Backend Dockerfile ──────────────────────────────────
# Builds the FastAPI backend + AI pipeline (YOLOv8 + ByteTrack)
#
# Build context: ./backend   (run from project root: docker compose build)

FROM python:3.11-slim

# ── System dependencies ────────────────────────────────────────────────────────
# Required by OpenCV, PyTorch, and YOLOv8 at runtime inside the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────────
# Copy requirements first so Docker can cache this layer.
# Only re-runs pip install when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ───────────────────────────────────────────────────────────
COPY . .

# ── Pre-download YOLOv8n model weights ────────────────────────────────────────
# Downloads ~6MB yolov8n.pt into the image at build time so the container
# starts instantly without a network fetch on first run.
# Skip this step if you mount ./models as a volume (the volume wins).
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" || true

# ── Port ───────────────────────────────────────────────────────────────────────
EXPOSE 3000

# ── Default command (overridden by docker-compose for dev --reload) ────────────
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "3000"]
