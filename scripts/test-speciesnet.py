"""Quick test: grab one frame from a stream, run SpeciesNet, print result."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from extractor import extract_frame
from detector import SpeciesDetector, extract_common_name


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=ydYDqZQpim8"
    country = sys.argv[2] if len(sys.argv) > 2 else None
    output = os.path.join(os.path.dirname(__file__), "..", "agent", "frames", "test.jpg")

    print(f"Extracting frame from: {url}")
    if not extract_frame(url, output):
        print("Frame extraction failed. Is the stream live? Is yt-dlp installed?")
        sys.exit(1)

    print(f"Frame saved to: {output}")
    print("Running SpeciesNet...")

    detector = SpeciesDetector()
    results = detector.predict([output], country_code=country)

    if not results:
        print("No predictions returned.")
        sys.exit(1)

    for r in results:
        pred = r.get("prediction", {})
        label = pred.get("label", "unknown")
        common = extract_common_name(label)
        category = pred.get("category", "unknown")
        conf = pred.get("confidence", 0)
        source = pred.get("prediction_source", "unknown")

        print(f"\nCategory: {category}")
        print(f"Species:  {common or 'N/A'} ({label})")
        print(f"Confidence: {conf:.1%}")
        print(f"Source: {source}")

        if "detections" in r:
            for det in r["detections"]:
                print(f"  Detection: {det['category']} ({det['conf']:.1%}) bbox={det['bbox']}")


if __name__ == "__main__":
    main()
