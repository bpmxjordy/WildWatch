import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

SPECIESNET_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("SPECIESNET_CONFIDENCE_THRESHOLD", "0.15")
)
SPECIESNET_CLASSIFICATION_THRESHOLD: float = float(
    os.getenv("SPECIESNET_CLASSIFICATION_THRESHOLD", "0.5")
)

FRAME_INTERVAL_SECONDS: int = int(os.getenv("FRAME_INTERVAL_SECONDS", "20"))
MAX_CONCURRENT_EXTRACTIONS: int = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "4"))
FRAME_QUALITY: int = int(os.getenv("FRAME_QUALITY", "85"))
FRAME_MAX_DIMENSION: int = int(os.getenv("FRAME_MAX_DIMENSION", "1280"))

BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "5"))
OFFLINE_RETRY_INTERVAL: int = int(os.getenv("OFFLINE_RETRY_INTERVAL", "300"))

FRAMES_DIR: str = os.path.join(os.path.dirname(__file__), "frames")
os.makedirs(FRAMES_DIR, exist_ok=True)
