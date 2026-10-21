import os
from pathlib import Path
from dotenv import load_dotenv
import imageio_ffmpeg

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

# Pastikan folder ada
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", os.getenv("HF_TOKEN", ""))
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")

# Model Settings (Google AI Studio)
TEXT_MODEL = "gemini-3.8-flash"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
IMAGE_MODEL = "gemini-3.1-flash-image"

# Video Specs (YouTube Shorts)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# Path FFmpeg binary
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
