import uasyncio as asyncio
from menorah import MenorahController
from wifi_manager import WiFiManager

pins = [32, 25, 27, 12, 13, 23, 21, 19, 4]
transorder = [0, 8, 7, 6, 5, 1, 2, 3, 4]
mpins = [pins[i] for i in transorder]
menorah = MenorahController(mpins, width=50)

# Connect to WiFi (or start config portal if no credentials)
wm = WiFiManager()
connected = False
try:
    connected = wm.connect()
except Exception as e:
    print('WiFi connect error:', e)

if not connected:
    # This will block and run a small AP + web form; after saving it reboots
    print('No saved/available networks. Starting config portal...')
    wm.start_config_portal()
else:
    print('WiFi connected — to check or re-run portal call: wm.start_config_portal()')


async def _start_menorah():
    # Turn on flicker for all candles (non-blocking tasks)
    menorah.light_all()
    # Keep the loop alive; user can add sequences or other tasks here
    while True:
        await asyncio.sleep(60)


try:
    # Preferred: run the coroutine if available
    asyncio.run(_start_menorah())
except AttributeError:
    # Fallback for older uasyncio versions
    loop = asyncio.get_event_loop()
    loop.create_task(_start_menorah())
    loop.run_forever()
