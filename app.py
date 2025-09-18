from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import streamlit as st

# --- Make sure our local src/ is importable when running `streamlit run app.py`
SRC = Path(__file__).parent / "src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

# Backend utilities from your codebase
from ingestion.uploaders import read_csv, read_geojson  # type: ignore
from ingestion.geocode import GeocoderService  # type: ignore
from ingestion.spatial import (  # type: ignore
    SpatialJoinConfig,
    distance_to_nearest_water,
    flag_within_water_threshold,
    intersect_with_natura,
    overlay_corine,
)
from data_sources.corine import read_corine  # type: ignore
from data_sources.natura2000 import read_natura  # type: ignore
from data_sources.eea_waterbase import read_waterbase_points_csv  # type: ignore
from rules.engine import RulesEngine  # type: ignore

# App helpers
from app_helpers.state import init_state, get_state  # type: ignore
from app_helpers.maps import make_map_layers, render_map  # type: ignore
from app_helpers.report import build_pdf_report  # type: ignore
from app_helpers.utils import to_geojson_dict  # type: ignore


# -----------------------------
# Configuration / Constants
# -----------------------------
WGS84 = "EPSG:4326"
DATA_DIR = Path("data/eu")
RULES_DIR = Path("src/rules/configs")
DEFAULT_RULEPACK = "sfdr_pai7_v1.yaml"

st.set_page_config(
    page_title="CLM MVP – Spatial Screening",
    page_icon="🗺️",
    layout="wide",
)


# -----------------------------
# Sidebar
# -----------------------------
def sidebar():
    st.sidebar.title("CLM MVP")
    st.sidebar.caption("Spatial Screening Demo")

    # Dataset version info (replace with real version strings when available)
    st.sidebar.markdown("### Dataset versions")
    st.sidebar.write(
        "- **CORINE**: 2018 sample\n"
        "- **Natura 2000**: sample extract\n"
        "- **EEA Waterbase**: sample points"
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Disclaimers")
    st.sidebar.info(
        "This demo uses sample datasets and a prototype ruleset. "
        "Outputs are **not** for production use or external distribution."
    )
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "Navigate",
        ["1) Upload", "2) Overlays & Screening", "3) Results", "4) Report"],
        index=0,
    )
    return page


# -----------------------------
# Data loading (local samples)
# -----------------------------
@st.cache_resource(show_spinner=False)
def load_reference_data() -> dict[str, gpd.GeoDataFrame]:
    # Expect local sample files, replace with your mirrors as needed
    paths = {
        "corine": DATA_DIR / "corine" / "corine_sample.gpkg",
        "natura": DATA_DIR / "natura2000" / "natura2000_sample.gpkg",
        "water": DATA_DIR / "waterbase" / "waterbase_sample.csv",
    }
    refs: dict[str, gpd.GeoDataFrame] = {}
    if paths["corine"].exists():
        refs["corine"] = read_corine(paths["corine"])
    if paths["natura"].exists():
        refs["natura"] = read_natura(paths["natura"])
    if paths["water"].exists():
        refs["water"] = read_waterbase_points_csv(paths["water"])
    return refs


# -----------------------------
# Page 1 – Upload & Preview
# -----------------------------
def page_upload():
    st.header("Upload Portfolio – CSV or GeoJSON")
    st.write("Upload a CSV (optionally with lat/lon) or a GeoJSON with point features.")

    f = st.file_uploader("Choose a file", type=["csv", "geojson"])
    lat_col = lon_col = None
    geocode_cols: list[str] = []
    geocode_enabled = False

    col1, col2, col3 = st.columns(3)
    with col1:
        lat_col = st.text_input("Latitude column (optional)", value="")
    with col2:
        lon_col = st.text_input("Longitude column (optional)", value="")
    with col3:
        geocode_enabled = st.checkbox("Geocode addresses", value=False)

    if geocode_enabled:
        st.info("Select address columns to concatenate for geocoding.")
        geocode_cols = st.multiselect(
            "Address columns", options=[], default=[]
        )

    if f:
        try:
            if f.type == "text/csv" or f.name.lower().endswith(".csv"):
                gdf = read_csv(
                    f.read(),
                    lat_col=lat_col or None,
                    lon_col=lon_col or None,
                    crs=WGS84,
                )
                df = pd.read_csv(f)  # need to re-read for column names in UI
                st.session_state["_last_csv_cols"] = list(df.columns)
            else:
                gdf = read_geojson(f.read(), force_wgs84=True)
                st.session_state["_last_csv_cols"] = list(gdf.columns)

            # If geocoding requested and no geometry
            if geocode_enabled and ("geometry" not in gdf or gdf.geometry.isna().all()):
                opts = st.session_state.get("_last_csv_cols", [])
                geocode_cols = st.multiselect(
                    "Address columns", options=opts, default=opts[:2] if opts else []
                )
                if st.button("Run geocoding"):
                    with st.spinner("Geocoding…"):
                        svc = GeocoderService()
                        gdf = svc.geocode_dataframe(gdf, address_cols=geocode_cols)

            # Keep in state
            st.session_state["portfolio_gdf"] = gdf.to_crs(WGS84)

            st.subheader("Preview")
            st.dataframe(gdf.drop(columns="geometry", errors="ignore").head(25))

            # Map preview
            st.subheader("Map")
            render_map(
                layers=make_map_layers(points=gdf, overlays={}),
                height=500,
            )

        except Exception as e:
            st.error(f"Failed to read file: {e}")


