import asyncio
import httpx
import uuid
import random
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BASE_URL = "http://localhost:8000"
TOTAL_SORTERS = 100
IMAGES_PER_SORTER = 20
CONCURRENCY_LIMIT = 20

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

async def simulate_sorter(seed_lot_name: str, client: httpx.AsyncClient):
    async with semaphore:
        try:
            response = await client.post(f"{BASE_URL}/start-session", json={"seed_lot": seed_lot_name})
            session_info = response.json()
            session_id = session_info.get("session_id")
            print(f"[{seed_lot_name}] Started session: {session_id}")

            for i in range(IMAGES_PER_SORTER):
                image_id = f"{seed_lot_name}_img_{i}_{uuid.uuid4().hex[:6]}"
                await client.post(f"{BASE_URL}/send-image", json={
                    "session_id": session_id,
                    "image_id": image_id
                })
                await asyncio.sleep(0)  # allow context switch

            await asyncio.sleep(0.2)
            await client.post(f"{BASE_URL}/stop-session", json={"session_id": session_id})
            print(f"[{seed_lot_name}] Stopped session: {session_id}")

            stats_response = await client.get(f"{BASE_URL}/stats/{session_id}")
            stats = stats_response.json()

            if "accepted" in stats:
                print(f"[{seed_lot_name}] Stats: accepted={stats['accepted']}, rejected={stats['rejected']}, sampled={stats['sampled']}")
            else:
                print(f"[{seed_lot_name}] Failed to fetch stats. Response: {stats}")

        except Exception as e:
            print(f"[{seed_lot_name}] Error: {repr(e)}")

async def main():
    seed_lots = [f"Lot_{i+1}" for i in range(TOTAL_SORTERS)]
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=200)
    async with httpx.AsyncClient(limits=limits) as client:
        await asyncio.gather(*(simulate_sorter(seed_lot, client) for seed_lot in seed_lots))

if __name__ == "__main__":
    asyncio.run(main())
