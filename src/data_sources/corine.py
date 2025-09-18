from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import geopandas as gpd
import requests

# Small sample: use a pre-clipped CLC (provide your own URL/artifact registry).
# Placeholder URL (replace with your internal mirror or a smaller sample)
DEFAULT_URL = "https://example.org/data/corine_clc2018_sample.gpkg"
DEFAULT_LAYER = "clc2018"

def download_corine(url: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return out_path

def read_corine(path: Path, layer: Optional[str] = None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, layer=layer or DEFAULT_LAYER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download/read CORINE sample")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default="data/eu/corine/corine_sample.gpkg")
    parser.add_argument("--layer", default=DEFAULT_LAYER)
    args = parser.parse_args()

    dst = download_corine(args.url, Path(args.out))
    gdf = read_corine(dst, layer=args.layer)
    print(gdf.head(3))
