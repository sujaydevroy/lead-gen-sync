# Dealer data sourcing — design plan (data-crawler-service)

_Status: updated 2026-10-08 with the user's decisions (§2). **Initial target: India, tobacco.**
Schema changes (§5) are written as migration 0006. Phase 0 crawler code is in `crawler/` (see README.md):
file-based storage (snapshots + identity map in `var/`); the `crawl` staging schema of §7 comes with Phase 1._

## 1. What we need (the target format)

Our clients are **manufacturers looking for buyers**: distributors, wholesalers, C&F agents / super
stockists and large retailers who will purchase from them. A "dealer" is any trade party in the channel,
not only an OEM's authorised partner. First industry: **tobacco** (sector `Tobacco & Related Products`:
Cigarettes, Cigars, Tobacco, Bidi, Pan Masala, Chewing Tobacco, Mouth Fresheners, Tobacco Retail
Accessories). First country: **India**.

The crawler produces records that the **existing admin Dealer Upload** accepts
(`backend/app/services/dealer_import_service.py`):

```
dcp.dealers ──< dcp.dealer_products >── dcp.products ──< dcp.product_sub_sectors >── dcp.sub_sectors >── dcp.sectors
     │ country_id → dcp.countries      region_id → dcp.regions (per country after migration 0006, §5)
     │ dealer_type_id → dcp.dealer_types      dealer_status_id → dcp.dealer_statuses
     └──< dcp.dealer_sources (new, §5)
```

One output record = one row of `dealers.json` (same snake_case keys):

| Field | Required | India source | How |
|---|---|---|---|
| `dealer_id` | no | — | Empty for new dealers (upload assigns `DLR-xxxx`); set when matched to an existing dealer |
| `dealer_name` | **yes** | MCA / Udyam / Tobacco Board / listing | crawl |
| `company_name` (legal name) | no | MCA master data, GST verification | crawl + verify |
| `dealer_type` | **yes** | NIC activity code (manufacture / wholesale / retail), Udyam activity, source wording | rule, AI fallback |
| `status` | yes | `Active` if confirmed by ≥2 independent sources, else `Pending` | rule (§6) |
| `contact_person` | no | Dealer website, paid MCA data (directors) | enrich |
| `email`, `phone`, `website` | no | Dealer website, email finder, listings | enrich |
| `registration_no` | no | **GSTIN** (preferred) or **CIN** (companies) or Udyam no. | crawl + verify |
| `full_address`, `city`, `state`, `postal_code` | no | MCA registered office / Udyam address / GST principal place | crawl + parse |
| `country` | **yes** | `India` | fixed |
| `region` | no | **Derived** from state (zonal map, §5.1) | rule |
| `sector` | no | **Derived**: majority sector of its products | rule |
| `product` | no | NIC sub-class (bidi, cigarettes, pan masala…), website, FSSAI category | rule + AI |
| `source_url`, `verification_date` | no | Primary source + last confirmation; all sources → `dealer_sources` | always |
| `last_transaction_*`, `currency` | no | **Never crawled** (client-private) | — |
| `is_demo` | no | `false` | fixed |

Product names are **canonicalised before upload** (alias table) — the upload creates any unknown
product, and the seed data already has duplicates (`Ring main unit (RMU)` vs `Ring Main Unit`).

## 2. Decisions (2026-10-08)

