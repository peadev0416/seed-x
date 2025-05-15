# 🌱 Seed-X Seed Classification System

This project simulates a local classification system used in seed sorting machines. It includes:

- A FastAPI backend with real-time batching, classification, sampling, and CSV logging
- A lightweight frontend (HTML/CSS/JS) to visualize session data
- Docker support for easy deployment
- Test script to simulate multiple sorting sessions


## 🚀 Features

- Start, stop, and simulate sorting sessions
- Batch-based classification with latency logic
- Random sampling and image storage
- CSV-based session stats and sampled image logs
- REST API to retrieve session statistics
- Frontend dashboard to view sessions
- Docker-ready


## 🧠 System Architecture

- `FastAPI`: RESTful backend API
- `JavaScript/HTML/CSS`: Frontend UI served via FastAPI
- `asyncio`: Batching and background processing
- `CSV`: Persistent session logging
- `Docker`: Containerized app environment


## 📦 Requirements

- Python 3.10+
- pip (for local dev)
- Docker (optional for containerized setup)


## 📁 Project Structure

```

.
├── app/                      # Backend logic
│   └── main.py
├── frontend/                 # Static HTML frontend
│   ├── index.html
│   ├── script.js
│   └── styles.css
├── sampled_images/          # Auto-generated sampled image logs
├── session_data.csv         # Auto-generated session log
├── tests/
│   └── test_simulation.py   # Load test script
├── requirements.txt
├── Dockerfile
├── .env
├── .env.example
└── README.md

````


## 🛠️ Local Setup

```bash
# Clone the repo and enter the project folder
cd seed-x

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload

# Visit the UI
http://localhost:8000
````


## 🧪 Run Test Simulation

```bash
python tests/test_simulation.py
```

This simulates multiple sorters sending images to the server.


## 🐳 Docker Usage

### 🔨 Build the image

```bash
docker build -t seed-x-app .
```

### ▶️ Run the container

```bash
docker run -p 8000:8000 seed-x-app
```

Then open [http://localhost:8000](http://localhost:8000)


## 🔗 API Endpoints

| Method | Path                           | Description                          |
| ------ | ------------------------------ | ------------------------------------ |
| POST   | `/start-session`               | Start a new sorting session          |
| POST   | `/send-image`                  | Send a seed image for classification |
| POST   | `/stop-session`                | End a sorting session                |
| GET    | `/stats/{session_id}`          | Get stats for a session              |
| GET    | `/sampled-images/{session_id}` | List sampled image IDs               |
| GET    | `/sessions`                    | List all recorded sessions           |


## 🎁 Bonus UI

* Served at `/`
* Visualizes all sessions
* Lets you inspect stats interactively


## 📌 Environment Variables (`.env`)

Example values:

```env
MAX_BATCH_SIZE=8
MAX_SINGLE_IMAGE_LATENCY_MS=300
SAMPLE_PERCENTAGE=10
SAMPLE_DIR=sampled_images
```

