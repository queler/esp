# config.py

# Toggle this in dev vs prod. Later you can wire this to a GPIO or file.
DEV_MODE = True

# Time source selection
USE_DEBUG_TIME = DEV_MODE  # In dev, use DebugTimeProvider; in prod, NTP

# NTP settings
NTP_HOST = "pool.ntp.org"
TIMEZONE_OFFSET_MINUTES = 0  # adjust if you want local time

# How often ModeManager should re-evaluate mode (seconds)
MODE_POLL_INTERVAL = 30

# How often StatusManager updates blink codes (seconds)
STATUS_TICK_INTERVAL = 0.2
