"""Entity resolution: group candidates that are the same business and merge them into one Dealer.

Matching keys, strongest first: CIN, GSTIN, PAN (inside a GSTIN: one business, many state registrations),
Udyam no., a register's own licence no. -> phone, email, website domain -> fuzzy name + same PIN code.
Guards:
* two candidates with different CINs / PANs are never merged, whatever else they share;
* a phone / email / domain shared by several different registered businesses (often their accountant's) is not
  used for matching.
Dealer IDs are stable across runs: var/state/identity.json remembers which key got which code (CRW-xxxxxxxx), and
an export of the portal's directory (--existing dealers.json) makes a match reuse the portal's Dealer ID.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from crawler import classify, india
from crawler.models import Candidate, Dealer, SourceRef

FUZZY_NAME_SCORE = 92
KIND_PRIORITY = ["registry", "tax_registry", "commodity_board", "msme_registry", "food_licence", "trade_fair",
                 "open_data", "website", "manual", "paid_api"]  # fmt: skip
CONTACT_FIELDS = ("phone", "email", "contact_person", "website")


def _priority(candidate: Candidate) -> tuple[int, int]:
    kind = KIND_PRIORITY.index(candidate.source.kind) if candidate.source.kind in KIND_PRIORITY else len(KIND_PRIORITY)
    return kind, 1 if candidate.extractor.startswith("ai") else 0


def _contact_priority(candidate: Candidate) -> tuple[int, int]:
    """The business's own website is the freshest place for its phone / email; then the usual order."""
    kind, ai = _priority(candidate)
    return (0 if candidate.source.kind == "website" else 1, kind + ai)


def strong_keys(c: Candidate) -> list[str]:
    keys = []
    if c.cin:
        keys.append(f"cin:{c.cin}")
    if c.gstin:
        keys += [f"gstin:{c.gstin}", f"pan:{india.pan_from_gstin(c.gstin)}"]
    if c.udyam_no:
        keys.append(f"udyam:{c.udyam_no}")
    if c.other_id:
        keys.append(f"id:{c.source.name.lower()}:{c.other_id.upper()}")
    return keys


def weak_keys(c: Candidate) -> list[str]:
    keys = []
    if c.phone:
        keys.append(f"phone:{india.phone_key(c.phone)}")
    if c.email:
        keys.append(f"email:{c.email}")
    domain = india.registrable_domain(c.website)
    if domain and domain not in india.FREE_MAIL_DOMAINS:
        keys.append(f"domain:{domain}")
    return keys


def name_pin_key(c: Candidate) -> str | None:
    name = india.name_key(c.dealer_name)
    return f"namepin:{name}|{c.postal_code}" if name and c.postal_code else None


class _Groups:
    """Union-find over candidate indexes that refuses to join groups with conflicting CIN / PAN."""

    def __init__(self, candidates: list[Candidate]):
        self.parent = list(range(len(candidates)))
        self.ids: list[dict[str, set[str]]] = [
            {
                "cin": {c.cin} if c.cin else set(),
                "pan": {india.pan_from_gstin(c.gstin)} if c.gstin else set(),
            }
            for c in candidates
        ]

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True
        for key in ("cin", "pan"):
            if self.ids[ra][key] and self.ids[rb][key] and not self.ids[ra][key] & self.ids[rb][key]:
                return False
        self.parent[rb] = ra
        for key in ("cin", "pan"):
            self.ids[ra][key] |= self.ids[rb][key]
        return True


def group(candidates: list[Candidate]) -> list[list[Candidate]]:
    groups = _Groups(candidates)
    by_key: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        for key in strong_keys(candidate):
            by_key[key].append(index)
    for indexes in by_key.values():
        for other in indexes[1:]:
            groups.union(indexes[0], other)

    # Weak keys: skip a value shared by several different registered businesses.
    weak: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        for key in weak_keys(candidate):
            weak[key].append(index)
    for indexes in weak.values():
        registered = {groups.find(i) for i in indexes if candidates[i].cin or candidates[i].gstin}
        if len(registered) > 1:
            continue
        for other in indexes[1:]:
            groups.union(indexes[0], other)

    # Fuzzy name within the same PIN code.
    by_pin: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        if candidate.postal_code:
            by_pin[candidate.postal_code].append(index)
    for indexes in by_pin.values():
        for pos, a in enumerate(indexes):
            name_a = india.name_key(candidates[a].dealer_name)
            for b in indexes[pos + 1 :]:
                if groups.find(a) == groups.find(b):
                    continue
                name_b = india.name_key(candidates[b].dealer_name)
                if name_a and name_b and fuzz.token_set_ratio(name_a, name_b) >= FUZZY_NAME_SCORE:
                    groups.union(a, b)

    clusters: dict[int, list[Candidate]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        clusters[groups.find(index)].append(candidate)
    return list(clusters.values())


class IdentityMap:
    """Matching key -> Dealer ID, kept between runs so a dealer keeps its code when new sources add keys."""

    def __init__(self, path: Path, existing: Iterable[dict[str, Any]] = ()):
        self.path = path
        self.keys: dict[str, str] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.portal: dict[str, str] = {}
        for row in existing:
            code = row.get("dealer_id")
            if not code:
                continue
            for key in _portal_keys(row):
                self.portal.setdefault(key, code)

    def code_for(self, strong: list[str], weak: list[str], used: set[str]) -> str:
        """Registration keys decide first (portal, then earlier runs); phone / email / name only when they don't.

        A code already given to another dealer in this run is never reused: two businesses that share an
        accountant's e-mail must not end up with one Dealer ID.
        """
        for keys in (strong, weak):
            for table in (self.portal, self.keys):
                for key in keys:
                    code = table.get(key)
                    if code and code not in used:
                        return code
        basis = (strong or weak or ["unknown"])[0]
        length = 8
        taken = set(self.keys.values()) | used
        while True:
            code = "CRW-" + hashlib.sha1(basis.encode()).hexdigest()[:length].upper()
            if code not in taken:
                return code
            length += 2

    def remember(self, keys: list[str], code: str) -> None:
        for key in keys:
            self.keys.setdefault(key, code)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.keys, indent=0, sort_keys=True), encoding="utf-8")


