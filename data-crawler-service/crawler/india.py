"""India-specific normalisation: states, regions, PIN codes, GSTIN, CIN, Udyam numbers, phones, emails, names.

All functions are pure (no network) and return None for values they can't make sense of, so one bad cell never
stops a run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import phonenumbers

# (canonical name, GST state code, region, extra spellings). Regions follow DESIGN.md §5.1 (zonal councils, with
# UP / Uttarakhand in North like the existing data, and the sixth India region "North East").
_STATES: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("Jammu & Kashmir", "01", "North", ("jammu and kashmir", "j&k", "jk")),
    ("Himachal Pradesh", "02", "North", ("hp",)),
    ("Punjab", "03", "North", ("pb",)),
    ("Chandigarh", "04", "North", ("ch",)),
    ("Uttarakhand", "05", "North", ("uttaranchal", "uk", "ut")),
    ("Haryana", "06", "North", ("hr",)),
    ("Delhi", "07", "North", ("new delhi", "nct of delhi", "national capital territory of delhi", "dl")),
    ("Rajasthan", "08", "North", ("rj",)),
    ("Uttar Pradesh", "09", "North", ("up",)),
    ("Bihar", "10", "East", ("br",)),
    ("Sikkim", "11", "North East", ("sk",)),
    ("Arunachal Pradesh", "12", "North East", ("ar",)),
    ("Nagaland", "13", "North East", ("nl",)),
    ("Manipur", "14", "North East", ("mn",)),
    ("Mizoram", "15", "North East", ("mz",)),
    ("Tripura", "16", "North East", ("tr",)),
    ("Meghalaya", "17", "North East", ("ml",)),
    ("Assam", "18", "North East", ("as",)),
    ("West Bengal", "19", "East", ("wb",)),
    ("Jharkhand", "20", "East", ("jh",)),
    ("Odisha", "21", "East", ("orissa", "or", "od")),
    ("Chhattisgarh", "22", "Central", ("chattisgarh", "ct", "cg")),
    ("Madhya Pradesh", "23", "Central", ("mp",)),
    ("Gujarat", "24", "West", ("gj",)),
    (
        "Dadra & Nagar Haveli and Daman & Diu",
        "26",
        "West",
        (
            "dadra and nagar haveli and daman and diu",
            "dadra and nagar haveli",
            "dadra & nagar haveli",
            "daman and diu",
            "daman & diu",
            "dn",
            "dd",
        ),
    ),  # fmt: skip
    ("Maharashtra", "27", "West", ("mh",)),
    ("Karnataka", "29", "South", ("ka",)),
    ("Goa", "30", "West", ("ga",)),
    ("Lakshadweep", "31", "South", ("ld",)),
    ("Kerala", "32", "South", ("kl",)),
    ("Tamil Nadu", "33", "South", ("tamilnadu", "tn")),
    ("Puducherry", "34", "South", ("pondicherry", "py")),
    ("Andaman & Nicobar Islands", "35", "South", ("andaman and nicobar islands", "andaman and nicobar", "an")),
    ("Telangana", "36", "South", ("tg", "ts")),
    ("Andhra Pradesh", "37", "South", ("ap",)),
    ("Ladakh", "38", "North", ("la",)),
]
# 25 (Daman & Diu) and 28 (undivided Andhra Pradesh) are older codes still found on registrations.
GST_STATE_CODES = {code: name for name, code, _, _ in _STATES} | {
    "25": "Dadra & Nagar Haveli and Daman & Diu",
    "28": "Andhra Pradesh",
}
REGION_BY_STATE = {name: region for name, _, region, _ in _STATES}
_STATE_LOOKUP: dict[str, str] = {}
for _name, _code, _region, _aliases in _STATES:
    _STATE_LOOKUP[_name.lower()] = _name
    for _alias in _aliases:
        _STATE_LOOKUP[_alias] = _name
# Two-letter codes are only trusted where a code is expected (CIN, short state columns), not inside free text.
_TWO_LETTER = {k for k in _STATE_LOOKUP if len(k) == 2}
_FULL_NAMES = sorted((k for k in _STATE_LOOKUP if len(k) > 2), key=len, reverse=True)

# First digit of a PIN code -> postal zone states (used to sanity-check, never to overwrite a stated state).
PIN_ZONES = {
    "1": {"Delhi", "Haryana", "Punjab", "Himachal Pradesh", "Jammu & Kashmir", "Ladakh", "Chandigarh"},
    "2": {"Uttar Pradesh", "Uttarakhand"},
    "3": {"Rajasthan", "Gujarat", "Dadra & Nagar Haveli and Daman & Diu"},
    "4": {"Maharashtra", "Goa", "Madhya Pradesh", "Chhattisgarh"},
    "5": {"Andhra Pradesh", "Telangana", "Karnataka"},
    "6": {"Tamil Nadu", "Kerala", "Puducherry", "Lakshadweep"},
    "7": {"West Bengal", "Odisha", "Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Tripura",
          "Sikkim", "Andaman & Nicobar Islands"},
    "8": {"Bihar", "Jharkhand"},
}  # fmt: skip

FREE_MAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "yahoo.in", "rediffmail.com", "rediff.com", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "aol.com", "protonmail.com", "proton.me", "zoho.com", "zohomail.in", "ymail.com",
    "msn.com", "indiatimes.com", "sify.com", "vsnl.com", "vsnl.net", "bsnl.in",
}  # fmt: skip
_SECOND_LEVEL = {"co.in", "org.in", "net.in", "firm.in", "gen.in", "ind.in", "gov.in", "nic.in", "ac.in", "co.uk"}

_GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CIN_RE = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")
_UDYAM_RE = re.compile(r"^UDYAM-([A-Z]{2})-(\d{2})-(\d{7})$")
_PIN_RE = re.compile(r"(?<!\d)([1-9]\d{2})\s?(\d{3})(?!\d)")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_LEGAL_SUFFIXES = re.compile(
    r"\b(private|pvt|limited|ltd|llp|co|company|corporation|corp|inc|india|the|m/s|ms)\b\.?", re.IGNORECASE
)


def clean_text(value: object) -> str | None:
    """Trimmed text with single spaces; None for empty / placeholder values."""
    if value is None:
        return None
    text = " ".join(str(value).replace(" ", " ").split())
    return None if text.lower() in {"", "-", "--", "na", "n/a", "nil", "null", "none", "not available"} else text


def state_name(value: object, *, allow_codes: bool = False) -> str | None:
    """Canonical Indian state / UT name from a name, spelling variant or (if allow_codes) a 2-letter code."""
    text = clean_text(value)
    if not text:
        return None
    key = re.sub(r"\s+", " ", text.lower().replace(".", "")).strip()
    if key in _TWO_LETTER and not allow_codes:
        return None
    return _STATE_LOOKUP.get(key)


def state_in_text(text: str | None) -> str | None:
    """The last full state name mentioned in an address ("..., Agra 282004, Uttar Pradesh" -> Uttar Pradesh)."""
    if not text:
        return None
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for name in _FULL_NAMES:
        for match in re.finditer(rf"(?<![a-z]){re.escape(name)}(?![a-z])", lowered):
            if best is None or match.start() > best[0]:
                best = (match.start(), _STATE_LOOKUP[name])
    return best[1] if best else None


def region_for(state: str | None) -> str | None:
    return REGION_BY_STATE.get(state) if state else None


def pin_code(value: object) -> str | None:
    """6-digit PIN from a PIN cell or the last PIN-looking number in an address."""
    text = clean_text(value)
    if not text:
        return None
    matches = _PIN_RE.findall(text)
    return "".join(matches[-1]) if matches else None


def pin_matches_state(pin: str | None, state: str | None) -> bool:
    """False only when both are known and the PIN's postal zone doesn't include the state."""
    if not pin or not state or pin[0] not in PIN_ZONES:
        return True
    return state in PIN_ZONES[pin[0]]


def gstin_check_char(first14: str) -> str:
    total = 0
    for index, char in enumerate(first14):
        product = _GSTIN_ALPHABET.index(char) * (1 if index % 2 == 0 else 2)
        total += product // 36 + product % 36
    return _GSTIN_ALPHABET[(36 - total % 36) % 36]


def gstin(value: object) -> str | None:
    """Valid GSTIN (format + state code + checksum), upper-cased; else None."""
    text = clean_text(value)
    if not text:
        return None
    code = re.sub(r"[\s-]", "", text.upper())
    if not _GSTIN_RE.match(code) or code[:2] not in GST_STATE_CODES:
        return None
    return code if gstin_check_char(code[:14]) == code[14] else None


def pan_from_gstin(code: str | None) -> str | None:
    """PAN embedded in a GSTIN: links one business's registrations across states."""
    return code[2:12] if code else None


