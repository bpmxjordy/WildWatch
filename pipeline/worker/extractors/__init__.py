from extractors.youtube import extract_youtube
from extractors.jpeg import extract_jpeg
from extractors.mjpeg import extract_mjpeg
from extractors.hls import extract_hls
from extractors.rtsp import extract_rtsp
from extractors.photosentinel import extract_photosentinel

EXTRACTORS = {
    "youtube": extract_youtube,
    "jpeg": extract_jpeg,
    "mjpeg": extract_mjpeg,
    "hls": extract_hls,
    "rtsp": extract_rtsp,
    "photosentinel": extract_photosentinel,
}


def extract_frame(source_url: str, output_path: str, platform: str = "youtube") -> bool:
    extractor = EXTRACTORS.get(platform)
    if extractor is None:
        return False
    return extractor(source_url, output_path)
