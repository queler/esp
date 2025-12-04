# time_provider.py

import utime
import machine

try:
    import ntptime
except ImportError:
    ntptime = None


class BaseTimeProvider:
    async def init(self, status_manager=None):
        # Override in subclass
        return

    def get_time(self):
        # Returns (Y, M, D, h, m, s)
        raise NotImplementedError

    def is_valid(self):
        # Override in subclass
        return False


class NTPTimeProvider(BaseTimeProvider):
    def __init__(self, host="pool.ntp.org", tz_offset_minutes=0):
        self._host = host
        self._tz_offset = tz_offset_minutes
        self._valid = False

    async def init(self, status_manager=None):
        # status_manager is optional; if provided, set/clear errors there.
        # Non-blocking-ish: but ntptime is blocking, so we just call it once or twice.
        if ntptime is None:
            if status_manager:
                status_manager.set_error("ntp_missing")
            return

        if status_manager:
            status_manager.clear_error("ntp_missing")

        try:
            ntptime.host = self._host
        except Exception:
            # Some ports may not allow assigning host; ignore.
            pass

        tries = 3
        for _ in range(tries):
            try:
                ntptime.settime()
                self._valid = True
                if status_manager:
                    status_manager.clear_error("ntp_fail")
                break
            except Exception:
                if status_manager:
                    status_manager.set_error("ntp_fail")
            # tiny delay between attempts
            await _sleep_ms(200)

        # If valid, we might want to apply time zone offset at read time.


    def get_time(self):
        # utime.localtime() returns (Y, M, D, h, m, s, weekday, yearday)
        t = utime.localtime()
        if self._tz_offset:
            # convert to seconds, offset, back to tuple
            secs = utime.mktime(t[:6] + (0, 0)) + self._tz_offset * 60
            t = utime.localtime(secs)
        return t[:6]

    def is_valid(self):
        # Also sanity-check year so we don't treat 2000-01-01 as valid.
        y, m, d, hh, mm, ss = self.get_time()
        return self._valid and (y >= 2024)


class DebugTimeProvider(BaseTimeProvider):
    def __init__(self, start_tuple=(2025, 1, 1, 18, 0, 0), speed=3600):
        """
        start_tuple: starting simulated time (Y,M,D,h,m,s)
        speed: how many simulated seconds per real second (e.g. 3600 => 1h/s).
        """
        self._base_epoch = _mktime_safe(start_tuple)
        self._base_real = utime.time()
        self._speed = speed
        self._valid = True

    async def init(self, status_manager=None):
        # In debug we consider time always "valid"
        if status_manager:
            status_manager.clear_error("time_invalid")

    def get_time(self):
        now_real = utime.time()
        delta_real = now_real - self._base_real
        sim_secs = self._base_epoch + int(delta_real * self._speed)
        t = utime.localtime(sim_secs)
        return t[:6]

    def is_valid(self):
        return self._valid

    # Optional REPL helpers:
    def set_time(self, y, m, d, hh, mm, ss):
        self._base_epoch = _mktime_safe((y, m, d, hh, mm, ss))
        self._base_real = utime.time()

    def set_speed(self, speed):
        # Adjust speed without jumping current simulated time
        now = self.get_time()
        self._base_epoch = _mktime_safe(now)
        self._base_real = utime.time()
        self._speed = speed


def _mktime_safe(t6):
    # t6: (Y,M,D,h,m,s)
    try:
        return utime.mktime(t6 + (0, 0))
    except Exception:
        # fallback
        return 0


async def _sleep_ms(ms):
    # Small helper to avoid importing uasyncio at top-level if you don't want to.
    import uasyncio as asyncio
    await asyncio.sleep_ms(ms)
