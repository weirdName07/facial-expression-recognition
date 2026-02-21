# Future Roadmap

## V1 - Core Real-Time AI
- Face Tracking with stable generic IDs
- Expression Recognition
- Basic Heart Rate extraction (rPPG)
- Glassmorphism HUD Dashboard

## V2 - Engagement & Attention Metrics
- **Gaze Estimation**: Adding a lightweight model to predict eye pitch/yaw vectors to determine screen attention.
- **Stress Inference**: Combining rPPG HRV (Heart Rate Variability), blink rate, and micro-expressions to infer long-term cognitive load and stress.

## V3 - Scale & Edge
- **WebAssembly (WASM)**: Running the YOLOv11 Face model directly in the browser via ONNX Runtime Web to reduce server costs and improve privacy.
- **Edge Deployment**: Compiling the backend stack to be deployed on Jetson Nano / Orin devices for offline use-cases.

## Observability Implementation
- Integrate Prometheus exporters in the FastAPI Gateway.
- Build Grafana templates visualizing real-time HR MAE, emotion F1 consistency over time vs lighting variations.
