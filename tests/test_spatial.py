import geopandas as gpd
from shapely.geometry import Point, Polygon
from ingestion.spatial import (
    SpatialJoinConfig,
    distance_to_nearest_water,
    flag_within_water_threshold,
    overlay_corine,
    intersect_with_natura,
)

def _toy():
    portfolio = gpd.GeoDataFrame(geometry=[Point(0, 0)], crs="EPSG:4326")
    natura = gpd.GeoDataFrame(
        {"SITECODE": ["ABC"], "SITENAME": ["Site A"]},
        geometry=[Polygon([(-0.1,-0.1), (0.1,-0.1), (0.1,0.1), (-0.1,0.1)])],
        crs="EPSG:4326",
    )
    corine = gpd.GeoDataFrame(
        {"CLC_CODE": ["111"], "LABEL3": ["Urban"]},
        geometry=[Polygon([(-1,-1), (1,-1), (1,1), (-1,1)])],
        crs="EPSG:4326",
    )
    water = gpd.GeoDataFrame(geometry=[Point(0.005, 0)], crs="EPSG:4326")
    return portfolio, natura, corine, water

def test_intersections():
    p, n, c, w = _toy()
    cfg = SpatialJoinConfig()
    out = intersect_with_natura(p, n, cfg)
    assert "SITECODE" in out.columns
    out2 = overlay_corine(p, c)
    assert out2["CLC_CODE"].iloc[0] == "111"

def test_distance_and_flag():
    p, n, c, w = _toy()
    dist = distance_to_nearest_water(p, w)
    assert "dist_water_m" in dist.columns
    flagged = flag_within_water_threshold(dist, threshold_m=1100)
    assert flagged["near_water_bool"].iloc[0] in (True, False)
