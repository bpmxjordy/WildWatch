FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip \
    ffmpeg curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

RUN useradd -m -r appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/models /data/frames
RUN chown -R appuser:appuser /app /data

USER appuser

ENV TORCH_HOME=/data/.cache/torch
ENV HF_HOME=/data/.cache/huggingface

CMD ["python", "main.py"]
