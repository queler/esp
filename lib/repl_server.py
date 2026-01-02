# repl_server.py
#
# Simple async REPL over TCP for MicroPython/uasyncio.
# - One client at a time.
# - Supports single-line Python, plus "await <expr>" for coroutines.

import uasyncio as asyncio

WELCOME = "Async REPL ready. Type Python or 'await <expr>'. Ctrl-] to quit.\n"


async def _awrite(writer, data):
    # Helper to write bytes or str
    if isinstance(data, str):
        data = data.encode()
    await writer.awrite(data)


async def handle_client(reader, writer, ns):
    try:
        peer = writer.get_extra_info("peername")
    except Exception:
        peer = None
    print("REPL client connected:", peer)

    # Namespace shared with the main app
    locals_ns = ns

    await _awrite(writer, WELCOME)

    while True:
        try:
            await _awrite(writer, ">>> ")
            line = await reader.readline()
            if not line:
                break

            try:
                line = line.decode().strip()
            except Exception:
                continue

            if not line:
                continue

            if line in ("exit", "quit", "\x1d"):  # Ctrl-]
                break

            try:
                # Handle "await expr"
                if line.startswith("await "):
                    expr = line[6:].strip()
                    obj = eval(expr, locals_ns, locals_ns)
                    if hasattr(obj, "__await__") or hasattr(obj, "send"):
                        result = await obj
                    else:
                        result = obj
                else:
                    # Try eval, fall back to exec
                    try:
                        result = eval(line, locals_ns, locals_ns)
                    except SyntaxError:
                        exec(line, locals_ns, locals_ns)
                        result = None

                if result is not None:
                    await _awrite(writer, repr(result) + "\n")
            except Exception as e:
                await _awrite(writer, "Error: %s\n" % repr(e))

        except Exception as e:
            print("REPL client error:", repr(e))
            break

    try:
        await writer.aclose()
    except Exception:
        pass
    print("REPL client disconnected:", peer)


async def start_repl_server(ns, host="0.0.0.0", port=8023):
    """
    Start a TCP server providing an async REPL.

    ns: dict of globals to use as the REPL namespace.
    """
    async def _client_wrapper(reader, writer):
        await handle_client(reader, writer, ns)

    server = await asyncio.start_server(_client_wrapper, host, port)

    # MicroPython doesn't need serve_forever/wait_closed here;
    # the server keeps running in the background as long as the
    # event loop is alive.
    print("Async REPL listening on %s:%d" % (host, port))

    # Just keep this coroutine alive so the task doesn't finish immediately.
    # A cheap way: wait on a never-set Event.
    stopper = asyncio.Event()
    await stopper.wait()
