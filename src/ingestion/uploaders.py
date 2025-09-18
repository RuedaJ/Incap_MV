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


def read_geojson(
    file_bytes: bytes, force_wgs84: bool = True
) -> gpd.GeoDataFrame:
    """
    Reads a GeoJSON (bytes) and returns a GeoDataFrame in WGS84.
    """
    data = json.loads(file_bytes.decode("utf-8"))
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    if force_wgs84:
        # Many GeoJSON are already 4326, but be explicit when possible
        if gdf.crs is None:
            gdf.set_crs(WGS84, inplace=True)
        else:
            gdf = gdf.to_crs(WGS84)
    return gdf


def validate_columns(
    df: Union[pd.DataFrame, gpd.GeoDataFrame], required: Iterable[str]
) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
