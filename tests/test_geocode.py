import pandas as pd
from ingestion.geocode import GeocoderService

def test_geocode_dataframe_no_crash(monkeypatch):
    # Fake geocode responses to avoid hitting external services
    def fake_geocode_one(self, q):
        return None  # simulate unresolved

    monkeypatch.setattr(GeocoderService, "geocode_one", fake_geocode_one)
    svc = GeocoderService(min_delay_seconds=0)

    df = pd.DataFrame({"address1": ["Somewhere"], "city": ["Nowhere"]})
    gdf = svc.geocode_dataframe(df, address_cols=["address1", "city"])
    assert "lon" in gdf.columns and "lat" in gdf.columns
    assert gdf.crs.to_string() == "EPSG:4326"
