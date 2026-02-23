# ── Chatterbox TTS RunPod Serverless Worker ───────────────────────
# Base: RunPod's PyTorch image (includes CUDA + Python)
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

# Install system deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     libsndfile1     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir     runpod     chatterbox-tts     && pip cache purge

# Create voices directory (for optional reference audio)
RUN mkdir -p /voices

# Copy handler
COPY handler.py /app/handler.py

# Pre-download model weights at build time (faster cold starts)
# Uses huggingface_hub directly to avoid loading the full model graph
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download('ResembleAI/chatterbox', local_dir='/root/.cache/chatterbox_model'); \
print('Model weights downloaded')" \
    || echo 'Model weight pre-download skipped (will download at first request)'

# Copy any voice reference files
COPY voices/ /voices/

CMD ["python", "-u", "/app/handler.py"]
