# main.py

import uasyncio as asyncio
import config
from h_find import Han

from wifi_manager import WiFiManager
from candle import Candle
from menorah import MenorahController
from time_provider import NTPTimeProvider, DebugTimeProvider
#from schedule_manager import ScheduleManager
from mode_manager import ModeManager
from status_manager import StatusManager, ERR_WIFI, ERR_SCHEDULE
#import aiorepl
#import repl_server
# Globals for REPL
TP = None
MM = None
MENORAH = None
STATUS = None
SCH_MGR = None
PINS = [32, 25, 27, 12, 13, 23, 21, 19, 4]
TRANSORDER = [0, 8, 7, 6, 5, 1, 2, 3, 4]
MPINS = [PINS[i] for i in TRANSORDER]


async def main():
    global TP, MM, MENORAH, STATUS, SCH_MGR

    print("Menorah starting...")

    # --- WiFi ---
    wifi = WiFiManager()
    status = StatusManager(status_led=None, all_candles=None)
    STATUS = status
    ok = await _wifi_init(wifi, status)
    if not ok:
        print("WiFi connection failed (continuing anyway).")

    # --- Time provider ---
    if config.USE_DEBUG_TIME:
        time_provider = DebugTimeProvider()
    else:
        time_provider = NTPTimeProvider(
            host=config.NTP_HOST,
            tz_offset_minutes=config.TIMEZONE_OFFSET_MINUTES,
        )
    await time_provider.init(status)
    TP = time_provider
    # --- Schedule (event-based) ---
    schedule_mgr = Han(TP)
    if not schedule_mgr.events:
        status.set_error(ERR_SCHEDULE)
    else:
        status.clear_error(ERR_SCHEDULE)

    # --- Candles & Menorah ---
    candles = [Candle(pin) for pin in MPINS]
    menorah = MenorahController(candles, shamash_index=0)
    MENORAH = menorah

    # --- Mode manager ---
    mode_mgr = ModeManager(time_provider, schedule_mgr, menorah, status)
    MM = mode_mgr
    SCH_MGR= schedule_mgr
    print("Starting tasks...")

    tasks = [
        # Menorah loop
            asyncio.create_task(menorah.run()),
        # Mode loop
            asyncio.create_task(mode_mgr.run()),
        # Status manager (currently no LEDs wired; harmless)
            asyncio.create_task(status.run())
    ]
    if config.REPL== 'tcp':
        # # aiorepl for interactive debug (DEV_MODE only)
        # if config.DEV_MODE:
        #     tasks.append(asyncio.create_task(aiorepl.task()))
        # NEW: async TCP REPL server
        # import repl_server
        # repl_ns = {
        #     # give the REPL access to useful stuff:
        #     "asyncio": asyncio,
        #     "config": config,
        #     "TP": TP,
        #     "SCH_MGR": SCH_MGR,
        #     "MENORAH": MENORAH,
        #     "MM_MANAGER": MM,
        #     "STATUS": STATUS,
        # }
        # tasks.append(asyncio.create_task(repl_server.start_repl_server(repl_ns)))
        raise NotImplementedError
    elif 0:
      pass  
    else:
        import aiorepl
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
