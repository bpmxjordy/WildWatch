import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://wildsight:wildsight_dev@localhost:5432/wildsight",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

FRAME_INTERVAL_SECONDS = int(os.getenv("FRAME_INTERVAL_SECONDS", "60"))
MAX_CONCURRENT_EXTRACTIONS = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "4"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
FRAME_MAX_DIMENSION = int(os.getenv("FRAME_MAX_DIMENSION", "1280"))
DETECTION_RETENTION_DAYS = int(os.getenv("DETECTION_RETENTION_DAYS", "30"))

MODELS_DIR = os.getenv("MODELS_DIR", "/data/models")
FRAMES_DIR = os.getenv("FRAMES_DIR", "/data/frames")

os.makedirs(FRAMES_DIR, exist_ok=True)