def _portal_keys(row: dict[str, Any]) -> list[str]:
    """Keys of a dealer exported from the portal (dealers.json shape)."""
    keys = []
    registration = row.get("registration_no")
    gst = india.gstin(registration)
    cin_info = india.cin(registration)
    if gst:
        keys += [f"gstin:{gst}", f"pan:{india.pan_from_gstin(gst)}"]
    if cin_info:
        keys.append(f"cin:{cin_info.cin}")
    phone = india.phone(row.get("phone"))
    if phone:
        keys.append(f"phone:{india.phone_key(phone)}")
    email = india.email(row.get("email"))
    if email:
        keys.append(f"email:{email}")
    pin = india.pin_code(row.get("postal_code")) or india.pin_code(row.get("full_address"))
    name = india.name_key(row.get("dealer_name"))
    if name and pin:
        keys.append(f"namepin:{name}|{pin}")
    return keys


def _first(cands: list[Candidate], field: str) -> Any:
    return next((getattr(c, field) for c in cands if getattr(c, field)), None)


def merge(
    cluster: list[Candidate], identities: IdentityMap, sector_file: Path, used: set[str], code: str | None = None
) -> Dealer:
    """One Dealer from a cluster. `used` collects the codes given out in this run; pass `code` to keep a code."""
    ordered = sorted(cluster, key=_priority)
    contacts = sorted(cluster, key=_contact_priority)
    strong = list(dict.fromkeys(k for c in ordered for k in strong_keys(c)))
    weak = list(dict.fromkeys(k for c in ordered for k in weak_keys(c)))
    weak += [k for k in dict.fromkeys(name_pin_key(c) for c in ordered) if k]
    code = code or identities.code_for(strong, weak, used)
    used.add(code)
    identities.remember(strong + weak, code)

    registry = next((c for c in ordered if c.source.kind == "registry"), None)
    # Display name: a trade name from another register / list beats the MCA legal name; a website's own wording last.
    display = next((c for c in ordered if c.source.kind not in ("registry", "website")), registry or ordered[0])
    name = display.dealer_name
    legal = _first(ordered, "legal_name") or (registry.dealer_name if registry and registry.dealer_name != name else None)

    products = list(dict.fromkeys(p for c in ordered for p in c.products))
    state = _first(ordered, "state")
    sources: dict[str, SourceRef] = {}
    for c in ordered:
        known = sources.get(c.source.url)
        if known is None:
            sources[c.source.url] = c.source.model_copy()
        else:  # the same page seen again: widen the dates, keep the first evidence
            known.first_seen = min(filter(None, [known.first_seen, c.source.first_seen]), default=None)
            known.last_seen = max(filter(None, [known.last_seen, c.source.last_seen]), default=None)

    return Dealer(
        dealer_code=code,
        dealer_name=name,
        legal_name=legal if legal != name else None,
        dealer_type=_first(ordered, "dealer_type") or "Distributor",
        contact_person=_first(contacts, "contact_person"),
        email=_first(contacts, "email"),
        phone=_first(contacts, "phone"),
        website=_first(contacts, "website"),
        registration_no=_first(ordered, "gstin")
        or _first(ordered, "cin")
        or _first(ordered, "udyam_no")
        or _first(ordered, "other_id"),
        full_address=_first(ordered, "full_address"),
        city=_first(ordered, "city"),
        state=state,
        postal_code=_first(ordered, "postal_code"),
        country="India",
        region=india.region_for(state),
        sector=classify.sector_for(products, sector_file, default=classify.TOBACCO_SECTOR if products else None),
        products=products,
        sources=list(sources.values()),
        candidate_count=len(cluster),
    )