| # | Question | Decision | Consequence |
|---|---|---|---|
| 1 | Regions outside India | Each country has its own regions: `country_id` on `dcp.regions` | Migration 0006 (§5.1). For India: the zonal map |
| 2 | Dealer sector | Majority sector of its products | Classify rule |
| 3 | First target | **India, tobacco**; dealers = manufacturers, distributors, wholesalers, large retailers | Dealer types (§3), India sources (§4) |
| 4 | Unknown country / sector / region / type | Add the value | Upload "create missing lookups" (§5.3) |
| 5 | Review | Confirmed by several sources → straight to `Active`; else `Pending` | §6 step 7 |
| 6 | Sources per dealer | New `dcp.dealer_sources` table | §5.2 |
| 7 | Paid lookups | Budget exists, amount open | §9 (India prices) |
| 8 | India regions | **Add North East** as the sixth India region | Done in migration 0006 |
| 9 | Phase 0 states | **UP, Andhra Pradesh, West Bengal, Gujarat, Karnataka** | §10 |
| 10 | Exporters / foreign buyers | **In scope — free sources + AI only for now** (no customs-data subscription) | I3 Tobacco Board, I6 websites, trade-fair pages; I9 deferred |

## 3. Dealer types for the Indian tobacco channel

Indian FMCG / tobacco moves **manufacturer → C&F agent / super stockist → distributor → wholesaler →
retailer**. For a manufacturer client, the buyers worth targeting are the first three tiers below.

| Type | India meaning | How we recognise it | Status in `dcp.dealer_types` |
|---|---|---|---|
| **Distributor** | Distributor, C&F agent, super stockist (territory buyer from manufacturers) | Source wording; GST trade name; NIC 46307 + scale | exists |
| **Wholesaler** | Bulk trader selling to retailers (e.g. mandi / market wholesalers) | NIC 46307 ("wholesale of manufactured tobacco & tobacco products"); Udyam "Trading" | **new** |
| **Retailer** | Only large ones: chains, modern trade, airport / duty-free | NIC retail of tobacco in specialised stores; size signals | **new** |
| **Manufacturer** | Cigarette / bidi / zarda / pan masala makers, leaf processors and exporters | NIC 1200x sub-classes; Tobacco Board registration | **new** |
| **Exporter / Importer** | Leaf and product exporters (Tobacco Board register); importers | Tobacco Board lists; customs data (paid) | **new** (one value: `Exporter / Importer`) |
| Reseller, Partner, Service Center | Electrical demo data | — | exists |

NIC 2008 codes to filter on (confirm against the official NIC 2008 book before coding):
`1200x` manufacture of tobacco products (sub-classes cover stemming / redrying, bidi, cigars, cigarettes,
snuff, zarda, katha / chewing lime, pan masala, other), `46307` wholesale of manufactured tobacco &
tobacco products, `4723` retail sale of tobacco products in specialised stores.

## 4. India data sources — feasibility

Tobacco makers in India rarely publish distributor lists (COTPA restricts promotion), and the big B2B
directories (IndiaMART, TradeIndia, JustDial) forbid scraping. The workable route is **government open
data for discovery + verification APIs + dealer websites for contacts**.

