"""
plate_ocr.py - Plate text assembly & validation for the OCR pipeline.

Pure post-processing: it never touches the YOLO model or the EasyOCR reader,
so detection/recognition accuracy is unchanged. It only fixes the step that
turns EasyOCR's raw text boxes into a plate string:

  1. EasyOCR splits a plate into several boxes ("MH12" + "AB1234", or even
     "MH","12","AB","1234").  Matching each box on its own can never succeed,
     so boxes are ordered (top row first, then left to right) and contiguous
     runs are joined before matching.
  2. OCR confuses characters that look alike (I/1, O/0, B/8, S/5 ...).  Each
     candidate is fitted against the known Indian plate layouts and only
     characters in the wrong class are corrected - a letter slot may take a
     digit-lookalike and vice versa.  Corrections are capped and penalised in
     the score, so a clean read always beats a repaired one.
"""

import re

# ── Plate layouts: L = letter, D = digit ─────────────────────────
# Ordered list; every layout is tried and the best-scoring fit wins.
STRUCTURES = [
    "LLDDLLDDDD",    # MH12AB1234  - standard
    "LLDDLDDDD",     # MH12A1234   - single-letter series
    "LLDDLLLDDDD",   # MH12ABC1234 - three-letter series
    "LLDLLDDDD",     # DL1AB1234   - single-digit RTO
    "LLDLLLDDDD",    # DL1CAB5678  - single-digit RTO, 3-letter series
    "LLDLDDDD",      # DL1A1234
    "DDLLDDDDLL",    # 22BH1234AA  - Bharat series
    "DDLLDDDDL",     # 22BH1234A   - Bharat series
]

# Character confusions, applied only when a slot demands the other class.
DIGIT_FOR_LETTER = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                    "J": "1", "Z": "2", "A": "4", "S": "5", "G": "6",
                    "T": "7", "B": "8"}
LETTER_FOR_DIGIT = {"0": "O", "1": "I", "2": "Z", "4": "A", "5": "S",
                    "6": "G", "7": "T", "8": "B"}

MAX_FIXES   = 2        # most character repairs allowed in one plate
FIX_PENALTY = 20       # score cost per repair - a clean read always wins
MAX_JOIN  = 4          # most OCR boxes joined into one candidate

# Noise EasyOCR reliably picks up from the plate itself.
NOISE_TOKENS = {"IND", "INDIA", "IN"}


def clean(text):
    """Uppercase and strip everything that cannot be part of a plate."""
    return re.sub(r"[^A-Z0-9]", "", str(text).upper())


def _fit(window, structure):
    """
    Try to read `window` as `structure`.
    Returns (plate, fixes) or None if a character cannot be coerced.
    """
    out, fixes = [], 0
    for ch, slot in zip(window, structure):
        if slot == "L":
            if ch.isalpha():
                out.append(ch)
            elif ch in LETTER_FOR_DIGIT:
                out.append(LETTER_FOR_DIGIT[ch]); fixes += 1
            else:
                return None
        else:
            if ch.isdigit():
                out.append(ch)
            elif ch in DIGIT_FOR_LETTER:
                out.append(DIGIT_FOR_LETTER[ch]); fixes += 1
            else:
                return None
        if fixes > MAX_FIXES:
            return None
    return "".join(out), fixes


def match_plate(text):
    """
    Find the best plate inside `text` (already cleaned or not).
    Returns (plate, score) or (None, 0). Higher score = more trustworthy.
    """
    s = clean(text)
    best, best_score = None, 0

    for structure in STRUCTURES:
        n = len(structure)
        if len(s) < n:
            continue
        bharat = structure.startswith("DDLL")
        for off in range(len(s) - n + 1):
            fit = _fit(s[off:off + n], structure)
            if fit is None:
                continue
            plate, fixes = fit
            # Bharat series must literally carry the BH marker.
            if bharat and plate[2:4] != "BH":
                continue
            # Prefer a reading that consumes the whole string: a shifted
            # sub-window must not outrank the full plate. Capped so a merged
            # "IND"/state-name prefix in one OCR box can still be skipped.
            leftover = len(s) - n
            score = 10 * n - FIX_PENALTY * fixes - min(25 * leftover, 60)
            if score > best_score:
                best, best_score = plate, score

    return best, best_score


def _ordered_tokens(ocr_results, min_conf):
    """
    Sort EasyOCR boxes into reading order (top row first, then left to right)
    and drop low-confidence / noise reads.
    `ocr_results` is EasyOCR's detail=1 output: (bbox, text, confidence).
    """
    items = []
    for r in ocr_results:
        try:
            bbox, text, conf = r[0], r[1], float(r[2])
        except (IndexError, TypeError, ValueError):
            continue
        if conf < min_conf:
            continue
        token = clean(text)
        if not token or token in NOISE_TOKENS:
            continue
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        items.append({
            "text": token,
            "conf": conf,
            "cy": sum(ys) / len(ys),
            "cx": sum(xs) / len(xs),
            "h":  max(ys) - min(ys),
        })

    if not items:
        return []

    # Group into rows: boxes whose centres sit within ~60% of a box height.
    band = max(1.0, sum(i["h"] for i in items) / len(items) * 0.6)
    items.sort(key=lambda i: (round(i["cy"] / band), i["cx"]))
    return items


def extract_plates(ocr_results, min_conf=0.15):
    """
    Turn one crop's EasyOCR output into ranked plate candidates.

    Returns a list of {"plate", "score", "conf", "source"} sorted best first.
    Single boxes are tried first, then joins of up to MAX_JOIN adjacent boxes,
    which is what recovers two-line plates.
    """
    tokens = _ordered_tokens(ocr_results, min_conf)
    if not tokens:
        return []

    found = {}
    for start in range(len(tokens)):
        for span in range(1, MAX_JOIN + 1):
            group = tokens[start:start + span]
            if len(group) < span:
                break
            joined = "".join(t["text"] for t in group)
            if len(joined) > 20:
                break
            plate, score = match_plate(joined)
            if not plate:
                continue
            conf = sum(t["conf"] for t in group) / len(group)
            # Joining boxes is slightly less certain than a single clean read.
            total = score + 20 * conf - 2 * (span - 1)
            prev = found.get(plate)
            if prev is None or total > prev["score"]:
                found[plate] = {
                    "plate":  plate,
                    "score":  total,
                    "conf":   conf,
                    "source": " + ".join(t["text"] for t in group),
                }

    return sorted(found.values(), key=lambda c: c["score"], reverse=True)


def is_plate(text):
    """True when `text` is already a well-formed plate (no repairs needed)."""
    s = clean(text)
    for structure in STRUCTURES:
        if len(s) != len(structure):
            continue
        fit = _fit(s, structure)
        if fit and fit[1] == 0:
            return True
    return False
