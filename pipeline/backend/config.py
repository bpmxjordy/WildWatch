import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://wildsight:wildsight_dev@localhost:5432/wildsight",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
    WTF_CSRF_ENABLED = False

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_MODEL_SIZE_MB", "2048")) * 1024 * 1024

    MODELS_DIR = os.getenv("MODELS_DIR", "/data/models")
    FRAMES_DIR = os.getenv("FRAMES_DIR", "/data/frames")
    EXPORTS_DIR = os.getenv("EXPORTS_DIR", "/data/exports")

    ALLOWED_MODEL_EXTENSIONS = {
        ".pt", ".onnx", ".engine", ".torchscript", ".zip",
    }

    GPU_VRAM_THRESHOLD = float(os.getenv("GPU_VRAM_THRESHOLD", "0.95"))