| # | Source | What it gives | Coverage | Cost | Verdict |
|---|---|---|---|---|---|
| I1 | **MCA Company Master Data** on data.gov.in (state-wise files, Open Government Licence India) | CIN, company name, status, class, paid-up capital, registration date, **principal business activity**, registered office address | Companies only (Pvt Ltd / Ltd / LLP); misses proprietorships and partnerships | **Free** (free data.gov.in API key) | **Phase 0 — primary discovery.** Filter by tobacco activity codes; capital as a size signal |
| I2 | **Udyam (MSME) unit list** on data.gov.in (district-wise; address, PIN, activity, size) | Proprietorships and partnerships too — most distributors / wholesalers are these | Very broad | **Free** (the unit-level resource may need "Request API"; confirm columns include the activity / NIC code) | **Phase 0 — second discovery source** (check access first) |
| I3 | **Tobacco Board of India** (registered growers, dealers, packers, exporters of Virginia tobacco; ~226 leaf exporters and ~557 manufacturer-exporters reported Nov 2024) | Registered traders / exporters with addresses | Leaf trade + exporters | Free from portal; **RTI request (₹10)** if no downloadable list | Phase 0/1 |
| I4 | **GST verification** (by GSTIN) | Legal name, trade name, status (active / cancelled), constitution, principal place of business, nature of business (wholesale / retail / manufacturing…) | Verification only — no search by product | Paid API (§9) | **Use** — the strongest "is this a live business" signal; also gives dealer type hints |
| I5 | **FSSAI FoSCoS FBO search** (pan masala, mouth fresheners are food) | Licence no., kind of business (manufacturer / trader / retailer), address | Per-name / per-district search; no bulk list | Free | Verification for pan masala / mouth-freshener dealers; bulk via State Food Safety Commissionerate or RTI |
| I6 | **Dealer's own website** (from MCA / GST / search) | Email, phone, brands carried, products | Many small Indian traders have no website | Free + AI tokens | Enrichment |
| I7 | Manufacturer pages (ITC, Godfrey Phillips, VST, bidi / pan masala brands) | Mostly "become a distributor" forms | Low | — | Only where a page actually lists distributors |
| I8 | Trade associations (Tobacco Institute of India, bidi federations, FMCG distributor federations, retailer federations) | Member lists | Usually private | — | Manual / partnership outreach, not crawling |
| I9 | **Customs shipment data** (Volza, Seair, etc.) — HS 2401 / 2402 / 2403 | Indian exporters + their foreign buyers, volumes | High for exporters / importers | Paid (§9) | **Deferred** (decision 10: exporters via free sources + AI for now) |
| I10 | OpenStreetMap `shop=tobacco` / Overture / Foursquare open places | Retail points | Sparse for Indian paan shops | Free | Low priority — retailers are tier 3 |
| ✗ | Google Places (terms forbid storing a database), IndiaMART / TradeIndia / JustDial / LinkedIn (terms forbid scraping) | — | — | — | **Excluded** |

**Feasibility verdict for India:** discovery from I1 + I2 (free, official, bulk) → verify with I4 (GST)
and I5 (FSSAI where relevant) → contacts from I6 (website, AI) and an email finder → I3 for exporters.
The weak spot is **contact details**: MCA / Udyam give addresses but rarely email or phone, so contact
enrichment is where the paid budget goes.

## 5. Schema changes (migration 0006 — written)

Files: `database/migrations/0006_regions_per_country_dealer_sources.sql`, Alembic revision
`0006_regions_per_country`, `database/02_schema.sql`, `03_seed.sql` (via `generate_seed.py`), ERD.
Apply with `.venv\Scripts\python -m app.cli setup` from `backend/`.

Follows the repo rules: idempotent SQL in `database/migrations/0006_*.sql`, an Alembic revision,
`database/02_schema.sql` updated, six common columns + `modified_on` trigger, ERD regenerated.

### 5.1 Regions per country (decision 1)
- `dcp.regions` gets `country_id BIGINT NOT NULL REFERENCES dcp.countries(id)`; unique key
  `(country_id, name)` instead of `(name)`.
- Data migration: today's 5 regions become **India's**; for every other (country, region) pair used by
  `dealers`, `companies` or `users`, create that country's own row and repoint. Nothing is deleted.
