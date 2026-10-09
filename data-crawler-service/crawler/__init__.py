"""Dealer data crawler for DealerConnect (see ../DESIGN.md).

Hybrid approach: deterministic HTTP adapters for structured sources (open-data APIs, CSV / Excel files, HTML
tables) and AI extraction only for unstructured pages (dealer websites, irregular lists, PDFs). The output is a
dealers.json-format file that the portal's admin Dealer Upload accepts, with a "sources" list per dealer.
"""

__version__ = "0.1.0"
