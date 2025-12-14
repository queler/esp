# status_manager.py

import uasyncio as asyncio
import config

# We’ll use string error keys for flexibility.
ERR_WIFI = "wifi"
ERR_NTP_FAIL = "ntp_fail"
ERR_NTP_MISSING = "ntp_missing"
ERR_SCHEDULE = "schedule"
ERR_TIME_INVALID = "time_invalid"


class StatusManager:
    def __init__(self, status_led=None, all_candles=None):
        # status_led: single Candle-like object for steady-state blink codes
        # all_candles: list of Candle-like objects, used at startup/fatal
        self._status_led = status_led
        self._all_candles = all_candles or []
        self._errors = set()
        self._fatal_errors = {ERR_SCHEDULE, ERR_TIME_INVALID}
        self._running = True

    def set_error(self, code):
        self._errors.add(code)

    def clear_error(self, code):
        self._errors.discard(code)

    def has_errors(self):
        return bool(self._errors)

    def has_fatal(self):
        return any(e in self._fatal_errors for e in self._errors)

    def _highest_error(self):
        if not self._errors:
            return None
        for e in self._fatal_errors:
            if e in self._errors:
                return e
        return sorted(self._errors)[0]

    async def run(self):
        # Startup self-test (no-op if no all_candles)
        await self._startup_self_test()

        while self._running:
            err = self._highest_error()
            if err is None:
                if self._status_led:
                    self._status_led.off()
                await asyncio.sleep(config.STATUS_TICK_INTERVAL)
                continue

            if err in self._fatal_errors and self._all_candles:
                await self._fatal_blink(err)
            else:
                await self._status_led_blink(err)

    async def _startup_self_test(self):
        if not self._all_candles:
            return
        for c in self._all_candles:
            c.on()
            await asyncio.sleep_ms(80)
            c.off()
        for c in self._all_candles:
            c.on()
        await asyncio.sleep_ms(200)
        for c in self._all_candles:
            c.off()

    async def _fatal_blink(self, code):
        if not self._all_candles:
            await asyncio.sleep(config.STATUS_TICK_INTERVAL)
            return
        count = _error_to_count(code)
        for _ in range(count):
            for c in self._all_candles:
                c.on()
            await asyncio.sleep_ms(150)
            for c in self._all_candles:
                c.off()
            await asyncio.sleep_ms(150)
        await asyncio.sleep_ms(600)

    async def _status_led_blink(self, code):
        if not self._status_led:
            await asyncio.sleep(config.STATUS_TICK_INTERVAL)
            return
        count = _error_to_count(code)
        for _ in range(count):
            self._status_led.on()
            await asyncio.sleep_ms(150)
            self._status_led.off()
            await asyncio.sleep_ms(150)
        await asyncio.sleep_ms(600)


def _error_to_count(code):
    if code == ERR_WIFI:
        return 1
    if code == ERR_NTP_MISSING:
        return 2
    if code == ERR_NTP_FAIL:
        return 3
    if code == ERR_SCHEDULE:
        return 4
    if code == ERR_TIME_INVALID:
        return 5
    return 1
