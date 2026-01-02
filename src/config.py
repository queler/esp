# config.py

# Toggle this in dev vs prod. Later you can wire this to a GPIO or file.
DEV_MODE = True
REPL = 'aiorepl'
# Time source selection
USE_DEBUG_TIME = False  # DEV_MODE  # In dev, use DebugTimeProvider; in prod, NTP

# NTP settings
NTP_HOST = "pool.ntp.org"
TIMEZONE_OFFSET_MINUTES = -5 * 60  # adjust if you want local time

# How often ModeManager should re-evaluate mode (seconds)
MODE_POLL_INTERVAL = 1

# How often StatusManager updates blink codes (seconds)
STATUS_TICK_INTERVAL = 0.2
# Idle display (when schedule state == -1)
IDLE_DATE_SECONDS = 2
IDLE_TIME_SECONDS = 5

# Location (needed for sunrise/sunset)
# lon: negative = west, positive = east
LATITUDE = 38.88  # 38.88135513142839, -77.21132350859696   # <-- set this
LONGITUDE = -77.21  # <-- set this

# Optional tweak knobs:
# If you want "night" to start a few minutes after sunset (or end before sunrise), change these.
SUNSET_FUDGE_MINUTES = -60
SUNRISE_FUDGE_MINUTES = 60


PRINT_MEM_INTERVAL=300