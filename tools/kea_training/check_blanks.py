import json
from collections import Counter

with open(r"D:\AI\WildWatch\tools\kea_training\metadata.json") as f:
    meta = json.load(f)

# Check if any images have 'empty' in their file path
empty_path = [img for img in meta["images"] if "empty" in img.get("file_name", "").lower()]
print(f"Images with 'empty' in path: {len(empty_path)}")
for img in empty_path[:10]:
    fn = img["file_name"]
    print(f"  {fn}")

# Check species field values
species = Counter(img.get("species", "") for img in meta["images"])
print(f"\nAll species values ({len(species)} unique):")
for s, c in species.most_common():
    print(f"  {s}: {c:,}")
