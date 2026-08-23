from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

EARTH_RADIUS_M = 6_371_008.8


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def normalize_roadway(value: str | None) -> str | None:
    if not value:
        return None
    s = value.upper().strip()
    s = s.replace("INTERSTATE", "I")
    s = re.sub(r"\bI[\s-]*(\d+)\b", r"I-\1", s)
    s = re.sub(r"\bUS[\s-]*(\d+)\b", r"US-\1", s)
    s = re.sub(r"\bSR[\s-]*(\d+)\b", r"SR-\1", s)
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_direction(value: str | None) -> str | None:
    if not value:
        return None
    token = value.upper().strip()
    aliases = {
        "N": "NB", "NORTH": "NB", "NORTHBOUND": "NB", "NB": "NB",
        "S": "SB", "SOUTH": "SB", "SOUTHBOUND": "SB", "SB": "SB",
        "E": "EB", "EAST": "EB", "EASTBOUND": "EB", "EB": "EB",
        "W": "WB", "WEST": "WB", "WESTBOUND": "WB", "WB": "WB",
    }
    return aliases.get(token, token)


def token_set(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[A-Z0-9]+", text.upper()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.5
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
