# 🎓 Knowledge Transfer (KT) Documentation

This document provides a comprehensive guide to the project structure, the utility of each directory, and the purpose of individual files.

## 📂 Project Root
- `backend/`: Core AI logic, inference pipeline, and WebSocket gateway.
- `frontend/`: Angular dashboard for real-time visualization.
- `docs/`: Technical documentation, roadmaps, and protocol specs.
- `run_all.ps1`: Automation script to launch both backend and frontend simultaneously.
- `README.md`: High-level entry point with architecture and setup instructions.
- `docker-compose.yml`: (Optional) Infrastructure orchestration for Redis/services.
- `yolo11n.pt`: (Redundant - Cleaned) Base YOLO weights.

---

## 🐍 Backend Architecture (`/backend`)

### 🛰️ Gateway (`/backend/gateway`)
- `main.py`: FastAPI/Uvicorn entry point. Manages WebSocket connections and broadcasts inference results from Redis.

### 🧠 Services (`/backend/services`)
#### 🎭 Expression Recognition (`/backend/services/expression_recognition`)
- `emotion_classifier.py`: Implements the `HSEmotion` model. Handles preprocessing and RAF-DB optimized classification.
- `main.py`: (Legacy) Standalone service entry point.

#### 🆔 Face Tracking (`/backend/services/face_tracking`)
- `face_detector.py`: YOLOv8-face implementation. Handles detection, tracking (Centroid), and ROI cropping.
- `face_recognizer.py`: Vector-based identity management. Includes the embedding database and age/gender smoothing logic.

#### 💓 Heart Rate (`/backend/services/heart_rate`)
- `rppg_engine.py`: Remote Photoplethysmography implementation. Extracts BVP signals and calculates BPM via FFT.

### 🤝 Shared (`/backend/shared`)
- `redis_client.py`: Centralized Redis wrapper for IPC (Inter-Process Communication).

### ⚙️ Root Backend Files
- `run_all_services.py`: The **Unified Runner**. Orchestrates all AI models, camera capture, and data publishing in a high-performance loop.
- `requirements.txt`: Python dependency manifest.

---

## 🎨 Frontend Architecture (`/frontend`)

### 🧱 Core Components (`/frontend/src/app/components`)
- `face-card/`: The primary UI element overlaid on faces. Displays Identity, Demographics, and Bio-signals.
- `emotion-wheel/`: D3-inspired SVG gauge for visualizing expression probabilities.
- `bio-signal-waveform/`: Canvas-based real-time heart rate pulse graph.
- `dashboard/`: Main layout and stream handling logic.

### 🔌 Services (`/frontend/src/app/services`)
- `websocket.service.ts`: Manages the binary/JSON stream from the backend.
- `stream.service.ts`: Handles camera access and start/stop signals.

---

## 📜 Documentation (`/docs`)
- `KT_DOCUMENTATION.md`: This file.
- `websocket_protocol.md`: Technical spec for the binary + JSON stream format.
- `performance_optimization.md`: Guide to the caching and throttling mechanics.
- `dev_run_instructions.md`: Detailed environment setup guide.

---

## 💡 Key Design Patterns
1. **Producer-Consumer**: The `CameraThread` produces frames; the `inference_loop` consumes them.
2. **IPC via Redis**: Enables decoupled scaling. The AI runner is separate from the WebSocket gateway.
3. **Throttled Analytics**: Heavy models (Face ID) run every 30 frames; fast models (Emotion) run every frame.
4. **Vector-DB**: In-memory caching of embeddings for O(1) identity lookups.

---
*For internal developer use only.*
