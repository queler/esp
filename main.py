# main.py

import uasyncio as asyncio
import config

from wifi_manager import WiFiManager
from menorah import MenorahController  # your existing class
# from candle import Candle  # if needed for constructing individual candles

from time_provider import NTPTimeProvider, DebugTimeProvider
from schedule_data import SCHEDULE
from schedule_manager import ScheduleManager
from mode_manager import ModeManager
from status_manager import StatusManager, ERR_WIFI

import aiorepl  # existing aiorepl module


async def main():
    print("Menorah starting...")

    # --- WiFi ---
    wifi = WiFiManager()
    status = StatusManager()  # will plug LEDs below after we build Menorah
    ok = await _wifi_init(wifi, status)

    # --- Time Provider ---
    if config.USE_DEBUG_TIME:
        time_provider = DebugTimeProvider()
    else:
        time_provider = NTPTimeProvider(
            host=config.NTP_HOST,
            tz_offset_minutes=config.TIMEZONE_OFFSET_MINUTES,
        )

    await time_provider.init(status)

    # --- Schedule ---
    schedule_mgr = ScheduleManager(SCHEDULE)
    # If SCHEDULE is empty, we’ll treat everything as non-Hanukkah:
    if not SCHEDULE:
        status.set_error("schedule")
    else:
        status.clear_error("schedule")

    # --- Menorah + Status LED wiring ---
    # You already have pins & MenorahController in your code; adjust this.
    # Example:
    pins = [32, 25, 27, 12, 13, 23, 21, 19, 4]
    transorder=[0,8,7,6,5,1,2,3,4]
    mpins=[pins[i] for i in transorder]
    menorah = MenorahController(mpins,width=50)
    # menorah = MenorahController(candles)
    # menorah = MenorahController()  # adapt to your real constructor

    # Optionally wire status manager to use the shamash or a dedicated LED
    # status_led = menorah.get_shamash_candle()
    # status_all = menorah.get_all_candles()
    # status = StatusManager(status_led=status_led, all_candles=status_all)

    # --- Managers ---
    mode_mgr = ModeManager(time_provider, schedule_mgr, menorah, status)

    # --- Tasks ---
    tasks = []

    # Menorah effect loop
    tasks.append(asyncio.create_task(menorah.run()))

    # Mode manager
    tasks.append(asyncio.create_task(mode_mgr.run()))

    # Status manager
    tasks.append(asyncio.create_task(status.run()))

    # aiorepl for interactive debug (optional in prod)
    if config.DEV_MODE:
        tasks.append(asyncio.create_task(aiorepl.task()))

    print("All tasks started.")
    # Block forever
    await asyncio.Event().wait()


async def _wifi_init(wifi, status):
    try:
        ok = await wifi.connect()
    except Exception:
        ok = False

    if not ok:
        status.set_error(ERR_WIFI)
    else:
        status.clear_error(ERR_WIFI)
    return ok


asyncio.run(main())
