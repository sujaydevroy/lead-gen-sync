"""Port of frontend/src/lib/sectorMatching.js: map free-text product lines onto sub-sectors.

A product matches a sub-sector when it equals the sub-sector name (case-insensitive) or contains
one of its keywords as a whole word / phrase. Used to maintain dcp.product_sub_sectors.
"""

from __future__ import annotations

import re
from functools import lru_cache

SUB_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Electrical Switches": ["switch", "switches"],
    "Switchgear": ["switchgear", "ring main unit", "rmu", "breakers & switches"],
    "MCB & MCCB": ["mcb", "mccb", "breaker", "breakers", "circuit breaker"],
    "Distribution Boards": ["distribution board", "distribution boards"],
    "Electrical Panels": ["panel", "panels", "enclosure", "enclosures"],
    "Wires & Cables": ["wire", "wires", "cable", "cables"],
    "Industrial Cables": ["industrial cable", "industrial cables"],
    "House Wires": ["house wire", "house wires"],
    "Transformers": ["transformer", "transformers"],
    "Motors": ["motors", "electric motor"],
    "Generators": ["generator", "generators", "genset"],
    "Electrical Control Equipment": ["control products", "control equipment", "motor starter", "motor starters"],
    "Contactors": ["contactor", "contactors"],
    "Relays": ["relay", "relays"],
    "Capacitors": ["capacitor", "capacitors"],
    "Electrical Accessories": ["din rail", "accessories", "terminal block"],
    "Modular Switches": ["modular switch", "modular switches"],
    "Sockets & Plugs": ["socket", "sockets", "plug", "plugs"],
    "Fans": ["fan", "fans", "ceiling fan"],
    "Exhaust Fans": ["exhaust fan", "exhaust fans"],
    "LED Bulbs": ["led bulb", "led bulbs"],
    "LED Lights": ["led light", "led lights", "led panel"],
    "Commercial Lighting": ["commercial lighting"],
    "Industrial Lighting": ["industrial lighting", "high bay"],
    "Street Lighting": ["street lighting", "street light"],
    "Solar Lighting": ["solar lighting", "solar light"],
    "Batteries": ["battery", "batteries"],
    "Inverters": ["inverter", "inverters"],
    "UPS": ["ups"],
    "Stabilizers": ["stabilizer", "stabilizers", "stabiliser"],
    "Power Quality Equipment": ["power quality", "harmonic filter", "surge protection"],
    "Earthing Products": ["earthing", "grounding"],
    "Lightning Protection": ["lightning protection", "lightning"],
}


@lru_cache(maxsize=512)
def _matcher(sub_sector: str) -> re.Pattern[str]:
    terms = [sub_sector, *SUB_SECTOR_KEYWORDS.get(sub_sector, [])]
    alternatives = "|".join(re.escape(t.lower()) for t in terms)
    return re.compile(rf"(^|[^a-z0-9])({alternatives})($|[^a-z0-9])")


def product_matches_sub_sector(product: str, sub_sector: str) -> bool:
    return bool(product) and _matcher(sub_sector).search(product.lower()) is not None


def matching_sub_sectors(product: str, sub_sectors: list[str]) -> list[str]:
    return [s for s in sub_sectors if product_matches_sub_sector(product, s)]
