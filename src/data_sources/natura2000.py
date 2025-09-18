from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import geopandas as gpd
import requests

# Example WFS download flow (replace with your controlled endpoint/mirror)
# The live EU WFS can be slow; for MVP prefer a mirrored sample file.
DEFAULT_URL = "https://example.org/data/natura2000_sample.gpkg"
DEFAULT_LAYER = "natura2000"

def download_natura(url: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return out_path

def read_natura(path: Path, layer: Optional[str] = None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, layer=layer or DEFAULT_LAYER)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download/read Natura 2000 sample")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default="data/eu/natura2000/natura2000_sample.gpkg")
    parser.add_argument("--layer", default=DEFAULT_LAYER)
    args = parser.parse_args()

    dst = download_natura(args.url, Path(args.out))
    gdf = read_natura(dst, layer=args.layer)
    print(gdf.head(3))
