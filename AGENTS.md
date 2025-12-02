# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the entry point that coordinates Wi-Fi onboarding and kicks off the candle flicker tasks plus the async REPL.
- `candle.py` implements PWM-driven flicker logic per pin; `menorah.py` provides a 9-candle controller facade for the REPL.
- `wifi_manager.py` manages STA/AP setup, a minimal config portal, and persists credentials in `wifi.json`; keep secrets out of git.
- `firmware/` holds reference MicroPython firmware images; `wokwi.toml` and `wokwi-project.txt` describe the simulator wiring.

## Build, Flash, and Development Commands
- Install host deps: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
- Flash baseline firmware (adjust port): `esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash 0x1000 firmware/ESP32_GENERIC-20250911-v1.26.1.bin`.
- Push code to the board: `mpremote connect /dev/ttyUSB0 cp *.py :` then `mpremote connect /dev/ttyUSB0 run main.py`.
- Bring in the REPL helper if missing: `mpremote mip install aiorepl`.
- Simulate with Wokwi (if available): `wokwi-server --file wokwi.toml` then connect via the provided serial endpoint.

## Coding Style & Naming Conventions
- Python, 4-space indents, PEP 8 naming (snake_case for functions/vars, CapWords for classes). Keep modules short and hardware-aware.
- Prefer async patterns already in use (`uasyncio.create_task`) and avoid large allocations or imports that bloat firmware.
- Run formatters/linters locally when possible: `black *.py`, `pylint *.py` (note: MicroPython stubs are available in requirements).

## Testing Guidelines
- No automated tests yet; validate on-device. Typical checks: connect to Wi-Fi (`wm.connect()`), start the config portal, and toggle candles via the REPL (`menorah.light(0)`).
- For new behavior, add lightweight smoke scripts under `tests/` or gate behind a `if __name__ == "__main__":` block for host-side dry runs.
- Log observable outcomes (e.g., PWM duty changes, connection attempts) to the serial console; capture regressions before flashing widely.

## Commit & Pull Request Guidelines
- Use concise, imperative commit subjects (e.g., `Add PWM width setter`); group related MicroPython changes together.
- PRs should state what hardware/port was used, how it was tested, and include serial logs or photos/gifs when relevant.
- Link to tracking issues, describe user-visible changes (LED behavior, Wi-Fi flow), and call out risk areas (power, timing, allocations).

## Security & Configuration Tips
- Never commit real Wi-Fi credentials; keep `wifi.json` device-local. Use throwaway SSIDs in examples.
- Avoid long-lived background tasks without cancellation hooks; ensure PWM is set to 0 when stopping to prevent unintended power draw.
