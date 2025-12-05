#!/usr/bin/env python3
"""
Generate schedule_data.py for the ESP Menorah.

Requires:
    pip install astral convertdate pytz
"""

from datetime import date, datetime, timedelta
from convertdate import hebrew
from astral import LocationInfo
from astral.sun import sun
import pytz


# === CONFIG ===

# Location & timezone
CITY_NAME = "YourCity"
REGION_NAME = "YourRegion"
LATITUDE = 38.9      # example: DC-ish
LONGITUDE = -77.0
TIMEZONE_NAME = "America/New_York"

# How many years to generate (starting from START_YEAR)
START_YEAR = 2025
NUM_YEARS = 20

# Lighting window offsets (relative to local sunset/sunrise)
# In minutes
OFFSET_BEFORE_SUNSET = 60    # start this many minutes before sunset
OFFSET_AFTER_SUNRISE = 60    # end this many minutes after sunrise

OUTPUT_FILE = "schedule_data.py"


# === HELPER FUNCTIONS ===

def find_hanukkah_nights_for_year(greg_year, tz, location):
    """
    Return a list of entries for all 8 nights of Hanukkah that
    touch greg_year (some nights might be in the neighboring greg year).

    Each entry is:
        (year, month, day, night_number, start_minutes, end_minutes)
    """
    entries = []

    # Hanukkah starts 25 Kislev, runs 8 nights: 25–2/3 Tevet.
    # We need the Hebrew year corresponding to some date in this Gregorian year.
    # A simple way: convert Jan 1 of this year to Hebrew to get the Hebrew year.
    h_year, _, _ = hebrew.from_gregorian(greg_year, 1, 1)

    # For safety, we’ll check both this Hebrew year and the next, because
    # depending on where Hanukkah falls, part may be in greg_year-1 or greg_year+1.
    for hy in (h_year - 1, h_year, h_year + 1):
        # 25 Kislev
        h_month = hebrew.KISLEV
        h_day_start = 25

        # Compute Gregorian date for first night, then add nights
        g_year_start, g_month_start, g_day_start = hebrew.to_gregorian(
            hy, h_month, h_day_start)

        # convertdate gives the civil **daytime** date of 25 Kislev.
        # But we light the first candle the *previous* civil evening.
        first_day_date = date(g_year_start, g_month_start, g_day_start)
        first_night_date = first_day_date - timedelta(days=1)
        for night in range(8):
            current_date = first_night_date + timedelta(days=night)
            if current_date.year != greg_year:
                # We only want entries whose *calendar date* is in greg_year
                continue

            # Compute sunrise/sunset at this location on this date
            s = sun(location.observer, date=current_date, tzinfo=tz)

            local_sunset = s["sunset"]
            # the *next* sunrise is technically next morning
            local_sunrise = s["sunrise"]

            # Compute start = sunset - OFFSET_BEFORE_SUNSET
            start_dt = local_sunset - timedelta(minutes=OFFSET_BEFORE_SUNSET)

            # Compute end = sunrise + OFFSET_AFTER_SUNRISE (next morning)
            # If sunrise is before sunset (same day), we want the following day’s sunrise
            if local_sunrise < local_sunset:
                local_sunrise = local_sunrise + timedelta(days=1)
            end_dt = local_sunrise + timedelta(minutes=OFFSET_AFTER_SUNRISE)

            # Store times in minutes since midnight of the *calendar date* of current_date
            # We assume start_dt is on current_date or very close.
            start_minutes = start_dt.hour * 60 + start_dt.minute
            # end is after midnight → we’ll wrap into [0, 24*60*2) if needed.
            # For simplicity on the ESP, we can cap to 24:00 of next day or keep raw.
            # But earlier plan assumed we just compare same-day minutes.
            # For now, we’ll clamp end to 23:59 of current_date+1,
            # and on ESP treat “>= start or < end_if_next_day” as lit.
            # To keep it simple, we can instead treat window as same-day only,
            # assuming end stays before midnight; but let's keep basic same-day for now:

            end_minutes = end_dt.hour * 60 + end_dt.minute

            entries.append((
                current_date.year,
                current_date.month,
                current_date.day,
                night + 1,        # night number 1..8
                start_minutes,
                end_minutes,
            ))

    # Deduplicate and sort by date then night
    entries = list({(y, m, d, n, s, e) for (y, m, d, n, s, e) in entries})
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
        year_entries = find_hanukkah_nights_for_year(year, tz, location)
        all_entries.extend(year_entries)

    # Deduplicate again across years, just in case
    all_entries = list({e for e in all_entries})
    all_entries.sort()

    # Write schedule_data.py
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
