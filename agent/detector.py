from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SpeciesDetector:
    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from speciesnet import SpeciesNet as SpeciesNetModel
        logger.info("Loading SpeciesNet model (first run downloads ~420MB)...")
        self._model = SpeciesNetModel(
            "kaggle:google/speciesnet/pyTorch/v4.0.2a/1",
            components="all",
        )
        logger.info("SpeciesNet model loaded.")

    def predict(
        self, image_paths: list[str], country_code: str | None = None
    ) -> list[dict]:
        if not image_paths:
            return []

        self._load()
        try:
            result = self._model.predict(
                filepaths=image_paths,
                country=country_code,
                run_mode="single_thread",
                progress_bars=False,
            )
        except Exception:
            logger.exception("SpeciesNet inference failed")
            return []

        predictions = result.get("predictions", [])
        return predictions


# ---------------------------------------------------------------------------
# Taxonomy-aware classification
#
# SpeciesNet labels are full taxonomy strings:
#   "<uuid>;<class>;<order>;<family>;<genus>;<species>;<common_name>"
# The whole hierarchy is embedded in every prediction, so we can roll a set of
# uncertain species guesses UP the tree by summing their probability mass and
# committing to the deepest rank that clears a confidence threshold. That turns
# "10 uncertain penguin species" into a confident "Penguin" instead of "animal".
# ---------------------------------------------------------------------------

import os

RANK_SEQUENCE = ["class", "order", "family", "genus", "species"]

# How much SpeciesNet's own (geofenced) species call we trust outright.
SPECIES_TRUST = float(os.getenv("SPECIES_TRUST", "0.5"))

# Two separate MegaDetector box-confidence floors:
#   RECORD_MIN_CONF - below this a box is dropped as noise and not stored.
#   DRAW_MIN_CONF   - boxes below this are still recorded but NOT drawn on the
#                     snapshot, so the image only shows confident boxes.
# Recording must not depend on the draw threshold, or low-box frames would store
# no detection row and the UI would fall back to stale labels.
RECORD_MIN_CONF = float(os.getenv("DETECTION_RECORD_CONFIDENCE", "0.5"))
DRAW_MIN_CONF = float(os.getenv("DETECTION_MIN_CONFIDENCE", "0.6"))

# Cumulative probability mass required to commit at each rank. Coarser ranks
# (family/order) are safe, general statements so they commit more readily;
# a specific species call demands strong evidence. Setting the ROLLUP_THRESHOLD
# env var overrides all ranks with a single uniform value.
_UNIFORM = os.getenv("ROLLUP_THRESHOLD")
if _UNIFORM:
    _v = float(_UNIFORM)
    RANK_THRESHOLDS = {"class": 0.0, "order": _v, "family": _v, "genus": _v, "species": _v}
else:
    RANK_THRESHOLDS = {"class": 0.0, "order": 0.40, "family": 0.45, "genus": 0.55, "species": 0.60}

# Class-level generic fallbacks (always stable — class rarely flips).
CLASS_COMMON = {
    "aves": "Bird",
    "mammalia": "Mammal",
    "reptilia": "Reptile",
    "amphibia": "Amphibian",
    "actinopterygii": "Fish",
    "chondrichthyes": "Fish",
}

