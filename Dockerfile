# ── Chatterbox TTS RunPod Serverless Worker ───────────────────────
# Base: NVIDIA CUDA runtime (clean slate)
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install Python 3.11 + system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    ffmpeg libsndfile1 git \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Step 1: Install PyTorch + torchaudio + torchvision (matching CUDA 12.4 set)
RUN pip install --no-cache-dir \
    torch==2.4.0 torchaudio==2.4.0 torchvision==0.19.0 \
    --index-url https://download.pytorch.org/whl/cu124

# Step 2: Install chatterbox-tts WITHOUT letting it override torch/torchvision
RUN pip install --no-cache-dir --no-deps chatterbox-tts

# Step 3: Install remaining chatterbox dependencies (except torch/torchvision)
RUN pip install --no-cache-dir \
    runpod \
    transformers \
    safetensors \
    huggingface_hub \
    soundfile \
    librosa \
    einops \
    encodec \
    numpy \
    scipy \
    && pip cache purge

# Create voices directory (for optional reference audio)
RUN mkdir -p /voices

# Copy handler
COPY handler.py /app/handler.py

# Pre-download model weights at build time (faster cold starts)
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download('ResembleAI/chatterbox', local_dir='/root/.cache/chatterbox_model'); \
print('Model weights downloaded')" \
    || echo 'Model weight pre-download skipped (will download at first request)'

# Copy any voice reference files
COPY voices/ /voices/

CMD ["python", "-u", "/app/handler.py"]
