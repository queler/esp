#!/usr/bin/env python3
"""
Generate schedule_events.py for the ESP Menorah.

Requires:
    pip install astral convertdate pytz
"""

from datetime import date, timedelta
from convertdate import hebrew
from astral import LocationInfo
from astral.sun import sun
import pytz


# === CONFIG ===

CITY_NAME = "Falls Church"
REGION_NAME = "Virginia"
LATITUDE = 38.9            # adjust to your location
LONGITUDE = -77.0
TIMEZONE_NAME = "America/New_York"

H_START_YEAR = 5786
NUM_YEARS = 25

OFFSET_BEFORE_SUNSET = 60    # minutes before sunset to start
OFFSET_AFTER_SUNRISE = 60    # minutes after sunrise to end

OUTPUT_FILE = "../schedule_events.py"


# === HELPERS ===

def find_hanukkah_events_for_year(hy, tz, location):
    """
    Return a list of EVENTS for all 8 nights that touch greg_year.

    Each event is:
        (year, month, day, hour, minute, state)

    state:
        1..8  = Hanukkah night N (candles ON)
        0     = Hanukkah daytime (candles OFF)
    """
    events = []

    # Hebrew year corresponding to Jan 1 of this greg year
    #h_year, _, _ = hebrew.from_gregorian(greg_year, 1, 1)

    #for hy in (h_year - 1, h_year, h_year + 1):
    # 25 Kislev of this Hebrew year
    h_month = hebrew.KISLEV
    h_day_start = 25

    g_year_start, g_month_start, g_day_start = hebrew.to_gregorian(
        hy, h_month, h_day_start
    )
    daytime_25_kislev = date(g_year_start, g_month_start, g_day_start)

    # First lighting night is the civil evening *before* 25 Kislev
    first_night_date = daytime_25_kislev - timedelta(days=1)
    suns={} 
    for night in range(9):
        lighting_date = first_night_date + timedelta(days=night)
        suns[lighting_date]=sun(location.observer, date=lighting_date, tzinfo=tz)

    for night in range(8):
        lighting_date = first_night_date + timedelta(days=night)
        next_morning_date = lighting_date + timedelta(days=1)
        
        # Compute sunset & sunrise for the lighting date
        #s = sun(location.observer, date=lighting_date, tzinfo=tz)
        local_sunset = suns[lighting_date]["sunset"]
        local_sunrise = suns[next_morning_date]["sunrise"]

        # Ensure sunrise is the *next morning*, not earlier the same day
        if local_sunrise < local_sunset:
            raise ValueError("Sunrise is before sunset")
            local_sunrise = local_sunrise + timedelta(days=1)

        start_dt = local_sunset - timedelta(minutes=OFFSET_BEFORE_SUNSET)
        end_dt = local_sunrise + timedelta(minutes=OFFSET_AFTER_SUNRISE)

        # Event: candles ON for this night
        events.append((
            start_dt.year,
            start_dt.month,
            start_dt.day,
            start_dt.hour,
            start_dt.minute,
            night + 1,   # night number 1..8
        ))

        # Event: Hanukkah daytime (candles OFF) after this night
        events.append((
            end_dt.year,
            end_dt.month,
            end_dt.day,
            end_dt.hour,
            end_dt.minute,
            0,           # Hanukkah daytime / candles off
        ))
    end_of_last_night = first_night_date + timedelta(days=8)
    last_night_sunset=suns[end_of_last_night]["sunset"]
    end_holiday_dt = last_night_sunset + timedelta(minutes=OFFSET_BEFORE_SUNSET)
    events.append((
        end_holiday_dt.year, 
        end_holiday_dt.month,
        end_holiday_dt.day,
        end_holiday_dt.hour,
        end_holiday_dt.minute,
        -1,          # End of Hanukkah
    ))
    # Deduplicate & sort
    events = list({e for e in events})
    events.sort(key=lambda e: (e[0], e[1], e[2], e[3], e[4]))
    return events


def main():
    tz = pytz.timezone(TIMEZONE_NAME)
    location = LocationInfo(
        name=CITY_NAME,
        region=REGION_NAME,
        timezone=TIMEZONE_NAME,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )

    all_events = []

    for year in range(H_START_YEAR, H_START_YEAR + NUM_YEARS):
        all_events.extend(find_hanukkah_events_for_year(year, tz, location))

    # Deduplicate & sort across all years
    all_events = list({e for e in all_events})
    all_events.sort(key=lambda e: (e[0], e[1], e[2], e[3], e[4]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Auto-generated Hanukkah schedule events\n")
        f.write("# Each entry: (year, month, day, hour, minute, state)\n")
        f.write("# state: -1 = outside Hanukkah (implicit), 0 = Hanukkah daytime, 1..8 = night\n\n")
        f.write("EVENTS = [\n")
        for (y, m, d, hh, mm, state) in all_events:
            f.write(f"    ({y}, {m}, {d}, {hh}, {mm}, {state}),\n")
        f.write("]\n")

    print(f"Wrote {len(all_events)} events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
