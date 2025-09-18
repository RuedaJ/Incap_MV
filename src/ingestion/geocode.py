from __future__ import annotations

import time
from typing import Iterable, Optional

import geopandas as gpd
import pandas as pd
from geopy.adapters import AioHTTPAdapter  # Not used yet, placeholder for async
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import ArcGIS, Nominatim
from shapely.geometry import Point

WGS84 = "EPSG:4326"


class GeocoderService:
    """
    Simple geocoding with fallback:
      1) ArcGIS (lenient, generous rate)
      2) Nominatim (OpenStreetMap, community rules)
    Respect providers' ToS:
      - Set a descriptive user_agent
      - Rate-limit requests
    """

    def __init__(
        self,
        user_agent: str = "clm-mvp-geocoder/0.1",
        min_delay_seconds: float = 1.0,
        arcgis: bool = True,
        nominatim: bool = True,
    ) -> None:
        self._providers = []
        if arcgis:
            self._providers.append(ArcGIS(timeout=10))
        if nominatim:
            self._providers.append(Nominatim(user_agent=user_agent, timeout=10))
        # Rate limiters (simple sync flow)
        self._rate = min_delay_seconds
        self._last_call = 0.0

    def _sleep_if_needed(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self._rate:
            time.sleep(self._rate - elapsed)
        self._last_call = time.time()

    def geocode_one(self, query: str) -> Optional[Point]:
        for provider in self._providers:
            self._sleep_if_needed()
            try:
                loc = provider.geocode(query)
                if loc:
                    return Point(loc.longitude, loc.latitude)
            except Exception:
                continue
        return None

    def geocode_dataframe(
        self,
        df: pd.DataFrame,
        address_cols: Iterable[str],
        output_lon: str = "lon",
        output_lat: str = "lat",
    ) -> gpd.GeoDataFrame:
        """
        Concats address columns to a single query, geocodes rows with missing geometry.
        """
        addr_series = df[list(address_cols)].astype(str).agg(", ".join, axis=1)
        lons, lats = [], []
        for q in addr_series.tolist():
            pt = self.geocode_one(q)
            if pt is None:
                lons.append(None)
                lats.append(None)
            else:
                lons.append(pt.x)
                lats.append(pt.y)
        out = df.copy()
        out[output_lon] = lons
        out[output_lat] = lats
        gdf = gpd.GeoDataFrame(
            out,
            geometry=gpd.points_from_xy(out[output_lon], out[output_lat]),
            crs=WGS84,
        )
        return gdf
