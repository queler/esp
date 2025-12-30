# dateutil_simple.py
# Tiny date helpers (MicroPython friendly).

import time

LT_TUPLE_SIZE = len(time.localtime())


def mktimex(y: int, mo: int = 1, d: int = 1, h: int = 0, mi: int = 0,
            s: int = 0, wd: int = 0, yd: int = 0,
            dst: int = -1) -> int:
    if LT_TUPLE_SIZE == 9:
        return int(time.mktime((y, mo, d, h, mi, s, wd, yd, dst)))
    if LT_TUPLE_SIZE == 8:
        return int(time.mktime((y, mo, d, h, mi, s, wd, yd)))
    raise NotImplementedError("Unknown localtime() tuple size: %d" % LT_TUPLE_SIZE)


def add_days(y: int, m: int, d: int, delta_days: int) -> tuple[int, int, int]:  # -> tuple[int, int, int]:
    """Return (y,m,d) shifted by delta_days, using a noon anchor for stability."""
    # Use noon to avoid weirdness if you ever add DST logic later.
    try:
        base = time.mktime((y, m, d, 12, 0, 0, 0, 0))
    except TypeError:
        base = time.mktime((y, m, d, 12, 0, 0, 0, 0, -1))
    shifted = base + int(delta_days) * 86400
    t = time.localtime(shifted)
    return int(t[0]), int(t[1]), int(t[2])


def hm_to_min(h: int, m: int) -> int:
    return int(h) * 60 + int(m)


def min_to_hm(total_min: int) -> tuple[int, int]:
    total_min = int(total_min) % 1440
    return total_min // 60, total_min % 60
