from __future__ import annotations

import io
import json
from typing import Iterable, Optional, Union

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

WGS84 = "EPSG:4326"


def read_csv(
    file_bytes: bytes,
    lat_col: Optional[str] = None,
    lon_col: Optional[str] = None,
    crs: str = WGS84,
) -> gpd.GeoDataFrame:
    """
    Reads a CSV (bytes) and returns a GeoDataFrame.
    If lat/lon provided, builds point geometry.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    if lat_col and lon_col and lat_col in df and lon_col in df:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df[lon_col], df[lat_col])],
            crs=WGS84,
        )
        return gdf.to_crs(crs)
    # Return as non-spatial table (empty geometry) for later geocoding
    df["_geometry"] = None
    gdf = gpd.GeoDataFrame(df, geometry="_geometry", crs=WGS84)
    return gdf.drop(columns=["_geometry"])


def read_geojson(file_bytes: bytes, force_wgs84: bool = True) -> gpd.GeoDataFrame:
    """
    Reads a GeoJSON (bytes) and returns a GeoDataFrame (handles FeatureCollection,
    single Feature, or bare geometry). Defaults CRS to WGS84 if missing.
    """
    data = json.loads(file_bytes.decode("utf-8"))
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        features = data.get("features", [])
    elif isinstance(data, dict) and data.get("type") == "Feature":
        features = [data]
    elif isinstance(data, dict) and "type" in data and "coordinates" in data:
        # bare geometry → wrap as Feature
        features = [{"type": "Feature", "properties": {}, "geometry": data}]
    else:
        raise ValueError("Unsupported GeoJSON structure. Expect FeatureCollection or Feature.")

    gdf = gpd.GeoDataFrame.from_features(features)

    # Ensure CRS
    if gdf.crs is None:
        gdf.set_crs(WGS84, inplace=True)
    if force_wgs84 and gdf.crs.to_string() != WGS84:
        gdf = gdf.to_crs(WGS84)
    return gdf


def validate_columns(
    df: Union[pd.DataFrame, gpd.GeoDataFrame], required: Iterable[str]
) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
