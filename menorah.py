# menorah.py
import uasyncio as asyncio
from candle import Candle

class MenorahController:
    def __init__(self, pins, width=20):
        if len(pins) != 9:
            raise ValueError("Provide exactly 9 pins: 0=Shamash, 1-8=other candles")
        self.candles = [Candle(p, width=width) for p in pins]

    # --- Synchronous REPL controls ---
    def light(self, n):
        if 0 <= n < 9:
            self.candles[n].on()

    def extinguish(self, n):
        if 0 <= n < 9:
            self.candles[n].off()

    def light_all(self):
        for c in self.candles:
            c.on()

    def off_all(self):
        for c in self.candles:
            c.off()

    # --- Async sequences ---
    async def light_sequence(self, delay_ms=800):
        self.light(0)  # Shamash first
        await asyncio.sleep_ms(delay_ms)
        for i in range(1, 9):
            self.light(i)
            await asyncio.sleep_ms(delay_ms)

    async def extinguish_sequence(self, delay_ms=500):
        for i in reversed(range(9)):
            self.extinguish(i)
            await asyncio.sleep_ms(delay_ms)

    # --- Status / debug ---
    def status(self):
        return {i: c.is_on for i, c in enumerate(self.candles)}

    def width_set(self, n, width):
        if 0 <= n < 9:
            self.candles[n].width = width
