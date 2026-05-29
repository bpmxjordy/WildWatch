import logging

from extractors.base import ffmpeg_single_frame

logger = logging.getLogger(__name__)


def extract_rtsp(source_url: str, output_path: str) -> bool:
    return ffmpeg_single_frame(
        source_url,
        output_path,
        timeout=20,
        extra_args=["-rtsp_transport", "tcp"],
    )
