import uasyncio as asyncio
import sys

async def handle_client(reader, writer):
    g = __import__("__main__").__dict__
    writer.write(b"TCP REPL ready. Type Python.\n>>> ")
    await writer.drain()

    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode().strip()

        if line in ("quit", "exit"):
            break

        try:
            result = eval(line, g)
            if result is not None:
                writer.write(repr(result).encode() + b"\n")
        except SyntaxError:
            try:
                exec(line, g)
            except Exception as e:
                writer.write(("Exception: %s\n" % e).encode())
        except Exception as e:
            writer.write(("Exception: %s\n" % e).encode())

        writer.write(b">>> ")
        await writer.drain()

    await writer.wait_closed()


async def start_tcp_repl(port=4545):
    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    print("TCP REPL running on port", port)
    return server
