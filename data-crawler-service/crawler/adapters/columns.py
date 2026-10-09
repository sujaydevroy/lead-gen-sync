"""Header spellings per field (compared after lower-casing and removing everything but letters and digits).

Profiles cover the column names of the open datasets; sources.yaml can add spellings with `columns:`.
"""

from __future__ import annotations

from crawler.adapters.base import norm_header

GENERIC: dict[str, tuple[str, ...]] = {
    "dealer_name": ("name", "dealername", "firmname", "nameofthefirm", "nameoffirm", "tradername", "nameofthetrader",
                    "exporter", "nameofexporter", "nameoftheexporter", "company", "companyname", "dealer", "party",
                    "nameofparty", "distributor", "nameofdistributor", "businessname", "tradename", "enterprisename"),
    "legal_name": ("legalname", "legalnameofbusiness", "registeredname"),
    "dealer_type": ("dealertype", "type", "category", "typeofbusiness", "natureofbusiness"),
    "contact_person": ("contactperson", "contactname", "proprietor", "nameofproprietor", "owner", "partner", "director"),
    "email": ("email", "emailid", "emailaddress", "mail", "emailaddr"),
    "phone": ("phone", "phoneno", "phonenumber", "mobile", "mobileno", "mobilenumber", "telephone", "telno", "contactno",
              "contactnumber", "contact"),
    "website": ("website", "web", "url", "websiteurl"),
    "gstin": ("gstin", "gstno", "gstnumber", "gst", "gstinuin"),
    "cin": ("cin", "corporateidentificationnumber", "cinno"),
    "udyam_no": ("udyamno", "udyamnumber", "udyamregistrationnumber", "udyamregistrationno"),
    "other_id": ("registrationno", "registrationnumber", "regno", "licenceno", "licenseno", "licencenumber",
                 "licensenumber", "rcmcno", "certificateno"),
    "full_address": ("address", "fulladdress", "registeredofficeaddress", "officeaddress", "addressofthefirm",
                     "communicationaddress", "postaladdress"),
    "city": ("city", "town", "place", "district", "districtname", "location"),
    "state": ("state", "statename", "registeredstate"),
    "postal_code": ("pin", "pincode", "postalcode", "zip", "zipcode", "pinno"),
    "products": ("products", "product", "productlines", "items", "commodity", "commodities", "itemsdealtin"),
    "nic_code": ("nic", "niccode", "nic2008", "nic2008code", "industrialclass", "nic5digit", "nic5digitcode"),
    "activity": ("activity", "activitydescription", "businessactivity", "principalbusinessactivity",
                 "principalbusinessactivityaspercin", "majoractivity", "nicdescription", "description"),
    "business_status": ("status", "companystatus", "gststatus", "registrationstatus"),
}  # fmt: skip

# MCA company master data (data.gov.in, one resource per state)
MCA: dict[str, tuple[str, ...]] = {
    "dealer_name": ("companyname",),
    "cin": ("corporateidentificationnumber", "cin"),
    "business_status": ("companystatus",),
    "nic_code": ("industrialclass",),
    "activity": ("principalbusinessactivityaspercin", "principalbusinessactivity"),
    "full_address": ("registeredofficeaddress",),
    "state": ("registeredstate",),
    "email": ("emailaddr", "email"),
}

# Udyam (MSME) registered units (data.gov.in, district-wise)
UDYAM: dict[str, tuple[str, ...]] = {
    "dealer_name": ("enterprisename", "nameofenterprise", "unitname", "nameofunit", "name"),
    "udyam_no": ("udyamregistrationnumber", "udyamno", "registrationnumber", "regno"),
    "full_address": ("address", "communicationaddress", "unitaddress", "officialaddress"),
    "city": ("district", "districtname", "city"),
    "state": ("state", "statename"),
    "postal_code": ("pincode", "pin"),
    "nic_code": ("niccode", "nic5digitcode", "nic5digit", "nic"),
    "activity": ("majoractivity", "activity", "nicdescription", "activitydescription"),
}

PROFILES = {"generic": GENERIC, "mca": MCA, "udyam": UDYAM}


def column_map(headers: list[str], profile: str, extra: dict[str, list[str]] | None = None) -> dict[str, int]:
    """field -> column index; profile spellings first, then the generic ones, first matching column wins."""
    spellings: dict[str, list[str]] = {}
    for table in (PROFILES[profile], GENERIC):
        for field, names in table.items():
            spellings.setdefault(field, []).extend(names)
    for field, names in (extra or {}).items():
        spellings.setdefault(field, [])[:0] = [norm_header(n) for n in names]

    normalised = [norm_header(h) for h in headers]
    mapping: dict[str, int] = {}
    used: set[int] = set()
    for field, names in spellings.items():
        for name in names:
            if name in normalised and normalised.index(name) not in used:
                mapping[field] = normalised.index(name)
                used.add(mapping[field])
                break
    return mapping
