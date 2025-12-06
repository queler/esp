#!/usr/bin/env python3
"""
Generate schedule_data.py for the ESP Menorah.

Requires:
    pip install astral convertdate pytz
"""

from datetime import date, timedelta
from convertdate import hebrew
from astral import LocationInfo
from astral.sun import sun
import pytz


# === CONFIG ===

CITY_NAME = "YourCity"
REGION_NAME = "YourRegion"
LATITUDE = 38.9            # adjust to your location
LONGITUDE = -77.0
TIMEZONE_NAME = "America/New_York"

START_YEAR = 2025
NUM_YEARS = 20

# In minutes
OFFSET_BEFORE_SUNSET = 60    # start this many minutes before sunset
OFFSET_AFTER_SUNRISE = 60    # end this many minutes after sunrise

# Write into the firmware root
OUTPUT_FILE = "../schedule_data.py"


# === HELPER FUNCTIONS ===

def find_hanukkah_nights_for_year(greg_year, tz, location):
    """
    Return a list of entries for all 8 nights of Hanukkah that
    touch greg_year (some nights might be in the neighboring greg year).

    Each entry is:
        (year, month, day, night_number, start_minutes, end_minutes)
    """
    entries = []

    # Determine Hebrew year corresponding to Jan 1 of this greg year
    h_year, _, _ = hebrew.from_gregorian(greg_year, 1, 1)

    # Check nearby Hebrew years in case of cross-year boundaries
    for hy in (h_year - 1, h_year, h_year + 1):
        h_month = hebrew.KISLEV
        h_day_start = 25

        # convertdate returns the civil *daytime* date of 25 Kislev.
        g_year_start, g_month_start, g_day_start = hebrew.to_gregorian(
            hy, h_month, h_day_start)
        daytime_25_kislev = date(g_year_start, g_month_start, g_day_start)

        # We actually light the first candle the *previous* civil evening.
        first_night_date = daytime_25_kislev - timedelta(days=1)

        for night in range(8):
            current_date = first_night_date + timedelta(days=night)
            if current_date.year != greg_year:
                continue

            s = sun(location.observer, date=current_date, tzinfo=tz)
            local_sunset = s["sunset"]
            local_sunrise = s["sunrise"]

            # If sunrise is earlier than sunset, use the next day's sunrise
            if local_sunrise < local_sunset:
                local_sunrise = local_sunrise + timedelta(days=1)

            start_dt = local_sunset - timedelta(minutes=OFFSET_BEFORE_SUNSET)
            end_dt = local_sunrise + timedelta(minutes=OFFSET_AFTER_SUNRISE)

            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute

            entries.append((
                current_date.year,
                current_date.month,
                current_date.day,
                night + 1,
                start_minutes,
                end_minutes,
            ))

    # Deduplicate and sort
    entries = list({e for e in entries})
    entries.sort()
    return entries


def main():
    tz = pytz.timezone(TIMEZONE_NAME)
    location = LocationInfo(
        name=CITY_NAME,
        region=REGION_NAME,
        timezone=TIMEZONE_NAME,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )

    all_entries = []

    for year in range(START_YEAR, START_YEAR + NUM_YEARS):
        all_entries.extend(find_hanukkah_nights_for_year(year, tz, location))

    all_entries = list({e for e in all_entries})
    all_entries.sort()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Auto-generated Hanukkah schedule data\n")
        f.write("# Format: (year, month, day, night, start_minutes, end_minutes)\n\n")
        f.write("SCHEDULE = [\n")
        for (y, m, d, night, start_min, end_min) in all_entries:
            f.write(f"    ({y}, {m}, {d}, {night}, {start_min}, {end_min}),\n")
        f.write("]\n")

    print(f"Wrote {len(all_entries)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
