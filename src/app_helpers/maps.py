from __future__ import annotations

from typing import Dict, Optional

import geopandas as gpd
import pydeck as pdk


def _to_geojson_features(gdf: gpd.GeoDataFrame) -> dict:
    return {
        "type": "FeatureCollection",
        "features": gdf.to_crs("EPSG:4326").iterfeatures(),
    }


def make_map_layers(
    points: Optional[gpd.GeoDataFrame],
    overlays: Dict[str, gpd.GeoDataFrame],
    risk_col: Optional[str] = None,
) -> list:
    layers = []

    # Overlays: CORINE & Natura as polygon GeoJSON, water as scatter
    if "corine" in overlays:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                _to_geojson_features(overlays["corine"]),
                stroked=True,
                filled=False,
                lineWidthMinPixels=1,
                opacity=0.6,
            )
        )
    if "natura" in overlays:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                _to_geojson_features(overlays["natura"]),
                stroked=True,
                filled=False,
                lineWidthMinPixels=1,
                opacity=0.6,
            )
        )
    if "water" in overlays:
        w = overlays["water"].to_crs("EPSG:4326")
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=w,
                get_position="geometry.coordinates",
                get_radius=30,
                radius_min_pixels=2,
                opacity=0.7,
            )
        )

    # Points: portfolio/result
    if points is not None:
        pts = points.to_crs("EPSG:4326").copy()
        if risk_col and risk_col in pts.columns:
            color_map = {"High": [200, 30, 30], "Medium": [240, 180, 20], "Low": [30, 160, 60]}
            pts["_color"] = pts[risk_col].map(color_map).fillna([120, 120, 120])
        else:
            pts["_color"] = [30, 144, 255]  # default blue

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=pts,
                get_position="geometry.coordinates",
                get_fill_color="_color",
                get_radius=60,
                radius_min_pixels=3,
            )
        )

    return layers


def render_map(layers: list, height: int = 500):
    view_state = pdk.ViewState(latitude=48.5, longitude=9.0, zoom=4.2)
    r = pdk.Deck(layers=layers, initial_view_state=view_state, map_style=None)
    import streamlit as st

    st.pydeck_chart(r, use_container_width=True, height=height)
