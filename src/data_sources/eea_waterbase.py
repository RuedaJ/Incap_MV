from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

# Placeholder CSV with lon/lat and WFD status (replace with real Waterbase sample)
DEFAULT_URL = "https://example.org/data/eea_waterbase_sample.csv"

def download_waterbase(url: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path

def read_waterbase_points_csv(path: Path, lon="lon", lat="lat", status_col="wfd_status") -> gpd.GeoDataFrame:
    df = pd.read_csv(path)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs="EPSG:4326")
    # Normalize a minimal schema the screening expects
    if status_col not in gdf.columns:
        gdf[status_col] = None
    gdf["WATER_ID"] = gdf.get("water_id", gdf.index.astype(str))
    return gdf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download/read EEA Waterbase sample")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default="data/eu/waterbase/waterbase_sample.csv")
    args = parser.parse_args()

    dst = download_waterbase(args.url, Path(args.out))
    gdf = read_waterbase_points_csv(dst)
    print(gdf.head(3))
