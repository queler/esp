# time_provider.py

import utime

try:
    import ntptime
except ImportError:
    ntptime = None

def _weekday_mon0(y, m, d):
    # Sakamoto; returns Mon=0..Sun=6
    t = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    y2 = y - (1 if m < 3 else 0)
    w = (y2 + y2//4 - y2//100 + y2//400 + t[m-1] + d) % 7  # Sun=0..Sat=6
    return (w - 1) % 7  # Mon=0..Sun=6

def _nth_sunday(y, m, n):
    wd1 = _weekday_mon0(y, m, 1)
    first_sun = 1 + ((6 - wd1) % 7)  # Sunday=6
    return first_sun + 7*(n-1)

def _us_dst_active_utc(now_epoch, year, std_offset_min):
    # US DST (since 2007): starts 2nd Sunday in March @ 02:00 local standard
    # ends 1st Sunday in Nov @ 02:00 local daylight
    std_off_h = std_offset_min // 60  # e.g. -5 for EST

    start_day = _nth_sunday(year, 3, 2)
    end_day   = _nth_sunday(year, 11, 1)

    # start UTC = 02:00 - std_off_h
    start_utc = _mktime_safe((year, 3, start_day, 2 - std_off_h, 0, 0))

    # end is 02:00 local daylight (std+1) => UTC = 02:00 - (std_off_h+1) = 01:00 - std_off_h
    end_utc   = _mktime_safe((year, 11, end_day, 1 - std_off_h, 0, 0))

    return start_utc <= now_epoch < end_utc
class BaseTimeProvider:
    async def init(self, status_manager=None):
        # Override in subclass
        return

    def get_time(self)-> tuple[int,int,int,int,int,int] :
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
        self._std_offset = tz_offset_minutes
        self._dst_minutes = 0
        self._dst_next_check = 0

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
        now = utime.time()  # UTC epoch seconds

        # recompute DST occasionally
        if now >= self._dst_next_check:
            y = utime.localtime(now)[0]  # UTC year
            dst = _us_dst_active_utc(now, y, self._std_offset)
            self._dst_minutes = 60 if dst else 0

            # check daily, but hourly during Mar/Nov (near transitions)
            mo = utime.localtime(now)[1]
            self._dst_next_check = now + (3600 if mo in (3, 11) else 86400)

        secs = now + (self._std_offset + self._dst_minutes) * 60
        return utime.localtime(secs)[:6]

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

    def get_time(self)-> tuple[int,int,int,int,int,int] :
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
