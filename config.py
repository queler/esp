# config.py

# Toggle this in dev vs prod. Later you can wire this to a GPIO or file.
DEV_MODE = True
REPL='aiorepl'
# Time source selection
USE_DEBUG_TIME = False #DEV_MODE  # In dev, use DebugTimeProvider; in prod, NTP

# NTP settings
NTP_HOST = "pool.ntp.org"
TIMEZONE_OFFSET_MINUTES = -5*60  # adjust if you want local time

# How often ModeManager should re-evaluate mode (seconds)
MODE_POLL_INTERVAL = 1

# How often StatusManager updates blink codes (seconds)
STATUS_TICK_INTERVAL = 0.2

# Location (needed for sunrise/sunset)
# lon: negative = west, positive = east
LATITUDE = 38.85     # <-- set this
LONGITUDE = -77.30   # <-- set this

# Optional tweak knobs:
# If you want "night" to start a few minutes after sunset (or end before sunrise), change these.
SUNSET_FUDGE_MINUTES = 0
SUNRISE_FUDGE_MINUTES = 0