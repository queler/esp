# main.py
import gc

import uasyncio as asyncio

import config
from candle import Candle
from h_find import Han
from menorah import MenorahController
# from schedule_manager import ScheduleManager
from mode_manager import ModeManager
from status_manager import StatusManager, ERR_WIFI, ERR_SCHEDULE
from time_provider import NTPTimeProvider, DebugTimeProvider, BaseTimeProvider
from wifi_manager import WiFiManager

#import aiorepl
#import repl_server
# Globals for REPL
TP: "BaseTimeProvider"
MM : "ModeManager"
MENORAH: "MenorahController"
STATUS: "StatusManager"
SCH_MGR : "Han"
TASKS:"list"
PINS = (32, 25, 27, 12, 13, 23, 21, 19, 4)
TRANSORDER = (0, 8, 7, 6, 5, 1, 2, 3, 4)
MPINS = tuple(PINS[i] for i in TRANSORDER)
CANDLES = None
TASKS = []
_RESTARTING = False


async def main():
    global CANDLES, _RESTARTING, TP, \
        MM, MENORAH, STATUS, SCH_MGR, TASKS

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
    schedule_mgr = Han(TP.get_time())
    if not schedule_mgr.events:
        status.set_error(ERR_SCHEDULE)
    else:
        status.clear_error(ERR_SCHEDULE)

    # --- Candles & Menorah ---
    candles = [Candle(pin) for pin in MPINS]
    CANDLES = candles

    menorah = MenorahController(candles, shamash_index=0)
    MENORAH = menorah

    # --- Mode manager ---
    mode_mgr = ModeManager(time_provider, schedule_mgr, menorah, status)
    MM = mode_mgr
    SCH_MGR= schedule_mgr
    print("Starting tasks...")

    TASKS = [
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
    # elif 0:
    #   pass
    else:
        import aiorepl
        TASKS.append(asyncio.create_task(aiorepl.task()))
    if config.PRINT_MEM_INTERVAL>0:
        TASKS.append(asyncio.create_task(printmem()))
    print("All tasks started.")
    await asyncio.Event().wait()

async def printmem():
    while True:
        print (TP.get_time(),"gc.free_mem:",gc.mem_free())
        await asyncio.sleep(config.PRINT_MEM_INTERVAL)

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

async def _cancel_tasks(tasks):
    # Cancel and give the loop a chance to deliver CancelledError
    for t in tasks:
        try:
            t.cancel()
        except Exception:
            pass
    # let cancellations run
    await asyncio.sleep_ms(0)
    await asyncio.sleep_ms(50)


async def _restart_tasks_async(resync_time=False, restart_repl=True):
    global TASKS, MM, MENORAH, SCH_MGR, TP, STATUS, _RESTARTING

    if _RESTARTING:
        print("restart already in progress")
        return
    _RESTARTING = True

    old = TASKS
    TASKS = []

    # cancel existing tasks
    await _cancel_tasks(old)

    # optionally resync time
    if resync_time:
        try:
            await TP.init(STATUS)
        except Exception as e:
            print("time resync failed:", e)

    # rebuild schedule + mode + menorah controller (reuse same Candle objects)
    SCH_MGR = Han(TP.get_time())
    MENORAH = MenorahController(CANDLES, shamash_index=0)
    MM = ModeManager(TP, SCH_MGR, MENORAH, STATUS)

    # start tasks again
    tasks = [
        asyncio.create_task(MENORAH.run()),
        asyncio.create_task(MM.run()),
        asyncio.create_task(STATUS.run()),
    ]

    if restart_repl and config.REPL != "tcp":
        try:
            import aiorepl
            tasks.append(asyncio.create_task(aiorepl.task()))
        except Exception as e:
            print("aiorepl restart failed:", e)

    TASKS = tasks
    _RESTARTING = False
    print("tasks restarted")


def restart_tasks(resync_time=False, restart_repl=True):
    # call from *real* REPL:
    #   import main; main.restart_tasks()
    asyncio.create_task(_restart_tasks_async(resync_time=resync_time, restart_repl=restart_repl))


def stop_tasks():
    # useful if you want to drop into REPL without background loops
    asyncio.create_task(_cancel_tasks(TASKS))

asyncio.run(main())
