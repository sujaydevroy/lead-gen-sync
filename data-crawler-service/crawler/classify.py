"""Dealer type, products and sector from industry codes and activity text (deterministic rules first).

NIC codes (National Industrial Classification) appear in MCA data (and inside every CIN) and in Udyam data.
Older companies carry NIC 2004 / 1998 codes, so both the 2008 codes (12xxx manufacture, 46307 wholesale,
4723x retail) and the older tobacco codes (16xxx) are listed. Sub-class meanings follow the official NIC books;
verify a code there before adding it.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

TOBACCO_SECTOR = "Tobacco & Related Products"

# NIC prefix -> (dealer type, products). Longest prefix wins.
NIC_RULES: dict[str, tuple[str, list[str]]] = {
    # NIC 2008, class 1200 "Manufacture of tobacco products"
    "12001": ("Manufacturer", ["Tobacco"]),  # stemming and redrying of tobacco
    "12002": ("Manufacturer", ["Bidi"]),
    "12003": ("Manufacturer", ["Cigars"]),  # cigars, cheroots, cigarillos
    "12004": ("Manufacturer", ["Cigarettes"]),
    "12005": ("Manufacturer", ["Tobacco"]),  # snuff
    "12006": ("Manufacturer", ["Chewing Tobacco"]),  # zarda
    "12007": ("Manufacturer", ["Chewing Tobacco"]),  # katha, chewing lime
    "12008": ("Manufacturer", ["Pan Masala"]),
    "12009": ("Manufacturer", ["Tobacco"]),  # other tobacco products
    "1200": ("Manufacturer", ["Tobacco"]),
    # NIC 2004 / 1998, group 160 "Manufacture of tobacco products" (same sub-class order as 2008)
    "16001": ("Manufacturer", ["Tobacco"]),
    "16002": ("Manufacturer", ["Bidi"]),
    "16003": ("Manufacturer", ["Cigars"]),
    "16004": ("Manufacturer", ["Cigarettes"]),
    "16005": ("Manufacturer", ["Tobacco"]),
    "16006": ("Manufacturer", ["Chewing Tobacco"]),
    "16007": ("Manufacturer", ["Chewing Tobacco"]),
    "16008": ("Manufacturer", ["Pan Masala"]),
    "16009": ("Manufacturer", ["Tobacco"]),
    "1600": ("Manufacturer", ["Tobacco"]),
    # NIC 2008 trade
    "46307": ("Wholesaler", ["Tobacco"]),  # wholesale of manufactured tobacco & tobacco products
    "4723": ("Retailer", ["Tobacco Retail Accessories"]),  # retail sale of tobacco products in specialised stores
}
TOBACCO_NIC_PREFIXES = tuple(NIC_RULES)

# Activity text -> products (sub-sectors of "Tobacco & Related Products" in sector.json)
PRODUCT_KEYWORDS: list[tuple[str, str]] = [
    (r"\bcigarettes?\b", "Cigarettes"),
    (r"\bcigars?\b|\bcheroots?\b|\bcigarillos?\b", "Cigars"),
    (r"\bb[ie]e?dis?\b|\bbeedi", "Bidi"),
    (r"\bpan\s*masala\b|\bpaan\s*masala\b|\bgutkha\b", "Pan Masala"),
    (r"\bzarda\b|\bkhaini\b|\bchewing\s+tobacco\b|\bkatha\b|\bmawa\b", "Chewing Tobacco"),
    (r"\bmouth\s*fresheners?\b|\bsupari\b|\bmukhwas\b", "Mouth Fresheners"),
    (r"\bhookah\b|\bshisha\b|\brolling\s+papers?\b|\blighters?\b|\bsmokers'? accessories\b", "Tobacco Retail Accessories"),
    (r"\btobacco\b|\bsnuff\b", "Tobacco"),
]
# Activity text -> dealer type, checked in this order (distributor wording beats generic "trading").
TYPE_KEYWORDS: list[tuple[str, str]] = [
    (r"\bexport(er|ers|ing)?\b|\bimport(er|ers|ing)?\b", "Exporter / Importer"),
    (r"\bdistribut(or|ors|ion)\b|\bsuper\s*stockist\b|\bc\s*&\s*f\b|\bcarrying\s+and\s+forwarding\b|\bstockist\b", "Distributor"),
    (r"\bwholesal(e|er|ers)\b|\btrading\b|\btraders?\b", "Wholesaler"),
    (r"\bmanufactur(e|er|ers|ing)\b|\bprocessing\b|\bredrying\b|\bfactory\b", "Manufacturer"),
    (r"\bretail(er|ers)?\b|\bshop\b|\bstores?\b", "Retailer"),
]
DEALER_TYPES = ("Distributor", "Wholesaler", "Retailer", "Manufacturer", "Exporter / Importer")
UDYAM_ACTIVITY_TYPES = {"manufacturing": "Manufacturer", "trading": "Wholesaler"}  # "Services" says nothing


def nic_rule(code: str | None) -> tuple[str, list[str]] | None:
    if not code:
        return None
    digits = re.sub(r"\D", "", code)
    for length in range(len(digits), 3, -1):
        rule = NIC_RULES.get(digits[:length])
        if rule:
            return rule
    return None


def is_tobacco_nic(code: str | None) -> bool:
    return nic_rule(code) is not None


def products_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for pattern, product in PRODUCT_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE) and product not in found:
            found.append(product)
    return found


def type_from_text(text: str | None) -> str | None:
    if not text:
        return None
    for pattern, dealer_type in TYPE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return dealer_type
    return None


def is_tobacco_text(text: str | None) -> bool:
    return bool(products_from_text(text))


@lru_cache(maxsize=4)
def _sector_of_product(sector_file: str) -> dict[str, str]:
    """Product / sub-sector name (lower case) -> sector, from the portal's sector.json."""
    path = Path(sector_file)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for entry in data.get("sectors", []):
        for sub in entry.get("sub_sectors", []):
            mapping.setdefault(sub.lower(), entry["sector"])
    return mapping


def sector_for(products: list[str], sector_file: Path, default: str | None = None) -> str | None:
    """The sector most of the products belong to (decision 2 in DESIGN.md); ties go to the first product's sector.

    A sub-sector name listed under several sectors counts for the first one in sector.json.
    """
    mapping = _sector_of_product(str(sector_file))
    votes: Counter[str] = Counter()
    order: list[str] = []
    for product in products:
        sector = mapping.get(product.lower())
        if sector:
            votes[sector] += 1
            if sector not in order:
                order.append(sector)
    if not votes:
        return default
    best = max(votes.values())
    return next(sector for sector in order if votes[sector] == best)
