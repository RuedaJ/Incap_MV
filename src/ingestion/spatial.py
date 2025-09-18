from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import geopandas as gpd
from shapely.ops import nearest_points

WGS84 = "EPSG:4326"


@dataclass
class SpatialJoinConfig:
    """Configuration for screening steps."""
    join_how: str = "left"  # 'left' or 'inner'
    predicate_intersect: str = "intersects"  # intersects, contains, within
    buffer_meters: Optional[float] = None  # buffer input points for intersection
    distance_water_threshold_m: float = 1000.0  # <1km from water


def _ensure_crs_3857(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs("EPSG:3857")


def intersect_with_natura(
    portfolio: gpd.GeoDataFrame, natura_polygons: gpd.GeoDataFrame, cfg: SpatialJoinConfig
) -> gpd.GeoDataFrame:
    a = _ensure_crs_3857(portfolio)
    b = _ensure_crs_3857(natura_polygons)

    if cfg.buffer_meters:
        a = a.copy()
        a["geometry"] = a.geometry.buffer(cfg.buffer_meters)

    joined = gpd.sjoin(
        a, b[["geometry", "SITECODE", "SITENAME"]], how=cfg.join_how, predicate=cfg.predicate_intersect
    )
    joined = joined.to_crs(WGS84)
    return joined


def overlay_corine(
    portfolio: gpd.GeoDataFrame, corine_polygons: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    a = _ensure_crs_3857(portfolio)
    b = _ensure_crs_3857(corine_polygons[["geometry", "CLC_CODE", "LABEL3"]])
    # Spatial join to get the polygon attributes onto points
    out = gpd.sjoin(a, b, how="left", predicate="intersects").drop(columns=["index_right"])
    return out.to_crs(WGS84)


def distance_to_nearest_water(
    portfolio: gpd.GeoDataFrame, water_geoms: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    a = _ensure_crs_3857(portfolio)
    w = _ensure_crs_3857(water_geoms)

    # Build spatial index and compute nearest geometry efficiently
    w_sindex = w.sindex
    distances_m = []
    nearest_id = []

    for geom in a.geometry:
        possible_matches_index = list(w_sindex.nearest(geom.bounds, 1))
        candidate = w.iloc[possible_matches_index[0]].geometry
        p1, p2 = nearest_points(geom, candidate)
        distances_m.append(p1.distance(p2))
        nearest_id.append(w.index[possible_matches_index[0]])

    out = a.copy()
    out["dist_water_m"] = distances_m
    out["nearest_water_id"] = nearest_id
    return out.to_crs(WGS84)


def flag_within_water_threshold(
    portfolio_with_distance: gpd.GeoDataFrame, threshold_m: float
) -> gpd.GeoDataFrame:
    out = portfolio_with_distance.copy()
    out["near_water_bool"] = out["dist_water_m"] <= threshold_m
    return out
