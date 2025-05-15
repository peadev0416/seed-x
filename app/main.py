import asyncio
import random
import time
import uuid
import os
import csv
import json
import re
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 8))
MAX_SINGLE_IMAGE_LATENCY_MS = int(os.getenv("MAX_SINGLE_IMAGE_LATENCY_MS", 300))
SAMPLE_PERCENTAGE = int(os.getenv("SAMPLE_PERCENTAGE", 10))
SAMPLE_DIR = os.getenv("SAMPLE_DIR", "sampled_images")
SESSION_CSV = "session_data.csv"

# Create sample directory
os.makedirs(SAMPLE_DIR, exist_ok=True)

# Shared state
session_state: Dict[str, Dict] = {}
session_image_queues: Dict[str, List[Dict]] = {}
session_queues_lock = asyncio.Lock()

# Models
class StartSessionRequest(BaseModel):
    seed_lot: str

class StopSessionRequest(BaseModel):
    session_id: str

class ImageInput(BaseModel):
    image_id: str
    session_id: str

# Utilities
def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

def save_session_to_csv(row: Dict):
    file_exists = os.path.isfile(SESSION_CSV)
    with open(SESSION_CSV, mode="a", newline="") as csvfile:
        fieldnames = [
            "session_id", "seed_lot", "accepted", "rejected", "sampled",
            "sampled_images", "start_time", "end_time"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def get_session_from_csv(session_id: str) -> Optional[Dict]:
    if not os.path.exists(SESSION_CSV):
        return None
    with open(SESSION_CSV, mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["session_id"] == session_id:
                try:
                    row["sampled_images"] = json.loads(row["sampled_images"])
                    row["accepted"] = int(row["accepted"])
                    row["rejected"] = int(row["rejected"])
                    row["sampled"] = int(row["sampled"])
                    row["start_time"] = float(row["start_time"])
                    row["end_time"] = float(row["end_time"]) if row["end_time"] else ""
                    return row
                except Exception as e:
                    print(f"[ERROR] Failed to load row from CSV: {e}")
                    return None
    return None

def get_active_or_saved_session(session_id: str) -> Optional[Dict]:
    if session_id in session_state:
        return session_state[session_id]
    return get_session_from_csv(session_id)

# API Endpoints
@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")

@app.post("/start-session")
def start_session(req: StartSessionRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "seed_lot": req.seed_lot,
        "accepted": 0,
        "rejected": 0,
        "sampled": 0,
        "sampled_images": [],
        "start_time": time.time(),
        "end_time": ""
    }
    session_state[session_id] = session_data
    session_image_queues[session_id] = []
    background_tasks.add_task(batch_processor, session_id)
    return {"session_id": session_id, "message": f"Sorting session started for seed lot '{req.seed_lot}'"}

@app.post("/stop-session")
def stop_session(req: StopSessionRequest):
    session_id = req.session_id
    session = session_state.get(session_id)
    if not session:
        return {"error": "Session not found or already stopped."}

    session["end_time"] = time.time()
    save_session_to_csv({
        **session,
        "sampled_images": json.dumps(session["sampled_images"])
    })
    session_state.pop(session_id, None)
    session_image_queues.pop(session_id, None)
    return {"message": f"Session {session_id} stopped."}

@app.post("/send-image")
async def send_image(image: ImageInput):
    session_id = image.session_id
    if session_id not in session_state:
        return {"error": "Invalid or inactive session."}

    async with session_queues_lock:
        session_image_queues[session_id].append({
            "image_id": image.image_id,
            "timestamp": time.time(),
            "session_id": session_id
        })
    return {"message": "Image received."}

@app.get("/stats/{session_id}")
def get_stats(session_id: str):
    session = get_active_or_saved_session(session_id)
    if not session:
        return {"error": "Session not found."}
    return session

@app.get("/sampled-images/{session_id}")
def get_sampled_images(session_id: str):
    session = get_active_or_saved_session(session_id)
    if not session:
        return {"error": "Session not found."}
    return {"sampled_images": session["sampled_images"]}

@app.get("/sessions")
def list_sessions():
    if not os.path.exists(SESSION_CSV):
        return []

    sessions = []
    with open(SESSION_CSV, mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                sessions.append({
                    "session_id": row["session_id"],
                    "seed_lot": row["seed_lot"],
                    "start_time": float(row["start_time"]),
                    "end_time": float(row["end_time"]) if row["end_time"] else "",
                    "accepted": int(row["accepted"]),
                    "rejected": int(row["rejected"]),
                    "sampled": int(row["sampled"])
                })
            except Exception as e:
                print(f"[ERROR] Skipping malformed row: {e}")
    return sessions

# Batch Processor
async def batch_processor(session_id: str):
    print(f"[INFO] Batch processor started for session {session_id}")
    try:
        while session_id in session_state:
            now = time.time()
            ready_batch = []

            async with session_queues_lock:
                queue = session_image_queues.get(session_id, [])
                i = 0
                while i < len(queue):
                    image = queue[i]
                    age = now - image["timestamp"]

                    if len(ready_batch) < MAX_BATCH_SIZE and age >= (MAX_SINGLE_IMAGE_LATENCY_MS / 1000):
                        ready_batch.append(image)
                        del queue[i]
                    else:
                        i += 1

                    if len(ready_batch) >= MAX_BATCH_SIZE:
                        break

                if not ready_batch:
                    for image in queue[:]:
                        if now - image["timestamp"] >= (MAX_SINGLE_IMAGE_LATENCY_MS / 1000):
                            ready_batch.append(image)
                            queue.remove(image)

            if ready_batch:
                await classify_batch(ready_batch)

            await asyncio.sleep(0.1)

        # Final flush
        async with session_queues_lock:
            remaining = session_image_queues.get(session_id, [])
            if remaining:
                print(f"[INFO] Flushing {len(remaining)} remaining images for session {session_id}")
                await classify_batch(remaining)

    finally:
        async with session_queues_lock:
            session_image_queues.pop(session_id, None)
        print(f"[INFO] Batch processor finished for session {session_id}")

# Classification Logic
async def classify_batch(batch):
    for item in batch:
        label = random.choice(["accept", "reject"])
        session_id = item["session_id"]
        session = session_state.get(session_id)
        if not session:
            continue

        session[label + "ed"] += 1

        if random.randint(1, 100) <= SAMPLE_PERCENTAGE:
            session["sampled"] += 1
            safe_image_id = sanitize_filename(item['image_id'])
            sample_path = os.path.join(SAMPLE_DIR, f"{safe_image_id}.txt")
            try:
                with open(sample_path, "w") as f:
                    f.write(f"Simulated image ID: {item['image_id']}, Label: {label}")
                session["sampled_images"].append(item["image_id"])
            except Exception as e:
                print(f"[ERROR] Could not save sampled image {safe_image_id}: {e}")

    await asyncio.sleep(0.05)
