FROM python:3.10-slim

# Install dependensi sistem: FFmpeg & Font pendukung teks subtitle
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Setup user 1000 (standar keamanan Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    PORT=7860

WORKDIR /home/user/app

# Salin & pasang pustaka Python
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Salin file proyek
COPY --chown=user:user . .

# Buat folder kerja
RUN mkdir -p output temp assets data

EXPOSE 7860

CMD ["python", "web_app.py"]
