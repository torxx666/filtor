FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y --no-install-recommends \
    curl ca-certificates ripgrep fd-find \
    poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra \
    pandoc p7zip-full unrar unzip python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# rga (pour ZIP/RAR/DOCX)
RUN curl -L https://github.com/phiresky/ripgrep-all/releases/download/v0.10.6/ripgrep_all-v0.10.6-x86_64-unknown-linux-musl.tar.gz \
    | tar xz -C /usr/local/bin --strip-components=1 --wildcards '*/rga' \
    && chmod +x /usr/local/bin/rga

# PDF extraction avec pdftotext + OCR fallback
ENV RGA_PDF_BACKEND=pdf2text
ENV RGA_OCR=1
ENV RGA_MAX_FILE_SIZE=500M

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir fastapi uvicorn[standard]

WORKDIR /app
COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
