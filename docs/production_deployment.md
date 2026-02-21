# Production Deployment Guide

The production environment should decouple services to run on a Kubernetes cluster with autoscaling GPU nodes.

## Containerization
Each Python service has its own `Dockerfile`. Using lightweight base images (e.g., `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04` for inference nodes and `python:3.10-slim` for the gateway).

## Kubernetes Architecture
1. **Redis Cluster / Redis Streams**: Use a managed Redis service (e.g., AWS ElastiCache) for highly available PubSub broker.
2. **API Gateway Nodes**: CPU-only stateless pods running FastAPI, scaled out behind a Load Balancer.
3. **Inference Workers**: Deployed as stateless pods on GPU-enabled nodes (e.g., AWS g4dn.xlarge).
   - Use KEDA (Kubernetes Event-driven Autoscaling) to scale these worker pods based on the Redis message queue backlog.
4. **Frontend**: The Angular app should be compiled statically (`ng build --configuration production`) and served via a CDN (e.g., Cloudfront, Vercel) or Nginx ingress.

## Security & Privacy Policies
- **Data Retention**: By default, raw video frames are **NOT** stored. Only anonymous IDs and derived telemetry are retained optionally.
- **WebSocket Security**: In production, use `wss://` with proper JWT authentication attached to the initial connection request.
- **Encryption**: Implement Let's Encrypt SSL/TLS for all external ingresses.

## Failure Fallbacks
- **Graceful Degradation**: If an AI service goes down, the gateway should send a `{"status": "degraded"}` event to the frontend, which will render a skeleton/calibration state instead of crashing.
- **Circuit Breakers**: Use tools like Redis Sentinel to handle broker failover.