- Code touched: dealer filters / facets (`dealer_repository.py`), `/lookups/regions`, company / admin
  forms, dealer import (region resolved within the row's country), seed generator.
- **India state → region map** (based on the zonal councils; adds **North East**, which the current
  5 regions don't have — confirm):
  - North: Delhi, Haryana, Punjab, Himachal Pradesh, Jammu & Kashmir, Ladakh, Rajasthan, Chandigarh, Uttarakhand, Uttar Pradesh
  - Central: Madhya Pradesh, Chhattisgarh
  - East: Bihar, Jharkhand, Odisha, West Bengal
  - West: Gujarat, Maharashtra, Goa, Dadra & Nagar Haveli and Daman & Diu
  - South: Andhra Pradesh, Telangana, Karnataka, Kerala, Tamil Nadu, Puducherry, Lakshadweep, Andaman & Nicobar
  - North East: Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Tripura, Sikkim

  (Uttar Pradesh / Uttarakhand sit in the Central Zonal Council officially; the existing seed data
  already treats Agra as North, so the map follows that. Easy to change — it's a data file.)

### 5.2 `dcp.dealer_sources` (decision 6)
| Column | Notes |
|---|---|
| `dealer_id` | FK → `dcp.dealers` |
| `source_url` | page / dataset / API record URL |
| `source_kind` | `registry`, `msme_registry`, `tax_registry`, `food_licence`, `commodity_board`, `website`, `paid_api`, `manual` |
| `source_name` | e.g. `MCA company master (Uttar Pradesh)`, `GST verification`, `Tobacco Board` |
| `external_id` | CIN / GSTIN / Udyam no. / FSSAI licence no. |
| `first_seen_on`, `last_seen_on` | dates |
| `evidence` | `jsonb`: fields this source confirmed (+ snippets for AI-extracted ones) |

Unique `(dealer_id, source_url)`. `dealers.source_url` / `verification_date` stay as the primary
source and latest confirmation, so the API shape doesn't change.

### 5.3 Create missing lookups on upload (decision 4)
- Dealer Upload (always on): unknown country (full name only — a 2–3 letter code that isn't known is still an
  error), region (within the row's country), sector and dealer type are **created**; status and currency stay
  fixed lists.
- The upload result lists every value it created (`createdLookups`, shown on the upload page), so a typo is
  visible. Sub-sectors are never auto-created.
- Crawler files carry a `sources` list per dealer (JSON objects: `url`, `kind`, `name`, `external_id`,
  `evidence`, `first_seen`, `last_seen`); the upload saves them, plus the row's Source URL, to
  `dcp.dealer_sources` (`sourcesSaved` in the result).

## 6. Approach: hybrid (HTTP + AI)

| | HTTP adapters (no AI) | AI (LLM) |
|---|---|---|
| Used for | data.gov.in APIs / CSVs (MCA, Udyam), GST / FSSAI verification, Tobacco Board lists (HTML / PDF tables) | Dealer websites (contacts, brands, products), irregular PDFs, mapping free-text activity → dealer type / products, messy Indian address parsing |
| Why | Exact, free, repeatable | Handles the long tail without a parser per site |
| Guardrail | Fails loudly | Closed vocabularies; each extracted field must quote verbatim evidence or it's dropped; deterministic validators afterwards |

Pipeline: `sources.yaml → 1 Discover → 2 Fetch → 3 Extract → 4 Normalise → 5 Classify → 6 Resolve → 7 Decide → 8 Publish`

1. **Discover** — MCA + Udyam filtered by tobacco activity; Tobacco Board lists.
2. **Fetch** — `httpx`, honest User-Agent with contact email, robots.txt, ≤1 req/s per host, retries;
   raw responses stored (gzip + hash).
3. **Extract** — adapters for structured data; LLM (structured JSON + evidence) for websites / PDFs.
4. **Normalise** — phone → E.164 `+91` (`phonenumbers`), email syntax + MX, **GSTIN checksum + PAN
   embedded in it**, CIN format, 6-digit PIN code → state check, state → region.
5. **Classify** — dealer type from NIC / GST nature of business / Udyam activity (AI only if missing);
   products from NIC sub-class + website → canonical names → sub-sectors; sector = majority sector.
6. **Resolve** — dedupe: GSTIN → PAN (first 10 chars of GSTIN after the state code links a company's
   GSTINs across states) → CIN → phone → email → website domain → fuzzy name + PIN (`rapidfuzz`).
   A match reuses the dealer's `dealer_code`.
7. **Decide** — **`Active`** when ≥2 independent sources agree (e.g. MCA or Udyam + **GST active**),
   name + address match, and a phone or email validates. **`Pending`** otherwise. GST status
   "cancelled" or MCA status "struck off" → `Inactive`.
8. **Publish** — Phase 0/1: `dealers.json`-format file + `dealer_sources` file via Dealer Upload.
   Phase 2: direct admin API call.

Re-verification every 90 days (GST status is the cheap check).

## 7. Crawler internals

Staging schema `crawl` (not the portal schema): `sources`, `runs`, `pages`, `dealer_candidates`
(`jsonb` + evidence + confidence + extractor / prompt version + match keys), `candidate_links`,
`review_decisions`, `product_aliases`, `region_map`, `suppressions` (opt-outs).

Stack (Python, like `backend/`): `httpx`, `selectolax` / `parsel`, `trafilatura`, `pdfplumber`,
`openpyxl`, `pydantic` models mirroring the import `FIELDS` (a test keeps them in sync),
`phonenumbers`, `email-validator`, `pycountry`, `rapidfuzz`; queue = PostgreSQL `FOR UPDATE SKIP
LOCKED`; LLM behind an `Extractor` interface; tests on saved fixtures + throwaway PostgreSQL :55432.

## 8. Compliance (India)

- **DPDP Act 2023 and its Rules**: named contacts and personal mobiles / mailboxes of proprietors are
  personal data. Keep source + date per field (`dealer_sources.evidence`), prefer business contacts,
  keep a suppression list, honour removal requests, and give a notice at first contact.
- **COTPA 2003**: bans tobacco advertising / promotion to the public; B2B trade communication with
  licensed businesses is a different thing, but keep outreach strictly trade-to-trade. **Get a legal
  opinion before Phase 2** — this is not legal advice.
- **TRAI / DND** rules apply to promotional calls and SMS: check DND before phone outreach.
- data.gov.in data is under the Open Government Licence – India (attribution required); respect site
  terms and robots.txt; no CAPTCHA bypassing (GST and MCA portals have CAPTCHAs → use licensed APIs).

## 9. Paid lookups in India — what they cost (estimates, Oct 2026)

From vendor pages and listings found on 2026-10-08; several vendors quote only on request, so **treat
these as planning numbers**. USD at ~₹88.

| Service | What it adds | Price found | Per dealer | Verdict |
|---|---|---|---|---|
| **GST verification API** (e.g. GSTZen) | Live status, legal + trade name, nature of business, address | Annual bundles ≈ **₹3,500 / 5,000 calls, ₹5,000 / 10,000, ₹8,250 / 25,000** (+18% GST); listings show ~₹0.50 / call | **₹0.33–0.70** | **Use** — best value |
| **MCA company data API** (Probe42, CompanyData, Signzy…) | Directors (contact person), company email from filings, status | No public per-call price; one vendor advertises "from $0.02 / credit"; Probe42 "from ₹499" | ~₹2+ (quote needed) | Optional; get 2 quotes |
| **Email finder** (Hunter.io) | Business emails from a website domain | Free 50/mo; Starter $49/mo (2,000 credits); Growth $149/mo (~10,000) — 1 credit per email found | ₹1.3–2.2 | Use only for dealers with a website (many small Indian traders have none) |
| **LLM — Claude Haiku 5.5** ($0.10 / $0.50 per million tokens in / out; Batch API −50%) | Website / PDF extraction, classification | ≈ $0.0011 per page (~6k in + 1k out) | ≈ ₹0.2–0.4 | **Use** |
| **LLM — Claude Sonnet 5.5** ($2 / $10 per million) | Hard pages only (~10%) | ≈ $0.022 per page | small | Use sparingly |
| **Customs data** (Volza / Seair) | Exporters + foreign buyers by HS code | Entry ~$1,500 (monthly vs annual unclear across sources); enterprise far higher | subscription | Only if export buyers matter |
| **RTI requests** (Tobacco Board, State Food Safety) | Official lists not published online | ₹10 per application | — | Use |
| Infrastructure | Small VM / container | ~₹500–1,500 / month | — | Use |

**Starting budget for India (target: 5,000 tobacco dealers):**

| Scenario | First 5,000 dealers | Monthly after (refresh + ~1,000 new) |
|---|---|---|
| **Free sources + AI only** (MCA + Udyam + Tobacco Board, LLM for websites) | ≈ **₹2,000–4,000** | ≈ ₹1,000–2,500 |
| **Recommended starter** (+ GST verification for all, + email finder for dealers with websites) | ≈ **₹18,000–22,000** (GST bundle ₹5,000–6,000 incl. tax, Hunter Growth 1 month ≈ ₹13,000, LLM + VM ≈ ₹2,000–3,000) | ≈ ₹4,000–8,000 |
| **+ MCA API for directors / emails** | + ≈ ₹10,000–20,000 per 5,000 lookups (quote needed) | as used |
| **+ customs export data** | + from ~₹1.3 lakh | subscription |

Rule of thumb: **≈ ₹4 per fully enriched dealer** in the recommended starter (GST ₹0.5 + email ₹2 +
AI ₹0.3 + share of fixed costs), **≈ ₹0.5** with free sources + AI only.

## 10. Phased plan (India)

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Spike (≈1–2 weeks)** | Migration 0006 (regions per country + India map incl. North East, `dealer_sources`, new dealer types, create-missing-lookups). Adapters: MCA master data (2–3 big tobacco states first: UP, Andhra Pradesh, West Bengal, Gujarat, Karnataka — bidi / leaf / pan masala clusters), Udyam access check, Tobacco Board. GST verification on a 200-dealer sample. Publish via Dealer Upload on a **throwaway DB** | ≥95% rows accepted; 50-row manual spot check; measured yield (dealers per state) and GST match rate |
| **1 — MVP** | All states; website discovery + AI contact extraction; FSSAI check for pan masala / mouth fresheners; ≥2-source auto-Active rule; `crawl` staging tables; CLI | Phone / email precision ≥98% (sampled); duplicates <2% |
| **2 — Enrichment** | Email finder, optional MCA API (directors), optional customs data; review page in the admin portal; direct API publish | Legal opinion done; ≥60% of Active dealers with phone or email |
| **3 — Operate** | Scheduled GST re-verification, source health alerts, cost dashboard | Active dealers verified ≤90 days ago |

## 11. Still open

Nothing blocking Phase 0. Revisit paid enrichment (GST API, email finder, MCA API, customs data) after Phase 0
has measured how many dealers the free sources give and how many lack a phone / email.

## Sources (checked 2026-10-08)

- MCA company master data (data.gov.in): https://community.data.gov.in/?p=117928
- Udyam unit lists: https://www.data.gov.in/resource/district-wise-total-msme-registered-enterprises-under-udyam-registration-till-last-date ,
  https://aikosh.indiaai.gov.in/home/datasets/details/list_of_msme_registered_units_under_udyam.html ,
  https://www.udyamregistration.gov.in/docs/Udyam_Metadata.pdf
- NIC 46307: https://worldoftaxonomy.com/codes/nic_2008/46307
- Tobacco Board of India: https://tobaccoboard.commerce.gov.in/ ; counts:
  https://www.newsonair.gov.in/tbi-leads-delegation-of-tobacco-exporters-in-world-tobacco-middle-east-focuses-on-branding-unmanufactured-indian-tobacco
- FSSAI FBO search: https://www.registerkaro.in/post/fssai-fbo-search-how-to-verify-an-fbo-license-ensure-compliance
- GST API pricing: https://gstzen.in/gst-validator-api-pricing-details , https://www.capterra.in/software/1240769/GSTIN-API
- MCA data APIs: https://www.capterra.com/p/236540/Probe42/ , https://companydata.com/mca-api/
- Hunter.io: https://hunter.io/pricing
- Volza: https://dupple.com/reviews/volza , https://comparetiers.com/tools/volza
- Google Places pricing / terms context: https://openplacesapi.com/blog/google-places-api-pricing
