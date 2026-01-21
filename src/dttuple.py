# dateutil_simple.py
# Tiny date helpers (MicroPython friendly).

import time


def add_days(y: int, m: int, d: int, delta_days: int) -> tuple[int, int, int]:  # -> tuple[int, int, int]:
    """Return (y,m,d) shifted by delta_days, using a noon anchor for stability."""
    # Use noon to avoid weirdness if you ever add DST logic later.
    base = mktime_d6((y, m, d, 12, 0, 0))
    shifted = base + int(delta_days) * 86400
    t = time.localtime(shifted)
    return int(t[0]), int(t[1]), int(t[2])


def mktime_d6(dt6: tuple[int, int, int, int, int, int]) -> int:
    try:
        base = time.mktime(dt6 + (0, 0))
    except TypeError:
        base = time.mktime(dt6 + (0, 0, -1))
    return base


def add_secs(dt6: 'tuple[int,int,int,int,int,int]', delta_secs: int) ->'tuple[int,int,int,int,int,int]':  # -> tuple[int, int, int]:

    base=mktime_d6(dt6)
    shifted = base + delta_secs
    t = time.localtime(shifted)
    return t[:6]

def hm_to_min(h: int, m: int) -> int:
    return int(h) * 60 + int(m)


def min_to_hm(total_min: int) -> tuple[int, int]:
    total_min = int(total_min) % 1440
    return total_min // 60, total_min % 60
