from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point
from rules.engine import RulesEngine

def test_rules_pack_eval(tmp_path):
    # Minimal row with expected inputs
    gdf = gpd.GeoDataFrame(
        [{"SITECODE": "X1", "CLC_CODE": "111", "dist_water_m": 500, "wfd_status": "Poor"}],
        geometry=[Point(0,0)],
        crs="EPSG:4326",
    )
    engine = RulesEngine(Path("src/rules/configs"))
    pack = engine.load_pack("sfdr_pai7_v1.yaml")
    out = engine.evaluate(gdf, pack)
    assert out.loc[0, "biodiversity_category"] == "High"
    assert out.loc[0, "water_category"] == "High"
    assert out.loc[0, "rulepack_version"] == pack.version
    assert isinstance(out.loc[0, "rule_audit"], list)
