import logging

from extractors.base import ffmpeg_single_frame

logger = logging.getLogger(__name__)


def extract_mjpeg(source_url: str, output_path: str) -> bool:
    return ffmpeg_single_frame(source_url, output_path, timeout=15)
