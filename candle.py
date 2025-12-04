# candle.py
import uasyncio as asyncio
import random
from machine import Pin, PWM
import machine

class Candle:
    MAX = 65535

    def __init__(self, pin, width=80, freq=5000):
        self.pin = pin
        if machine.unique_id()==b'$\n\xc4\x00\x01\x10':
            self.width=50
        else:
            self.width = width

        self.current_duty = 0
        self.task = None
        self.led = PWM(Pin(pin), freq=freq)
        self.led.duty_u16(0)

        # Start the flicker loop immediately
        #loop = asyncio.get_event_loop()
        #self.task = loop.create_task(self._loop())
    async def _loop(self):
        while True:
            base = int(self.MAX * (self.width / 100))
            rng = int(self.MAX * (1-self.width / 100))
            duty = max(0, min(self.MAX, base + random.randint(-rng, rng)))
            self.current_duty = duty
            self.led.duty_u16(duty)
            await asyncio.sleep_ms(random.randint(50, 150))

    # --- REPL-friendly methods ---
    def on(self):
        self.enabled = True
        self.task=asyncio.create_task(self._loop())
    def off(self):
        self.enabled = False
        if self.task is not None:
            self.task.cancel()
        self.led.duty_u16(0)

