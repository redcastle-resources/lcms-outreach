#!/usr/bin/env python3
"""
Uinta Mountains – LCMS Change via STAC + TiTiler
=================================================
Searches the Planetary Computer STAC catalog for LCMS Change data, starts a
local TiTiler COG server, then builds an interactive Folium map saved to HTML.

Usage
-----
    python uinta_lcms_stac_titiler.py            # default year = 2022
    python uinta_lcms_stac_titiler.py --year 2020

Additional requirements (beyond repo requirements.txt)
-------------------------------------------------------
    pip install pystac-client planetary-computer \
                "titiler[core]" uvicorn httpx \
                folium
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

# ── Guard optional imports with friendly messages ──────────────────────────────
try:
    import folium
except ImportError:
    sys.exit("Install folium:  pip install folium")

try:
    import pystac_client
except ImportError:
    sys.exit("Install pystac-client:  pip install pystac-client")

try:
    import uvicorn
    from fastapi import FastAPI
    from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
    from titiler.core.factory import TilerFactory
except ImportError:
    sys.exit('Install TiTiler:  pip install "titiler[core]" uvicorn fastapi')

try:
    import requests
except ImportError:
    sys.exit("Install requests:  pip install requests")

# ── Constants ──────────────────────────────────────────────────────────────────

# Planetary Computer STAC endpoint + LCMS collection
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
LCMS_COLLECTION = "usfs-lcms"

# Change band asset key as named in Planetary Computer LCMS items.
# Inspect item.assets.keys() if the search returns items but tiles are blank.
CHANGE_ASSET_KEY = "change"

# Uinta Mountains bounding box [west, south, east, north]
UINTA_BBOX = [-111.5, 40.2, -109.5, 41.2]
UINTA_CENTER = (40.72, -110.5)

# Local TiTiler port – change if 8085 is already in use
TITILER_PORT = 8085

# LCMS Change class definitions (value → label, RGBA)
# https://www.fs.usda.gov/research/rmrs/projects/lcms-data-exploration-tool
CHANGE_CLASSES: dict[int, tuple[str, tuple[int, int, int, int]]] = {
    1: ("Stable",       (172, 172, 172, 255)),
    2: ("Slow Loss",    (255, 215,   0, 255)),
    3: ("Fast Loss",    (220,  20,  60, 255)),
    4: ("Gain",         (  0, 128,   0, 255)),
    5: ("Other Change", (135, 206, 235, 255)),
}


# ── STAC helpers ───────────────────────────────────────────────────────────────

def open_catalog() -> pystac_client.Client:
    """Open the PC STAC catalog, signing requests when planetary-computer is
    available (required for authenticated assets)."""
    try:
        import planetary_computer as pc
        return pystac_client.Client.open(PC_STAC_URL, modifier=pc.sign_inplace)
    except ImportError:
        print(
            "planetary-computer package not found – URLs will NOT be signed.\n"
            "Install it for reliable access:  pip install planetary-computer"
        )
        return pystac_client.Client.open(PC_STAC_URL)


def search_lcms(year: int, bbox: list[float]) -> list:
    """Return STAC items for LCMS in *bbox* for the given *year*."""
    catalog = open_catalog()
    search = catalog.search(
        collections=[LCMS_COLLECTION],
        bbox=bbox,
        datetime=f"{year}-01-01/{year}-12-31",
        max_items=20,
    )
    items = list(search.items())
    print(f"STAC search → {len(items)} LCMS item(s) for {year}")
    return items


def extract_change_hrefs(items: list) -> list[str]:
    """Pull the signed COG href for the Change asset from each STAC item."""
    hrefs: list[str] = []
    for item in items:
        # Try a few plausible asset key spellings
        key = next(
            (k for k in (CHANGE_ASSET_KEY, "Change", "change_raw") if k in item.assets),
            None,
        )
        if key:
            href = item.assets[key].href
            hrefs.append(href)
            print(f"  ✓ {item.id!r:60s} asset={key!r}")
        else:
            available = list(item.assets.keys())
            print(
                f"  ✗ {item.id!r}: no Change asset found.\n"
                f"    Available keys: {available}\n"
                f"    Set CHANGE_ASSET_KEY to the correct key above."
            )
    return hrefs


# ── TiTiler local server ───────────────────────────────────────────────────────

def build_app() -> FastAPI:
    """Minimal FastAPI app exposing TiTiler COG endpoints."""
    app = FastAPI(title="LCMS TiTiler", version="0.1.0")
    cog_router = TilerFactory()
    app.include_router(cog_router.router, prefix="/cog", tags=["COG"])
    add_exception_handlers(app, DEFAULT_STATUS_CODES)
    return app


def start_titiler(port: int = TITILER_PORT) -> None:
    """Launch TiTiler in a background daemon thread and block until ready."""
    app = build_app()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            requests.get(f"{base}/cog/info", timeout=0.5)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.3)
    else:
        print(f"WARNING: TiTiler may not have started on port {port}.")

    print(f"TiTiler →  {base}/cog/docs")


# ── Tile-URL construction ──────────────────────────────────────────────────────

def build_colormap_param() -> str:
    """Encode CHANGE_CLASSES as the JSON string TiTiler expects for ?colormap=."""
    cm = {str(k): list(rgba) for k, (_, rgba) in CHANGE_CLASSES.items()}
    return json.dumps(cm)


def cog_tile_url(href: str, port: int = TITILER_PORT) -> str:
    """
    Return an XYZ tile template URL for a single COG served by the local
    TiTiler instance.

    TiTiler replaces {z}/{x}/{y} at request time; Folium substitutes them
    client-side with the actual tile coordinates.
    """
    params = urlencode(
        {
            "url": href,
            "colormap": build_colormap_param(),
            # Rescale: Change values are 1–5 (integer); no rescaling needed
            # but we restrict the render range to valid classes.
            "rescale": "1,5",
        }
    )
    base = f"http://127.0.0.1:{port}"
    return f"{base}/cog/tiles/{{z}}/{{x}}/{{y}}?{params}"


# ── Folium map ─────────────────────────────────────────────────────────────────

def _legend_html(year: int) -> str:
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:7px;margin:4px 0">'
        f'<span style="width:16px;height:16px;border-radius:3px;flex-shrink:0;'
        f'background:rgba({r},{g},{b},{a/255:.2f});border:1px solid #aaa"></span>'
        f'<span>{label}</span></div>'
        for _, (label, (r, g, b, a)) in CHANGE_CLASSES.items()
    )
    return f"""
    <div id="lcms-legend"
         style="position:fixed;bottom:30px;left:20px;z-index:9999;
                background:#ffffffee;padding:10px 14px;border-radius:8px;
                box-shadow:0 2px 10px rgba(0,0,0,.25);font:13px/1.4 sans-serif">
      <b style="font-size:14px">LCMS Change {year}</b>
      <div style="font-size:11px;color:#555;margin-bottom:6px">Uinta Mountains</div>
      {rows}
    </div>"""


def make_map(tile_url: str, year: int) -> folium.Map:
    m = folium.Map(
        location=list(UINTA_CENTER),
        zoom_start=9,
        tiles="CartoDB positron",
        attr="© CartoDB © OpenStreetMap",
    )

    # LCMS Change raster layer
    folium.TileLayer(
        tiles=tile_url,
        attr="USFS GTAC LCMS · TiTiler",
        name=f"LCMS Change {year}",
        overlay=True,
        opacity=0.85,
        max_zoom=15,
    ).add_to(m)

    # Study-area outline
    folium.Rectangle(
        bounds=[
            [UINTA_BBOX[1], UINTA_BBOX[0]],
            [UINTA_BBOX[3], UINTA_BBOX[2]],
        ],
        color="#1a6fad",
        fill=False,
        weight=2,
        tooltip="Uinta Mountains search area",
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend_html(year)))
    return m


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--year", type=int, default=2022, help="LCMS year (default: 2022)")
    p.add_argument(
        "--port", type=int, default=TITILER_PORT,
        help=f"Local TiTiler port (default: {TITILER_PORT})",
    )
    p.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    year = args.year
    port = args.port

    # ── 1. STAC search ─────────────────────────────────────────────────────────
    items = search_lcms(year, UINTA_BBOX)
    if not items:
        sys.exit(
            f"\nNo LCMS items returned for {year}.\n"
            f"  • Check that '{LCMS_COLLECTION}' is the correct collection name.\n"
            f"  • Try: python -c \"import pystac_client; "
            f"c=pystac_client.Client.open('{PC_STAC_URL}'); "
            f"print([col.id for col in c.get_collections()])\""
        )

    hrefs = extract_change_hrefs(items)
    if not hrefs:
        sys.exit(
            "\nChange assets not found in the returned items.\n"
            "Update CHANGE_ASSET_KEY at the top of this script to match "
            "the correct key (printed above)."
        )

    # Use the first COG for simplicity.
    # For a full mosaic across multiple tiles, add:
    #   pip install "titiler[mosaic]" cogeo-mosaic
    # and replace cog_tile_url() with a MosaicJSON-based endpoint.
    if len(hrefs) > 1:
        print(
            f"\nNote: {len(hrefs)} tiles cover the Uinta Mountains.\n"
            "Mapping the first tile only. For a full mosaic, see the comment above.\n"
        )
    cog_href = hrefs[0]

    # ── 2. Start TiTiler ───────────────────────────────────────────────────────
    start_titiler(port)

    # ── 3. Build tile URL ──────────────────────────────────────────────────────
    tile_url = cog_tile_url(cog_href, port)
    print(f"\nSample tile URL (z=8, x=47, y=98):\n  {tile_url.replace('{z}','8').replace('{x}','47').replace('{y}','98')}\n")

    # ── 4. Folium map ──────────────────────────────────────────────────────────
    m = make_map(tile_url, year)
    out_path = Path(f"uinta_lcms_change_{year}.html")
    m.save(str(out_path))
    print(f"Map saved → {out_path.resolve()}")

    if not args.no_browser:
        webbrowser.open(out_path.resolve().as_uri())

    # Keep the TiTiler daemon alive so the browser can fetch tiles
    print("\nTiTiler is serving tiles – keep this process running while viewing the map.")
    print("Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down.")


if __name__ == "__main__":
    main()
