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

  // Dynamic viewport dimensions for scaling normalised coords
  viewportWidth: number = window.innerWidth;
  viewportHeight: number = window.innerHeight;

  backendLatencyMs: number = 0;
  fps: number = 0;
  private lastFrameTimestamp: number = 0;

  private sub: Subscription = new Subscription();

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

  private processInferenceData(data: InferenceData) {
    if (!data || !data.faces) return;

    this.faces = data.faces;

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