# -----------------------------
# Page 2 – Overlays & Run Screening
# -----------------------------
def page_overlays_and_screen(refs: dict[str, gpd.GeoDataFrame]):
    st.header("Overlays & Risk Screening")

    if "portfolio_gdf" not in st.session_state:
        st.warning("Please upload a portfolio first (Page 1).")
        return

    portfolio: gpd.GeoDataFrame = st.session_state["portfolio_gdf"].to_crs(WGS84)

    # Overlay toggles
    st.subheader("Choose overlays")
    c1, c2, c3 = st.columns(3)
    with c1:
        show_corine = st.checkbox("CORINE Land Cover", value=True, help="Polygon overlay")
    with c2:
        show_natura = st.checkbox("Natura 2000", value=True, help="Polygon overlay")
    with c3:
        show_water = st.checkbox("Water bodies (sample points)", value=True)

    overlays = {}
    if show_corine and "corine" in refs:
        overlays["corine"] = refs["corine"].to_crs(WGS84)
    if show_natura and "natura" in refs:
        overlays["natura"] = refs["natura"].to_crs(WGS84)
    if show_water and "water" in refs:
        overlays["water"] = refs["water"].to_crs(WGS84)

    st.subheader("Map")
    render_map(
        layers=make_map_layers(points=portfolio, overlays=overlays),
        height=520,
    )

    st.markdown("---")
    st.subheader("Run screening")
    colA, colB = st.columns(2)
    with colA:
        buffer_m = st.number_input("Intersection buffer (m)", min_value=0, value=0, step=50)
        near_thresh = st.number_input("Near water threshold (m)", min_value=100, value=1000, step=100)
    with colB:
        predicate = st.selectbox("Intersection predicate", ["intersects", "contains", "within"])

    if st.button("Run risk screening"):
        with st.spinner("Computing…"):
            cfg = SpatialJoinConfig(
                join_how="left",
                predicate_intersect=predicate,
                buffer_meters=buffer_m if buffer_m > 0 else None,
                distance_water_threshold_m=near_thresh,
            )
            work = portfolio.copy()

            # Intersections / overlays
            if "natura" in overlays:
                work = intersect_with_natura(work, overlays["natura"], cfg)

            if "corine" in overlays:
                work = overlay_corine(work, overlays["corine"])

            if "water" in overlays:
                work = distance_to_nearest_water(work, overlays["water"])
                work = flag_within_water_threshold(work, threshold_m=near_thresh)

            # Apply rules
            engine = RulesEngine(RULES_DIR)
            pack = engine.load_pack(DEFAULT_RULEPACK)
            results = engine.evaluate(work, pack)

            # Normalize combined risk (biodiversity & water) using worst-of
            order = {"Low": 0, "Medium": 1, "High": 2, None: -1}
            def worst(a, b):
                return a if order.get(a, -1) >= order.get(b, -1) else b

            results["overall_risk"] = results.apply(
                lambda r: worst(r.get("biodiversity_category"), r.get("water_category")),
                axis=1,
            )

            # Persist
            st.session_state["screen_results"] = results.to_crs(WGS84)

        st.success("Screening complete. See Page 3 for results.")


# -----------------------------
# Page 3 – Results (table + map)
# -----------------------------
def page_results():
    st.header("Results – High / Medium / Low")
    if "screen_results" not in st.session_state:
        st.warning("Run the screening first (Page 2).")
        return

    res: gpd.GeoDataFrame = st.session_state["screen_results"]

    # Table
    st.subheader("Result table")
    cols_to_show = [
        *(c for c in ["SITECODE", "SITENAME", "CLC_CODE", "LABEL3"] if c in res.columns),
        *(c for c in ["dist_water_m", "near_water_bool", "wfd_status"] if c in res.columns),
        *(c for c in ["biodiversity_category", "water_category", "overall_risk"]),
    ]
    st.dataframe(res.drop(columns="geometry", errors="ignore")[cols_to_show], use_container_width=True)

    # Map with risk styling
    st.subheader("Map")
    render_map(
        layers=make_map_layers(
            points=res,
            overlays={},
            risk_col="overall_risk",
        ),
        height=560,
    )

    # Simple counts
    st.markdown("---")
    st.subheader("Counts")
    counts = res["overall_risk"].value_counts(dropna=False)
    st.write(counts.rename_axis("Risk").reset_index(name="Count"))


# -----------------------------
# Page 4 – Report (stub PDF)
# -----------------------------
def page_report():
    st.header("Generate Summary Report (PDF)")
    if "screen_results" not in st.session_state:
        st.warning("Run the screening first (Page 2).")
        return

    res: gpd.GeoDataFrame = st.session_state["screen_results"]
    title = st.text_input("Report title", value="CLM MVP – Screening Summary")
    author = st.text_input("Author/Org", value="Demo User")
    note = st.text_area("Additional notes", value="Prototype output – not for external distribution.")

    if st.button("Generate PDF"):
        with st.spinner("Building PDF…"):
            pdf_path = build_pdf_report(
                out_dir=Path("reports"),
                title=title,
                author=author,
                notes=note,
                counts=res["overall_risk"].value_counts(dropna=False).to_dict(),
                rulepack_file=DEFAULT_RULEPACK,
            )
        st.success("Report generated.")
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download PDF", f, file_name=Path(pdf_path).name, mime="application/pdf"
            )


# -----------------------------
# App entrypoint
# -----------------------------
def main():
    init_state()
    page = sidebar()
    refs = load_reference_data()

    if page.startswith("1"):
        page_upload()
    elif page.startswith("2"):
        page_overlays_and_screen(refs)
    elif page.startswith("3"):
        page_results()
    else:
        page_report()


if __name__ == "__main__":
    main()
