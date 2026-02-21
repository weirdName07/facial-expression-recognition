# WebSocket Protocol Specification

The Streaming Aggregation Gateway provides a unified WebSocket endpoint at `ws://localhost:8000/ws/stream` for the frontend client visualization.

## Connection
Client connects to:
`ws://<gateway_host>:<gateway_port>/ws/stream`

## Message Formats

### 1. Client -> Server (Control)
Optional configuration updates from the frontend to the backend.

```json
{
  "type": "config_update",
  "payload": {
    "target_fps": 30,
    "smoothing_factor": 0.8
  }
}
```

### 2. Server -> Client (Inference Results)
The primary broadcast event containing aggregated face data. Emitted roughly at the target FPS (e.g., 30 FPS ~ every 33ms).

```json
{
  "type": "inference_results",
  "payload": {
    "frame_id": 1024,
    "timestamp": 1700000000.123,
    "faces": {
      "face_1_uuid": {
        "bbox": {"x_min": 0.2, "y_min": 0.1, "x_max": 0.4, "y_max": 0.5},
        "landmarks": [{"x": 0.25, "y": 0.25}, ...],
        "tracking_confidence": 0.98,
        
        "expression": {
          "dominant_emotion": "Happy",
          "probabilities": {"Happy": 0.85, "Neutral": 0.1, "Sad": 0.05},
          "confidence": 0.92
        },
        
        "rppg": {
          "bpm": 72.5,
          "waveform": [0.1, -0.2, 0.5, ...], // Latest 50-100 frames of normalized AC signal
          "quality_score": 0.88,
          "calibration_state": "STABLE" // CALIBRATING | STABLE | LOST
        }
      }
    }
  }
}
```

## Latency Expectations
- End-to-end target: < 150ms
- Gateway processing is negligible; latency is dominated by AI inference tasks.
- If inference misses a frame, the gateway relies on Redis Pub/Sub backpressure or skips broadcasting that entity for the current frame.
