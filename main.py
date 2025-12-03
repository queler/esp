import uasyncio as asyncio
from menorah import MenorahController
from wifi_manager import WiFiManager
from candle import Candle
pins = [32, 25, 27, 12, 13, 23, 21, 19, 4]
transorder=[0,8,7,6,5,1,2,3,4]
mpins=[pins[i] for i in transorder]
menorah = MenorahController(mpins,width=50)
import _thread
import uasyncio as asyncio
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
# Start the menorah flickering
#mip.install('aiorepl')
import aiorepl
cs=[Candle(i) for i in mpins]

async def go():
    print('in go')
    while True:
        for i,c in enumerate(cs):
            print('calling on',i)
            c.on()
            print('done on',i)
            await asyncio.sleep(1)
        for i,c in enumerate(cs):
            print('calling off',i)
            c.off()
            print('done off',i)
            await asyncio.sleep(1)
        #while True:
    #    print('yield forever')
    #    await asyncio.sleep(0)

async def main():
    print("Starting tasks...")

    # Start other program tasks.
    t1 = asyncio.create_task(go())

    # Start the aiorepl task.
    repl = asyncio.create_task(aiorepl.task())

    await asyncio.gather(t1, repl)

asyncio.run(main())



