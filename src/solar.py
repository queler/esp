# solar.py
# Minimal sunrise/sunset calculator suitable for MicroPython.
#
# Returns sunrise/sunset as minutes since LOCAL midnight.
#
# Notes:
# - lon_deg: positive east, negative west (standard)
# - utc_offset_min: local = UTC + offset (e.g. US Eastern Standard = -300)
# - This is an approximation (NOAA-style) and is intended for scheduling.

import math

_ZENITH_DEG = 90.833  # official sunrise/sunset


def _is_leap(y: int) -> bool:
    return (y % 4 == 0) and ((y % 100 != 0) or (y % 400 == 0))


def _day_of_year(y: int, m: int, d: int) -> int:
    mdays = (31, 28 + (1 if _is_leap(y) else 0), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    total = d
    for i in range(m - 1):
        total += mdays[i]
    return total


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def sunrise_sunset_minutes(y: int, m: int, d: int, lat_deg: float, lon_deg: float, utc_offset_min: int = 0,
                           sunrise_fudge_min: "int "= 0, sunset_fudge_min: int = 0):
    """Return (sunrise_min, sunset_min) minutes since local midnight.

    Returns (None, None) for polar day/night.
    """
    n = _day_of_year(y, m, d)

    # fractional year (radians), around local noon
    gamma = 2.0 * math.pi / 365.0 * (n - 1 + (12.0 / 24.0))

    # equation of time (minutes)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    # solar declination (radians)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    lat = math.radians(lat_deg)
    zen = math.radians(_ZENITH_DEG)

    cos_ha = (math.cos(zen) / (math.cos(lat) * math.cos(decl))) - math.tan(lat) * math.tan(decl)

    if cos_ha > 1.0:
        return None, None  # sun never rises
    if cos_ha < -1.0:
        return None, None  # sun never sets

    ha_deg = math.degrees(math.acos(_clamp(cos_ha, -1.0, 1.0)))

    tz_hours = utc_offset_min / 60.0

    # solar noon in minutes (local)
    solar_noon = 720.0 - (4.0 * lon_deg) - eqtime + (tz_hours * 60.0)

    sunrise = (solar_noon - (ha_deg * 4.0)) + sunrise_fudge_min
    sunset = (solar_noon + (ha_deg * 4.0)) + sunset_fudge_min

    sunrise = sunrise % 1440.0
    sunset = sunset % 1440.0

    return int(round(sunrise)), int(round(sunset))


class SolarCache:
    """Tiny cache around sunrise_sunset_minutes for repeated queries."""

    def __init__(self, lat_deg: float, lon_deg: float, utc_offset_min: int,
                 sunrise_fudge_min: "int "= 0, sunset_fudge_min: int = 0):
        self.lat = lat_deg
        self.lon = lon_deg
        self.utc_offset_min = utc_offset_min
        self.sunrise_fudge_min = sunrise_fudge_min
        self.sunset_fudge_min = sunset_fudge_min

        self._cache_ymd = None
        self._cache = (None, None)

    def sunrise_sunset(self, y: int, m: int, d: int):
        """


        """
        key = (y, m, d)
        if key != self._cache_ymd:
            self._cache = sunrise_sunset_minutes(
                y, m, d,
                lat_deg=self.lat, lon_deg=self.lon,
                utc_offset_min=self.utc_offset_min,
                sunrise_fudge_min=self.sunrise_fudge_min,
                sunset_fudge_min=self.sunset_fudge_min,
            )
            self._cache_ymd = key
        return self._cache
