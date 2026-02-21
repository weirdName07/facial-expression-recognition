# Development Run Instructions

Follow these steps to spin up the entire platform locally.

## Prerequisite
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

## 1. Start Infrastructure (Redis)
From the project root:
```bash
docker-compose up -d redis
```

## 2. Start Backend Microservices
Open 4 separate terminal windows/tabs, activate the virtual environment in each, and run the services:

### Terminal 1 - API Gateway
```bash
source venv/bin/activate  # Or .\venv\Scripts\Activate.ps1 on Windows
python -m backend.gateway.main
# Runs on port 8000
```

### Terminal 2 - Face Tracking
```bash
source venv/bin/activate
python -m backend.services.face_tracking.main
# Runs on port 8001
```

### Terminal 3 - Expression Recognition
```bash
source venv/bin/activate
python -m backend.services.expression_recognition.main
# Runs on port 8002
```

### Terminal 4 - rPPG Heart Rate
```bash
source venv/bin/activate
python -m backend.services.rppg_heart_rate.main
# Runs on port 8003
```

## 3. Start Frontend Dashboard
Open a new terminal:
```bash
cd frontend
npm install
npm run start
# Runs on http://localhost:4200
```
