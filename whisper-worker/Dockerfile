FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install "setuptools==80.9.0" wheel

RUN python3 -m pip install \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

RUN python3 -m pip install --no-build-isolation "openai-whisper==20231117"

WORKDIR /app

COPY transcribe_folder.py /app/transcribe_folder.py

CMD ["python3", "/app/transcribe_folder.py"]
