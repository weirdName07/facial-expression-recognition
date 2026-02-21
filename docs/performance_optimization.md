# Performance Optimization Checklist

## Backend Optimization
- [ ] **Batch Inference**: Use Redis Streams to accumulate frames and perform batch inference on GPUs where appropriate (instead of latency-bound batch size=1).
- [ ] **ONNX Runtime / TensorRT**: Convert YOLOv11 and AffectNet PyTorch models to ONNX or TensorRT for a 2x-4x inference speedup.
- [ ] **Frame Dropping Strategy**: Ensure the API Gateway actively drops stale frames if the processing queue depth exceeds an acceptable latency threshold (< 150ms).
- [ ] **Half-Precision (FP16)**: Run AI models in FP16 precision instead of FP32.
- [ ] **Asynchronous I/O**: Ensure all Redis PubSub calls and WebSocket broadcasts use `asyncio` to prevent blocking the event loop.

## Frontend Optimization
- [ ] **OffscreenCanvas**: Use Web Workers to draw the `FaceOverlayCanvas` to avoid blocking the main thread, keeping Angular bindings fast.
- [ ] **RequestAnimationFrame (rAF)**: All particle effects and visual smoothings must be tied to `requestAnimationFrame`.
- [ ] **Throttling UI Updates**: If backend emits at 30 FPS but UI is lagging, throttle the RxJS WebSocket stream to 15-20 FPS using RxJS `sampleTime()`.
- [ ] **Hardware Acceleration**: Use CSS `transform` and `opacity` for animations (instead of `top`/`left`) to trigger GPU compositing in the browser. 