def gstin_state(code: str | None) -> str | None:
    return GST_STATE_CODES.get(code[:2]) if code else None


@dataclass(frozen=True)
class CinInfo:
    cin: str
    listed: bool
    nic_code: str  # industry code embedded at incorporation (NIC 2008, or NIC 2004 / 1998 for older companies)
    state: str | None
    year: int
    company_type: str  # PLC public, PTC private, OPC one person, GOI / SGC government, FLC / FTC foreign, NPL ...


def cin(value: object) -> CinInfo | None:
    text = clean_text(value)
    if not text:
        return None
    match = _CIN_RE.match(text.upper().replace(" ", ""))
    if not match:
        return None
    listed, nic, state_code, year, company_type, _ = match.groups()
    return CinInfo(
        cin=match.group(0),
        listed=listed == "L",
        nic_code=nic,
        state=state_name(state_code, allow_codes=True) or _CIN_STATE_EXTRA.get(state_code),
        year=int(year),
        company_type=company_type,
    )


# CIN state codes that differ from the 2-letter aliases above.
_CIN_STATE_EXTRA = {"UR": "Uttarakhand", "OR": "Odisha", "CT": "Chhattisgarh", "PY": "Puducherry", "TG": "Telangana"}


def udyam_no(value: object) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    code = re.sub(r"\s", "", text.upper())
    return code if _UDYAM_RE.match(code) else None


