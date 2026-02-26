import asyncio
import websockets

async def test():
    url = "ws://localhost:8000/ws/test123"
    print(f"Connecting to {url}...")
    try:
        async with websockets.connect(url) as ws:
            print("Connected!")
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"Got: {msg}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())
