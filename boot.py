# boot.py

import esp
esp.osdebug(None)

import gc
gc.collect()

try:
    import webrepl
    webrepl.start()
except ImportError:
    pass
