"""
Uzbekistan Location and Route Detector.
Analyzes normalized text to extract:
- Mentioned cities/regions/districts
- Destination targets (...ga, ...go, ...ka, ...gacha, v ..., do ...)
- Origin points (...dan, ...don, iz ...)
- Route pairs (Origin -> Destination)
- Dynamic transit offer triggers (Destination + Travel Action)
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Set, Optional

from app.services.locations.registry import (
    UZBEKISTAN_LOCATIONS,
    LOCATION_LOOKUP,
    ALL_LOCATION_STEMS,
    AFFIXES,
)

# Common travel / ride offer verbs and predicates
TRANSIT_ACTION_PATTERNS = [
    r'\b(?:ketami[sz]|borami[sz]|yurami[sz]|qatnaymi[sz]|chiqami[sz]|chiqadi)\b',
    r'\b(?:edem|yedem|viezja[a-z]*|edu|vyiezja[a-z]*)\b',
    r'\b(?:moshin[a-z]?\s*bor|mashin[a-z]?\s*bor|moshinbor|moshinabor|joy\s*bor)\b',
    r'\b(?:\d+\s*(?:ta\s*)?(?:odam|kishi|chel|mesta)\s*(?:kk|kerak|karak|garak|bor))\b',
    r'\b(?:ta[kx]si|taxi)\b',
    r'\b(?:pochta|yuk|odam)\s*(?:olami[sz]|tashish)\b',
    r'\b(?:salon\s*bo\'?sh|zapravkada(?:miz|turibmiz))\b',
    r'\b(?:est\s*mesta|yest\s*mesta|mesta\s*(?:dlya|yest|est)|mesta\s*bor)\b',
    r'\b(?:beru|vozmu|berem)\b(?:\s+(?:\d+|chelovek|chel|passajir|poputchik|odam|kishi))?'
]


@dataclass
class LocationMatch:
    canonical_name: str
    matched_word: str
    role: str  # "destination", "origin", "locative", "general"


@dataclass
class LocationDetectionResult:
    detected_locations: List[str] = field(default_factory=list)
    destinations: List[str] = field(default_factory=list)
    origins: List[str] = field(default_factory=list)
    routes: List[Tuple[str, str]] = field(default_factory=list)
    is_transit_offer: bool = False
    transit_reason: str = ""


def _strip_affix(word: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempt to strip known grammatical affixes from word.
    Returns (stem, affix_type) or (None, None).
    """
    # 1. Destination affixes: -gacha, -kacha, -ga, -go, -ka, -ko, -ge, -a
    for aff in AFFIXES["destination"]:
        if word.endswith(aff) and len(word) > len(aff) + 2:
            stem = word[:-len(aff)]
            if stem in LOCATION_LOOKUP:
                return stem, "destination"

    # 2. Origin affixes: -dan, -don, -din
    for aff in AFFIXES["origin"]:
        if word.endswith(aff) and len(word) > len(aff) + 2:
            stem = word[:-len(aff)]
            if stem in LOCATION_LOOKUP:
                return stem, "origin"

    # 3. Locative affixes: -da, -de
    for aff in AFFIXES["locative"]:
        if word.endswith(aff) and len(word) > len(aff) + 2:
            stem = word[:-len(aff)]
            if stem in LOCATION_LOOKUP:
                return stem, "locative"

    return None, None


def detect_locations(normalized_text: str) -> LocationDetectionResult:
    """
    Scan normalized text for Uzbekistan cities, districts, regions and route semantics.
    """
    if not normalized_text:
        return LocationDetectionResult()

    normalized_text = normalized_text.lower()
    words = normalized_text.split()
    matches: List[LocationMatch] = []
    seen_canon: Set[str] = set()

    for idx, word in enumerate(words):
        clean_word = re.sub(r'[^a-z0-9\']', '', word.lower())
        if not clean_word or len(clean_word) < 3:
            continue

        # Check Russian prepositions: 'v tashkent', 'do tashkenta'
        prev_word = words[idx - 1] if idx > 0 else ""
        is_preposition_dest = prev_word in ("v", "do", "k")
        is_preposition_orig = prev_word in ("iz", "s", "ot")

        # Case A: Exact stem match in lookup
        if clean_word in LOCATION_LOOKUP:
            canon = LOCATION_LOOKUP[clean_word]
            role = "destination" if is_preposition_dest else ("origin" if is_preposition_orig else "general")
            matches.append(LocationMatch(canonical_name=canon, matched_word=clean_word, role=role))
            seen_canon.add(canon)
            continue

        # Case B: Stem with affix (-ga, -dan, -da, -gacha, etc.)
        stem, affix_type = _strip_affix(clean_word)
        if stem and stem in LOCATION_LOOKUP:
            canon = LOCATION_LOOKUP[stem]
            role = "destination" if is_preposition_dest else ("origin" if is_preposition_orig else (affix_type or "general"))
            matches.append(LocationMatch(canonical_name=canon, matched_word=clean_word, role=role))
            seen_canon.add(canon)
            continue

    destinations = [m.canonical_name for m in matches if m.role == "destination"]
    origins = [m.canonical_name for m in matches if m.role == "origin"]
    all_locs = list(seen_canon)

    # Route pairs (Origin -> Destination)
    routes: List[Tuple[str, str]] = []
    if origins and destinations:
        for o in origins:
            for d in destinations:
                if o != d:
                    routes.append((o, d))

    # Check transit offer intent
    is_transit_offer = False
    transit_reason = ""

    has_destination = bool(destinations)
    has_transit_action = any(bool(re.search(pat, normalized_text)) for pat in TRANSIT_ACTION_PATTERNS)

    if has_destination and has_transit_action:
        dest_display = destinations[0].capitalize()
        is_transit_offer = True
        transit_reason = f"Yo'nalish bo'yicha taksi qatnovi taklifi ({dest_display} yo'nalishi)"
    elif routes and has_transit_action:
        r_orig, r_dest = routes[0]
        is_transit_offer = True
        transit_reason = f"Yo'nalish bo'yicha qatnov taklifi ({r_orig.capitalize()} -> {r_dest.capitalize()})"
    elif has_destination and bool(re.search(r'\b(?:\d+\s*(?:ta\s*)?(?:joy|mesta)|salon\s*bo\'?sh|\d+\s*(?:ta\s*)?(?:odam|kishi|chel)\s*(?:kk|kerak|karak|garak|bor|olami[sz]|tashish))\b', normalized_text)):
        dest_display = destinations[0].capitalize()
        is_transit_offer = True
        transit_reason = f"Yo'nalish va bo'sh o'rinlar ({dest_display})"

    # Disqualify if it's a passenger party inquiring/looking for a ride ("4 odammiz", "2 kishimiz")
    is_passenger_party = bool(re.search(r'\b(?:\d+\s*(?:ta\s*)?)?(?:odam|kishi)\s*mi[sz]\b', normalized_text))
    if is_passenger_party:
        is_transit_offer = False
        transit_reason = ""

    return LocationDetectionResult(
        detected_locations=all_locs,
        destinations=destinations,
        origins=origins,
        routes=routes,
        is_transit_offer=is_transit_offer,
        transit_reason=transit_reason,
    )
