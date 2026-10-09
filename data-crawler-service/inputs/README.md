# inputs/

Files you download for `tabular` sources (not committed: they can be large).

- `mca/<state>.csv` — data.gov.in, "Company Master Data", one resource per state (e.g. `uttar_pradesh.csv`).
- `udyam/<state>.csv` — Udyam registered units, once access is confirmed.
- `manual/dealers.csv` — your own lists (trade-fair exhibitors, association members) with headers like
  Name, Address, City, State, PIN, Phone, Email, GSTIN, Products.

File names must match `file:` in `../sources.yaml`.
