# time_provider.py

import utime

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
        """
        Initialize time from NTP.
        status_manager is optional; if provided, we set/clear NTP errors there.

        Note: ntptime.settime() is blocking; we just call it a few times.
        """
        from status_manager import ERR_NTP_MISSING, ERR_NTP_FAIL  # late import to avoid cycles

        if ntptime is None:
            if status_manager:
                status_manager.set_error(ERR_NTP_MISSING)
            return

        if status_manager:
            status_manager.clear_error(ERR_NTP_MISSING)

        try:
            ntptime.host = self._host
        except Exception:
            # Some ports may not allow assigning host; ignore.
            pass

        import uasyncio as asyncio

        tries = 3
        for _ in range(tries):
            try:
                ntptime.settime()
                self._valid = True
                if status_manager:
                    status_manager.clear_error(ERR_NTP_FAIL)
                break
            except Exception:
                if status_manager:
                    status_manager.set_error(ERR_NTP_FAIL)
            # tiny delay between attempts
            await asyncio.sleep_ms(200)

    def get_time(self):
        """
        Return current local time as (Y, M, D, h, m, s),
        applying the configured TZ offset in minutes.
        """
        t = utime.localtime()  # (Y,M,D,h,m,s,wd,yd)
        if self._tz_offset:
            # convert to seconds, offset, back to tuple
            secs = utime.mktime(t[:6] + (0, 0)) + self._tz_offset * 60
            t = utime.localtime(secs)
        return t[:6]

    def is_valid(self):
        """
        Treat time as valid if we've successfully synced and the year is sane.
        """
        if not self._valid:
            return False
        y, m, d, hh, mm, ss = self.get_time()
        return y >= 2024


class DebugTimeProvider(BaseTimeProvider):
    """
    Simulated time provider for development.

    - start_tuple: base simulated time (Y,M,D,h,m,s)
    - speed: simulated seconds per real second (e.g. 3600 => 1h/s)
    """

    def __init__(self, start_tuple=(2025, 1, 1, 18, 0, 0), speed=3600):
        self._base_epoch = _mktime_safe(start_tuple)
        self._base_real = utime.time()
        self._speed = speed
        self._valid = True

    async def init(self, status_manager=None):
        from status_manager import ERR_TIME_INVALID
        # In debug we consider time always "valid".
        self._valid = True
        if status_manager:
            status_manager.clear_error(ERR_TIME_INVALID)

    def get_time(self):
        now_real = utime.time()
        delta_real = now_real - self._base_real
        sim_secs = self._base_epoch + int(delta_real * self._speed)
        t = utime.localtime(sim_secs)
        return t[:6]

    def is_valid(self):
        return self._valid

    # REPL helpers:
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
