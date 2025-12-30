# hebrew_min.py
# MicroPython-friendly Hebrew<->Gregorian conversion (convertdate-like API)
#
# Month numbering (ecclesiastical): Nisan=1 ... Elul=6, Tishrei=7 ... Adar=12 (or Adar II=13).
#
# Minimal public API:
#   from_gregorian(y,m,d) -> (hy, hm, hd)
#   to_gregorian(hy,hm,hd) -> (y,m,d)
#   leap(hy) -> bool
#   month_days(hy, hm) -> 29/30
#
import math

# NOTE:
# This epoch value is chosen to match convertdate's published example:
# hebrew.from_gregorian(2014, 10, 31) == (5775, 8, 7)  :contentReference[oaicite:4]{index=4}
HEBREW_EPOCH = 347996.5  # Julian Day (JD) of Hebrew epoch (in this convention)

NISAN = 1
IYYAR = 2
SIVAN = 3
TAMMUZ = 4
AV = 5
ELUL = 6
TISHRI = 7
HESHVAN = 8
KISLEV = 9
TEVETH = 10
SHEVAT = 11
ADAR = 12
VEADAR = 13

MONTHS = [
    'Nisan',
    'Iyyar',
    'Sivan',
    'Tammuz',
    'Av',
    'Elul',
    'Tishri',
    'Heshvan',
    'Kislev',
    'Teveth',
    'Shevat',
    'Adar',
    'Adar Bet',
]

# ----------------- Gregorian <-> JD -----------------

def _gregorian_to_jd(y, m, d):
    """Gregorian date -> JD at midnight (as float with .5 convention)."""
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jdn = d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    # Convert JDN (integer, noon-based) to JD at midnight:
    return float(jdn) - 0.5


def _jd_to_gregorian(jd):
    """JD -> Gregorian date (y,m,d)."""
    j = int(math.floor(jd + 0.5))  # back to JDN
    a = j + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + (m // 10)
    return year, month, day


# ----------------- Hebrew calendar core -----------------

def leap(year):
    """True if Hebrew year is leap (13 months)."""
    return ((7 * year + 1) % 19) < 7


def year_months(year):
    return 13 if leap(year) else 12


def _elapsed_days(year):
    """
    Days from Hebrew epoch to Rosh Hashanah of 'year' (Tishrei 1),
    using classic 'molad' + postponement rules.
    """
    y = year - 1
    months = (235 * (y // 19) +
              12 * (y % 19) +
              ((7 * (y % 19) + 1) // 19))

    parts = 204 + 793 * (months % 1080)
    hours = 5 + 12 * months + 793 * (months // 1080) + (parts // 1080)
    day = 1 + 29 * months + (hours // 24)
    parts = (hours % 24) * 1080 + (parts % 1080)

    # Postponement rules
    if (parts >= 19440 or
        ((day % 7) == 2 and parts >= 9924 and (not leap(year))) or
        ((day % 7) == 1 and parts >= 16789 and leap(year - 1))):
        day += 1

    # Rosh Hashanah cannot be Sunday(0), Wednesday(3), Friday(5)
    if (day % 7) in (0, 3, 5):
        day += 1

    return day


def year_days(year):
    """Length of Hebrew year in days."""
    return int(_elapsed_days(year + 1) - _elapsed_days(year))


def _long_cheshvan(year):
    return (year_days(year) % 10) == 5


def _short_kislev(year):
    return (year_days(year) % 10) == 3


def month_days(year, month):
    """
    Days in Hebrew month.
    month: Nisan=1 ... Tishrei=7 ... Adar=12 (or Adar II=13).
    """
    # Always 29-day months (in this numbering)
    if month in (2, 4, 6, 10, 13):  # Iyar, Tammuz, Elul, Tevet, Adar II
        return 29

    # Adar (non-leap)
    if month == 12 and not leap(year):
        return 29

    # Variable months
    if month == 8 and not _long_cheshvan(year):
        return 29
    if month == 9 and _short_kislev(year):
        return 29

    return 30


def _hebrew_new_year_jd(year):
    return HEBREW_EPOCH + _elapsed_days(year)


def _hebrew_to_jd(year, month, day):
    """
    Hebrew (year,month,day) -> JD.
    Month numbering is ecclesiastical (Nisan=1).
    """
    jd = _hebrew_new_year_jd(year) + (day - 1)

    if month < 7:
        # Add months Tishrei..end of year
        for m in range(7, year_months(year) + 1):
            jd += month_days(year, m)
        # Add months Nisan..(month-1)
        for m in range(1, month):
            jd += month_days(year, m)
    else:
        # Add months Tishrei..(month-1)
        for m in range(7, month):
            jd += month_days(year, m)

    return jd


def _hebrew_from_jd(jd):
    jd = math.floor(jd) + 0.5

    # Rough year estimate then correct
    year = int((jd - HEBREW_EPOCH) // 366) + 1
    while jd >= _hebrew_to_jd(year + 1, 7, 1):
        year += 1

    # Find month
    if jd < _hebrew_to_jd(year, 1, 1):
        month = 7
    else:
        month = 1

    while jd > _hebrew_to_jd(year, month, month_days(year, month)):
        month += 1

    day = int(jd - _hebrew_to_jd(year, month, 1) + 1)
    return year, month, day


# ----------------- Public API -----------------

def from_gregorian(y, m, d):
    """Gregorian -> Hebrew (year,month,day)."""
    return _hebrew_from_jd(_gregorian_to_jd(y, m, d))


def to_gregorian(year, month, day):
    """Hebrew -> Gregorian."""
    return _jd_to_gregorian(_hebrew_to_jd(year, month, day))
