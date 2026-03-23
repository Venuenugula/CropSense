from forecast.weather import DEFAULT_LAT, DEFAULT_LON, resolve_location


def test_resolve_location_known_english_district():
    lat, lon = resolve_location("warangal")
    assert (lat, lon) != (DEFAULT_LAT, DEFAULT_LON)


def test_resolve_location_unknown_falls_back_to_default():
    lat, lon = resolve_location("unknown_district_xyz")
    assert (lat, lon) == (DEFAULT_LAT, DEFAULT_LON)
