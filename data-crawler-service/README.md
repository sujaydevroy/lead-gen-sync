# data-crawler-service

Dealer data crawler for DealerConnect, Phase 0 (India, tobacco). The design and the reasons are in
[`DESIGN.md`](DESIGN.md).

**Hybrid approach.** Structured sources are read directly over HTTP / from files, with no AI: open-data files
(MCA, Udyam), HTML tables and PDF tables. The AI (Claude) is used only where that fails: list pages without a table,
and dealer websites when the plain mailto: / tel: links don't give a phone, an email or products. Every value
the AI returns is checked against the page text, and anything not found on the page is dropped.

```
sources.yaml ─► crawl ─► var/snapshots/<source>.jsonl ─► enrich (websites) ─► publish ─► var/out/dealers_<time>.json
                (adapters: tabular / html / ai_page)                          (merge, Dealer IDs,     + report_<time>.md
                                                                               Active/Pending/Inactive)
```

The output file has the same shape as `dealers.json`, plus a `sources` list per dealer. Upload it in the portal
(**System Administrator → Dealer Upload**). Dealer IDs are stable (`CRW-xxxxxxxx`), so uploading the next run's
file updates the same dealers. Each source is stored in `dcp.dealer_sources`.

## Layout

```
crawler/
  config.py        settings from environment / .env
  fetch.py         polite HTTP: robots.txt, 1 request per host per second, retries, on-disk cache
  india.py         GSTIN (checksum), CIN (industry code inside), Udyam no., phones, PIN, state -> region
  classify.py      NIC codes / activity text -> dealer type, tobacco products; sector = majority of products
  normalize.py     one raw record -> Candidate
  adapters/        tabular.py (data.gov.in API or CSV/XLSX/JSON), html.py (tables first, AI fallback), columns.py
  ai/              text.py (HTML/PDF -> text), extractor.py (schemas + grounding), claude.py (Claude API)
  enrich.py        dealer websites (links first, AI for what is still missing)
  resolve.py       same business in several sources -> one dealer; stable Dealer IDs (var/state/identity.json)
  decide.py        Active / Pending / Inactive with the reason
  pipeline.py      crawl, enrich, publish (+ report)
  cli.py           python -m crawler ...
sources.yaml       the sources (Phase 0: MCA for UP, Andhra Pradesh, West Bengal, Gujarat, Karnataka)
inputs/            files you download for tabular sources (not committed)
var/               cache, snapshots, identity map, outputs (not committed)
tests/             pytest, fictional fixtures, no network
```

## Setup (Windows PowerShell)

Run these in the `data-crawler-service` folder:

```powershell
cd D:\Projects\Personal\lead-gen-sync\data-crawler-service
```

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\python -m pip install -e ".[ai,pdf,dev]"
```

```powershell
copy .env.example .env
```

Then open `.env` in an editor and fill in `CRAWLER_CONTACT_EMAIL`. Add `ANTHROPIC_API_KEY` if you want AI
extraction. Without it the crawler still runs: pages that need AI are skipped and listed.

## Getting the MCA files (Phase 0)

1. Open data.gov.in and search for **"Company Master Data"**. It has one resource per state.
2. Download the CSV for each Phase 0 state into `inputs\mca\`, named as in `sources.yaml`:
   `uttar_pradesh.csv`, `andhra_pradesh.csv`, `west_bengal.csv`, `gujarat.csv`, `karnataka.csv`.
3. Optional, instead of downloading: put the resource id from the dataset page in `datagov_resource:` (and
   remove `file:`), and set `DATA_GOV_IN_API_KEY` in `.env`. The crawler then reads it through the API.

The crawler keeps only tobacco businesses. It checks the NIC industry code (12xxx / 16xxx manufacture, 46307
wholesale, 4723x retail), which is also inside every CIN, and tobacco words in the activity text.

## Running

```powershell
.venv\Scripts\python -m crawler sources
```

```powershell
.venv\Scripts\python -m crawler crawl
```

```powershell
.venv\Scripts\python -m crawler enrich --limit 50
```

```powershell
.venv\Scripts\python -m crawler publish
```

Or all three at once:

```powershell
.venv\Scripts\python -m crawler run --limit 50
```

- `--source mca-uttar-pradesh` crawls one source (you can repeat the flag).
- `--no-ai` never calls the AI.
- `--existing dealers.json` matches against dealers already in the portal and reuses their Dealer IDs.
- `publish` prints the file names. Open `var\out\report_<time>.md` to see the counts and why dealers are Pending.

AI cost guard: at most `CRAWLER_LLM_MAX_CALLS` (default 200) AI calls per command. The command prints the token
usage. Haiku 5.5 costs about $0.001 per page (DESIGN.md §9).

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

The tests need no network, no database and no API key. One test reads `backend/app/services/dealer_import_service.py`
to check that every output column is one the portal's upload accepts.

## Adding a source

Add an entry to `sources.yaml`. The comments at the top list the options.

- **Downloadable list** (CSV / Excel): use `adapter: tabular`, `profile: generic`, `file: inputs/manual/<name>.csv`.
- **Web page or PDF list:** use `adapter: html` with `urls:`. Add `follow_links:` (a regex) for pagination or
  PDF links, and `default_dealer_type` / `default_products` when the whole list is one kind of business.
- **New column names:** add `columns: {dealer_name: ["Name of Unit"]}`.

Respect each site's terms. Never add sites whose terms forbid scraping (IndiaMART, JustDial, TradeIndia,
LinkedIn) or sources behind logins or CAPTCHAs.
