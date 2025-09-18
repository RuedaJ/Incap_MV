from __future__ import annotations

import json
from typing import Any, Dict

import geopandas as gpd


def to_geojson_dict(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": list(gdf.to_crs("EPSG:4326").iterfeatures()),
    }
