# syntax=docker/dockerfile:1.7
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_PREFER_BINARY=1 \
    HF_XET_HIGH_PERFORMANCE=1 \
    PATH="/opt/venv/bin:$PATH" \
    BERNINI_DIR="/opt/Bernini" \
    BERNINI_MODEL_DIR="/runpod-volume/models/Bernini-R-Diffusers" \
    BERNINI_RUNTIME_DIR="/opt/bernini-runtime" \
    BERNINI_RUNTIME_REPO="https://github.com/AvivK5498/Bernini-Runtime.git" \
    BERNINI_RUNTIME_BRANCH="main"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      python3.12 python3.12-dev python3.12-venv python3-pip \
      build-essential git git-lfs curl wget aria2 ffmpeg libgl1 libglib2.0-0 \
      ninja-build ca-certificates && \
    git lfs install && \
    python3.12 -m venv /opt/venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel packaging

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
      torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 \
      --index-url https://download.pytorch.org/whl/cu128

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
      https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/download/v0.7.16/flash_attn-2.8.3+cu128torch2.8-cp312-cp312-linux_x86_64.whl

RUN git clone --depth=1 https://github.com/bytedance/Bernini.git /opt/Bernini

RUN --mount=type=cache,target=/root/.cache/pip \
    grep -vE '^(--extra-index-url|torch==|torchvision==|torchaudio==)' /opt/Bernini/requirements.txt > /tmp/bernini-requirements.txt && \
    pip install -r /tmp/bernini-requirements.txt && \
    pip install --upgrade "huggingface_hub[hf_xet]" runpod requests && \
    pip install -e /opt/Bernini

COPY docker/start_serverless.sh /start_serverless.sh
COPY docker/prefetch_model.py /opt/prefetch_model.py
RUN chmod +x /start_serverless.sh

CMD ["/start_serverless.sh"]

