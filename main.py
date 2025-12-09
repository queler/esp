# main.py

import uasyncio as asyncio
import config

from wifi_manager import WiFiManager
from candle import Candle
from menorah import MenorahController

from time_provider import NTPTimeProvider, DebugTimeProvider
from schedule_data import SCHEDULE
from schedule_manager import ScheduleManager
from mode_manager import ModeManager
from status_manager import StatusManager, ERR_WIFI

import aiorepl


# Physical wiring: these came from your old main.py
PINS = [32, 25, 27, 12, 13, 23, 21, 19, 4]
TRANSORDER = [0, 8, 7, 6, 5, 1, 2, 3, 4]
MPINS = [PINS[i] for i in TRANSORDER]


async def main():
    print("Menorah starting...")

    # --- WiFi ---
    wifi = WiFiManager()
    status = StatusManager(status_led=None, all_candles=None)

    ok = await _wifi_init(wifi, status)
    if not ok:
        print("WiFi connection failed (continuing anyway for debug).")

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
    from status_manager import ERR_SCHEDULE
    if not SCHEDULE:
        status.set_error(ERR_SCHEDULE)
    else:
        status.clear_error(ERR_SCHEDULE)

    # --- Candles & Menorah ---
    candles = [Candle(pin) for pin in MPINS]
    menorah = MenorahController(candles, shamash_index=0)

    # --- Mode manager ---
    mode_mgr = ModeManager(time_provider, schedule_mgr, menorah, status)

    print("Starting tasks...")

    tasks = []

    # Menorah loop
    tasks.append(asyncio.create_task(menorah.run()))

    # Mode loop
    tasks.append(asyncio.create_task(mode_mgr.run()))

    # Status manager (currently no LEDs wired; harmless)
    tasks.append(asyncio.create_task(status.run()))

    # aiorepl for interactive debug (DEV_MODE only)
    if config.DEV_MODE:
        tasks.append(asyncio.create_task(aiorepl.task()))

    print("All tasks started.")
    await asyncio.Event().wait()


async def _wifi_init(wifi, status):
    try:
        ok = wifi.connect()  # WiFiManager.connect is synchronous in your master
    except Exception as e:
        print("WiFi connect error:", e)
        ok = False

    if not ok:
        status.set_error(ERR_WIFI)
    else:
        status.clear_error(ERR_WIFI)
    return ok


asyncio.run(main())
