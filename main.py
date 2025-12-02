import uasyncio as asyncio
import aiorepl
from menorah import MenorahController
from wifi_manager import WiFiManager
from candle import Candle

# Leave False when using mpremote mount; set True when you want aiorepl on serial.
ENABLE_AIOREPL = False

pins = [32, 25, 27, 12, 13, 23, 21, 19, 4]
transorder = [0, 8, 7, 6, 5, 1, 2, 3, 4]
mpins = [pins[i] for i in transorder]
menorah = MenorahController(mpins, width=50)
cs = [Candle(i) for i in mpins]

wm = WiFiManager()
_state = {"workers": [], "repl": None}


def connect_wifi():
    connected = False
    try:
        connected = wm.connect()
    except Exception as e:
        print("WiFi connect error:", e)

    if not connected:
        print("No saved/available networks. Starting config portal...")
        wm.start_config_portal()
    else:
        print("WiFi connected — to check or re-run portal call: wm.start_config_portal()")
    return connected


async def go():
    print("in go")
    for c in cs:
        print("calling on", c)
        c.on()
        print("done on", c)
        await asyncio.sleep(1)
    for c in cs:
        c.off()
        await asyncio.sleep(1)


async def _cancel_task(task):
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def stop_workers():
    tasks = list(_state["workers"])
    if _state["repl"]:
        tasks.append(_state["repl"])
    _state["workers"] = []
    _state["repl"] = None
    for t in tasks:
        await _cancel_task(t)


async def start_workers(loop_aiorepl):
    await stop_workers()
    connected = connect_wifi()
    _state["workers"] = [asyncio.create_task(go())]
    if loop_aiorepl:
        _state["repl"] = asyncio.create_task(aiorepl.task())
    return connected


async def restart(loop_aiorepl=None):
    if loop_aiorepl is None:
        loop_aiorepl = ENABLE_AIOREPL
    connected = await start_workers(loop_aiorepl)
    return "restarted (wifi_connected={}, aiorepl={})".format(connected, loop_aiorepl)


async def main(loop_aiorepl=ENABLE_AIOREPL):
    connected = await start_workers(loop_aiorepl)
    if not connected:
        print("WiFi config portal may be running; call restart() after setup.")
    # Keep the loop alive; restart() can be awaited from aiorepl when needed.
    await asyncio.Event().wait()


asyncio.run(main(ENABLE_AIOREPL))
