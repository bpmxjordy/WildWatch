import logging
import subprocess
from pathlib import Path

from config import FRAME_MAX_DIMENSION

logger = logging.getLogger(__name__)


def ffmpeg_single_frame(input_url: str, output_path: str, timeout: int = 20, extra_args: list | None = None) -> bool:
    cmd = ["ffmpeg", "-y"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend([
        "-i", input_url,
        "-frames:v", "1",
        "-q:v", "2",
        "-vf", f"scale='min({FRAME_MAX_DIMENSION},iw)':-2",
        output_path,
    ])
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True)
        if result.returncode != 0:
            logger.warning("ffmpeg failed: %s", result.stderr.decode(errors="replace")[:200])
            return False
        return Path(output_path).exists()
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg timed out for %s", input_url)
        return False
    except FileNotFoundError:
        logger.error("ffmpeg not found")
        return False