# Friendly common names for higher taxa relevant to wildlife cameras.
# Extend freely — unknown taxa fall back to the class-level generic.
SCI_TO_COMMON = {
    # families
    "spheniscidae": "Penguin", "ursidae": "Bear", "cervidae": "Deer",
    "strigidae": "Owl", "tytonidae": "Barn Owl", "accipitridae": "Bird of Prey",
    "pandionidae": "Osprey", "falconidae": "Falcon", "elephantidae": "Elephant",
    "felidae": "Wild Cat", "canidae": "Wild Canine", "procyonidae": "Raccoon",
    "mustelidae": "Mustelid", "giraffidae": "Giraffe", "rhinocerotidae": "Rhino",
    "hippopotamidae": "Hippo", "equidae": "Wild Horse", "bovidae": "Bovine",
    "hominidae": "Great Ape", "cercopithecidae": "Monkey", "lemuridae": "Lemur",
    "ardeidae": "Heron", "phoenicopteridae": "Flamingo", "alcidae": "Auk",
    "coraciidae": "Roller", "scolopacidae": "Sandpiper", "trichechidae": "Manatee",
    "cheloniidae": "Sea Turtle", "emydidae": "Pond Turtle", "bathyergidae": "Mole-rat",
    "suidae": "Wild Pig", "macropodidae": "Kangaroo", "phascolarctidae": "Koala",
    "delphinidae": "Dolphin",
    # orders
    "testudines": "Turtle", "primates": "Primate", "proboscidea": "Elephant",
    "cetacea": "Whale or Dolphin", "rodentia": "Rodent", "chiroptera": "Bat",
    "sphenisciformes": "Penguin", "pelecaniformes": "Waterbird",
    "anseriformes": "Waterfowl", "passeriformes": "Songbird",
    # genera
    "panthera": "Big Cat", "ursus": "Bear", "canis": "Wolf", "equus": "Zebra",
}


def _split_taxon(label: str) -> dict:
    """Parse a SpeciesNet taxonomy string into a rank->name dict (+ common)."""
    p = (label or "").split(";")
    p += [""] * (7 - len(p))
    return {
        "class": p[1].strip().lower(),
        "order": p[2].strip().lower(),
        "family": p[3].strip().lower(),
        "genus": p[4].strip().lower(),
        "species": p[5].strip().lower(),
        "common": p[6].strip(),
    }


def _titlecase(s: str) -> str:
    return " ".join(w.capitalize() for w in s.split()) if s else s


def common_for(rank: str, tax: dict) -> str:
    """Human-friendly common name for a taxon at a given rank."""
    if rank == "species":
        return _titlecase(tax.get("common") or tax.get("species") or "Animal")
    name = SCI_TO_COMMON.get(tax.get(rank, ""))
    if name:
        return name
    return CLASS_COMMON.get(tax.get("class", ""), _titlecase(tax.get(rank, "")) or "Animal")


def _deepest_rank(tax: dict) -> str | None:
    for rank in reversed(RANK_SEQUENCE):  # species -> class
        if tax.get(rank):
            return rank
    return None


def lineage_key(tax: dict, rank: str) -> tuple:
    idx = RANK_SEQUENCE.index(rank)
    return tuple(tax.get(r, "") for r in RANK_SEQUENCE[: idx + 1])


def tax_from_key(key: tuple) -> dict:
    tax = {r: "" for r in RANK_SEQUENCE}
    for r, v in zip(RANK_SEQUENCE, key):
        tax[r] = v
    return tax


def _mass_rollup(classes: list, scores: list):
    """Sum probability mass up the taxonomy; return the deepest rank whose best
    lineage clears that rank's threshold. Returns (rank, key, mass, tax) or None."""
    taxa = [(_split_taxon(c), float(s)) for c, s in zip(classes, scores)]
    for rank in reversed(RANK_SEQUENCE):  # species -> class (deepest first)
        groups: dict[tuple, dict] = {}
        for tax, sc in taxa:
            if not tax.get(rank):
                continue
            key = lineage_key(tax, rank)
            g = groups.setdefault(key, {"mass": 0.0, "tax": tax})
            g["mass"] += sc
        if groups:
            best_key, best = max(groups.items(), key=lambda kv: kv[1]["mass"])
            if best["mass"] >= RANK_THRESHOLDS.get(rank, 0.5):
                return rank, best_key, best["mass"], tax_from_key(best_key)
    return None


