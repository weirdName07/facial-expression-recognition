import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';

@Component({
  selector: 'app-camera-stream',
  template: `
    <div class="w-full h-full bg-black">
      <video #videoElement autoplay playsinline muted
             class="w-full h-full object-cover"
             style="transform: scaleX(-1);"></video>
    </div>
  `,
  styles: [`:host { display: block; width: 100%; height: 100%; position: relative; }`]
})
export class CameraStreamComponent implements OnInit {
  @ViewChild('videoElement', { static: true }) videoElement!: ElementRef<HTMLVideoElement>;

  ngOnInit() {
    this.initCamera();
  }

  private async initCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 3840 },
          height: { ideal: 2160 },
          frameRate: { ideal: 30 },
          facingMode: 'user'
        }
      });
      this.videoElement.nativeElement.srcObject = stream;
    } catch (err) {
      console.error("Error accessing camera:", err);
    }
  }
}
