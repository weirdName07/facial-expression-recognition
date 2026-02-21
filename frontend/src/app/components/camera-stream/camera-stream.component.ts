import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';

@Component({
  selector: 'app-camera-stream',
  template: `
    <div class="w-full h-full bg-black">
      <img *ngIf="frameSrc" [src]="frameSrc"
           class="w-full h-full object-cover"
           style="transform: scaleX(-1);"
           alt="Camera Feed" />
      <div *ngIf="!frameSrc" class="w-full h-full flex items-center justify-center">
        <div class="flex flex-col items-center gap-3">
          <div class="w-6 h-6 border-2 border-amber-400/40 border-t-amber-400 rounded-full animate-spin"></div>
          <span class="text-xs font-mono text-white/40 tracking-widest">AWAITING FEED</span>
        </div>
      </div>
    </div>
  `,
  styles: [`:host { display: block; width: 100%; height: 100%; position: relative; }`]
})
export class CameraStreamComponent implements OnChanges {
  @Input() frameBase64: string = '';
  frameSrc: string = '';

  ngOnChanges(changes: SimpleChanges) {
    if (changes['frameBase64'] && this.frameBase64) {
      this.frameSrc = 'data:image/jpeg;base64,' + this.frameBase64;
    }
  }
}