def parse_prediction(result: dict) -> dict:
    """Turn one SpeciesNet frame result into a rolled-up, frame-level label."""
    pred_label = result.get("prediction", "")
    pred_score = float(result.get("prediction_score", 0) or 0)
    pred_tax = _split_taxon(pred_label)

    detections = result.get("detections", [])
    top_detection = detections[0] if detections else {}
    det_label = top_detection.get("label", "")
    det_conf = top_detection.get("conf", 0)

    if "blank" in pred_label:
        category = "blank"
    elif det_label == "person" or "person" in pred_label:
        category = "person"
    elif det_label == "vehicle" or "vehicle" in pred_label:
        category = "vehicle"
    elif det_label == "animal" or _deepest_rank(pred_tax):
        category = "animal"
    else:
        category = "blank"

    # Collect animal boxes above the record floor, then de-dup overlaps with NMS.
    animal_bboxes = []
    for det in detections:
        if (
            det.get("label") == "animal"
            and det.get("bbox")
            and det.get("conf", 0) >= RECORD_MIN_CONF
        ):
            animal_bboxes.append({"bbox": det["bbox"], "conf": det.get("conf", 0)})
    animal_bboxes = _nms(animal_bboxes, iou_threshold=0.5)

    common_name = None
    species_label = None
    rank = None
    lineage = {r: "" for r in RANK_SEQUENCE}
    confidence = pred_score

    if category == "animal":
        classifications = result.get("classifications", {}) or {}
        classes = classifications.get("classes", []) or []
        scores = classifications.get("scores", []) or []

        pred_rank = _deepest_rank(pred_tax)
        chosen = None

        # Trust SpeciesNet's own geofenced call when it committed to a real taxon
        if pred_rank in ("species", "genus", "family") and pred_score >= SPECIES_TRUST:
            chosen = (pred_rank, lineage_key(pred_tax, pred_rank), pred_score, pred_tax)

        # Otherwise (or to go deeper), roll up the raw classifier mass
        mr = _mass_rollup(classes, scores) if classes else None
        if mr and (chosen is None or
                   RANK_SEQUENCE.index(mr[0]) > RANK_SEQUENCE.index(chosen[0])):
            chosen = mr

        if chosen:
            rank, _key, confidence, tax = chosen
            lineage = {r: tax.get(r, "") for r in RANK_SEQUENCE}
            common_name = common_for(rank, tax)
            species_label = ";".join(v for v in lineage_key(tax, rank) if v)
        else:
            # Couldn't confidently reach even a family — fall back to class generic
            dominant_class = ""
            if classes:
                by_class: dict[str, float] = {}
                for c, s in zip(classes, scores):
                    cl = _split_taxon(c)["class"]
                    if cl:
                        by_class[cl] = by_class.get(cl, 0) + float(s)
                if by_class:
                    dominant_class = max(by_class, key=by_class.get)
            dominant_class = dominant_class or pred_tax.get("class", "")
            if dominant_class:
                rank = "class"
                lineage["class"] = dominant_class
                common_name = CLASS_COMMON.get(dominant_class, "Animal")
                species_label = dominant_class

    return {
        "category": category,
        "label": pred_label,
        "common_name": common_name,
        "species_label": species_label,
        "rank": rank,
        "lineage": lineage,
        "confidence": confidence,
        "prediction_source": result.get("prediction_source", ""),
        "detection_conf": det_conf,
        "bbox": top_detection.get("bbox"),
        "all_animal_bboxes": animal_bboxes,
    }


def _iou(box_a: list, box_b: list) -> float:
    """Compute IoU between two [x, y, w, h] boxes."""
    ax1, ay1 = box_a[0], box_a[1]
    ax2, ay2 = ax1 + box_a[2], ay1 + box_a[3]
    bx1, by1 = box_b[0], box_b[1]
    bx2, by2 = bx1 + box_b[2], by1 + box_b[3]

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = box_a[2] * box_a[3]
    area_b = box_b[2] * box_b[3]
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def _nms(detections: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Non-Maximum Suppression: keep only the highest-confidence non-overlapping boxes."""
    if not detections:
        return []
    dets = sorted(detections, key=lambda d: d["conf"], reverse=True)
    keep = []
    for det in dets:
        if all(_iou(det["bbox"], k["bbox"]) < iou_threshold for k in keep):
            keep.append(det)
    return keep


def extract_common_name(label: str | None) -> str | None:
    if not label:
        return None
    parts = [p.strip() for p in label.split(";") if p.strip()]
    if not parts:
        return None
    name = parts[-1]
    if name == "blank" or len(name) < 2:
        return None
    return " ".join(w.capitalize() for w in name.split())
