import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { WebsocketService, InferenceData } from './services/websocket.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'Facial Expression Platform';
  isConnected = false;

  faces: Record<string, any> = {};
  currentFrame: string = '';

  // Dynamic viewport dimensions for scaling normalised coords
  viewportWidth: number = window.innerWidth;
  viewportHeight: number = window.innerHeight;

  backendLatencyMs: number = 0;
  fps: number = 0;
  private lastFrameTimestamp: number = 0;

  sub: Subscription = new Subscription();
  cameraStarted: boolean = false;

  constructor(private wsService: WebsocketService) { }

  @HostListener('window:resize')
  onResize() {
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;
  }

  ngOnInit() {
    this.sub.add(this.wsService.connectionStatus$.subscribe(status => {
      this.isConnected = status;
    }));

    this.sub.add(this.wsService.inferenceStream$.subscribe(data => {
      this.processInferenceData(data);
    }));
  }

  async startSession() {
    try {
      // Request permission in browser first (even though backend handles capture, 
      // this ensures the user grants privacy permission and we know hardware exists)
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      // Stop the stream immediately, backend will handle the real capture
      stream.getTracks().forEach(track => track.stop());

      this.cameraStarted = true;
      this.wsService.sendMessage({ type: 'START_INF' });
    } catch (err) {
      console.error('Camera permission denied or not found:', err);
      alert('Camera access is required for real-time analysis.');
    }
  }

  private processInferenceData(data: InferenceData) {
    if (!data) return;

    this.faces = data.faces || {};
    if (data.frame) {
      this.currentFrame = data.frame;
    }

    const now = performance.now();
    if (this.lastFrameTimestamp > 0) {
      const delta = now - this.lastFrameTimestamp;
      this.fps = 1000 / delta;
    }
    this.lastFrameTimestamp = now;

    const serverTime = data.timestamp * 1000;
    const systemTime = Date.now();
    this.backendLatencyMs = Math.max(0, systemTime - serverTime);
  }

  objectKeys(obj: any): string[] {
    return Object.keys(obj || {});
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }
}
