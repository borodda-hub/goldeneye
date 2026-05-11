"""Representative population-weighted lat/lon points per region for NWS API calls."""

REGION_POINTS: dict[str, list[tuple[float, float, float]]] = {
    "northeast": [(40.71, -74.01, 0.4), (42.36, -71.06, 0.35), (39.95, -75.17, 0.25)],  # NYC, Boston, Philadelphia
    "midwest":   [(41.88, -87.63, 0.35), (39.96, -82.99, 0.3), (44.98, -93.27, 0.2), (38.63, -90.20, 0.15)],  # Chicago, Columbus, Minneapolis, St. Louis
    "mountain":  [(39.74, -104.98, 0.4), (36.17, -115.14, 0.35), (40.76, -111.89, 0.25)],  # Denver, Las Vegas, Salt Lake
    "pacific":   [(34.05, -118.24, 0.45), (37.77, -122.42, 0.35), (47.61, -122.33, 0.20)],  # LA, SF, Seattle
    "south_central": [(29.76, -95.37, 0.35), (32.79, -96.80, 0.3), (35.47, -97.52, 0.2), (30.27, -97.74, 0.15)],  # Houston, Dallas, OKC, Austin
    "southeast": [(33.75, -84.39, 0.3), (30.33, -81.66, 0.25), (35.23, -80.84, 0.25), (36.17, -86.78, 0.2)],  # Atlanta, Jacksonville, Charlotte, Nashville
}