def phone(value: object) -> str | None:
    """Indian (or explicitly international) number in international format, e.g. "+91 98371 41116"."""
    text = clean_text(value)
    if not text:
        return None
    for chunk in re.split(r"[,;/]|\bor\b", text):
        chunk = chunk.strip()
        if len(re.sub(r"\D", "", chunk)) < 8:
            continue
        try:
            number = phonenumbers.parse(chunk, "IN")
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(number):
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    return None


def phone_key(formatted: str | None) -> str | None:
    """Digits-only key for matching ("+91 98371 41116" -> "+919837141116")."""
    return "+" + re.sub(r"\D", "", formatted) if formatted else None


def email(value: object) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    for chunk in re.split(r"[,;\s/]+", text):
        candidate = chunk.strip().strip(".<>()[]").lower()
        if _EMAIL_RE.match(candidate) and ".." not in candidate:
            return candidate
    return None


def registrable_domain(host_or_url: str | None) -> str | None:
    """example.co.in from https://www.shop.example.co.in/contact."""
    if not host_or_url:
        return None
    host = re.sub(r"^[a-z]+://", "", host_or_url.strip().lower()).split("/")[0].split(":")[0].split("@")[-1]
    labels = [label for label in host.split(".") if label]
    if len(labels) < 2:
        return None
    keep = 3 if ".".join(labels[-2:]) in _SECOND_LEVEL and len(labels) >= 3 else 2
    return ".".join(labels[-keep:])


def website(value: object) -> str | None:
    text = clean_text(value)
    if not text or " " in text or "." not in text or "@" in text:
        return None
    url = text if re.match(r"^https?://", text, re.I) else f"https://{text}"
    return url.rstrip("/")


def website_from_email(address: str | None) -> str | None:
    """A company mail domain often is its website (sales@kaveri.co.in -> https://kaveri.co.in); free mail is not."""
    if not address or "@" not in address:
        return None
    domain = address.split("@", 1)[1]
    return None if domain in FREE_MAIL_DOMAINS else f"https://{domain}"


def dealer_name(value: object) -> str | None:
    """Display name: whitespace cleaned, leading "M/s" removed, ALL-CAPS kept as the source wrote it."""
    text = clean_text(value)
    if not text:
        return None
    text = re.sub(r"^(m/s\.?|messrs\.?)\s+", "", text, flags=re.IGNORECASE)
    return text.strip(" ,.-") or None


def name_key(value: str | None) -> str:
    """Name for fuzzy matching: lower case, no legal suffixes or punctuation."""
    if not value:
        return ""
    text = _LEGAL_SUFFIXES.sub(" ", value.lower().replace("&", " and "))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())
