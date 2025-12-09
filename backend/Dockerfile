# backend/Dockerfile – ANTI-ERREUR DEFINITIVE 2025
FROM python:3.12-slim

# 1. Installe curl + TOUS les outils nécessaires
RUN apt update && apt install -y --no-install-recommends \
    curl \
    ca-certificates \
    ripgrep \
    fd-find \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    pandoc \
    catdoc \
    xlsx2csv \
    p7zip-full \
    unrar-free \
    unzip \
    gzip \
    bzip2 \
    tar \
    && rm -rf /var/lib/apt/lists/*

# 2. Installe ripgrep-all (version 0.10.6 stable – URL VERIFIEE et fonctionnelle)
RUN curl -L https://github.com/phiresky/ripgrep-all/releases/download/v0.10.6/ripgrep_all-v0.10.6-x86_64-unknown-linux-musl.tar.gz \
    | tar xz -C /usr/local/bin --strip-components=1 --wildcards '*/rga' \
    && chmod +x /usr/local/bin/rga

# 3. Python deps
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart

# 4. Copie ton code
WORKDIR /app
COPY main.py .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]