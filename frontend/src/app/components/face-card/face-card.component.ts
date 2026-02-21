import { Component, Input } from '@angular/core';

@Component({
   selector: 'app-face-card',
   template: `
    <div class="absolute transition-all duration-300 ease-out z-10"
         [style.left.px]="x" [style.top.px]="y"
         [style.width.px]="width" [style.height.px]="height">
      
      <!-- Warm orange glowing bounding box -->
      <div class="absolute inset-0 rounded-lg pointer-events-none"
           style="border: 2px solid rgba(251, 191, 36, 0.5);
                  box-shadow: 0 0 12px rgba(251, 191, 36, 0.25),
                              inset 0 0 12px rgba(251, 191, 36, 0.08);">
      </div>
      
      <!-- Unified Side Panel: Identity + Gauge + Waveform -->
      <div class="absolute top-0 flex flex-col w-[240px] pointer-events-auto
                  backdrop-blur-xl rounded-2xl overflow-hidden
                  transition-all duration-300 ease-out"
           [class.left-full]="!isPanelOnLeft"
           [class.right-full]="isPanelOnLeft"
           [class.ml-3]="!isPanelOnLeft"
           [class.mr-3]="isPanelOnLeft"
           style="background: rgba(30, 25, 20, 0.80);
                  border: 1px solid rgba(251, 191, 36, 0.15);
                  box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(251, 191, 36, 0.06);">
      
         <!-- Identity Header -->
         <div class="flex justify-between items-center px-4 pt-3 pb-2">
            <span class="text-sm font-semibold text-white tracking-wide">Guest</span>
            <div class="flex items-center gap-1.5">
               <div class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></div>
               <span class="text-[9px] text-amber-300/60 font-mono">{{ (confidence * 100).toFixed(0) }}% CF</span>
            </div>
         </div>
         
         <div class="w-full h-px" style="background: linear-gradient(90deg, transparent, rgba(251,191,36,0.2), transparent);"></div>
         
         <!-- Emotion Wheel -->
         <div class="flex items-center justify-center py-3">
            <app-emotion-wheel 
               [dominantEmotion]="emotion" 
               [confidence]="emotionConfidence"
               [probabilities]="probabilities">
            </app-emotion-wheel>
         </div>
         
         <div class="w-full h-px" style="background: linear-gradient(90deg, transparent, rgba(251,191,36,0.15), transparent);"></div>

         <!-- Heart Rate Waveform -->
         <div class="px-3 py-3" *ngIf="rppg">
            <app-bio-signal-waveform
               [bpm]="rppg.bpm"
               [quality]="rppg.quality_score"
               [waveform]="rppg.waveform"
               [state]="rppg.calibration_state">
            </app-bio-signal-waveform>
         </div>
      </div>
    </div>
  `,
   styles: [`:host { display: block; }`]
})
export class FaceCardComponent {
   @Input() faceId: string = 'unknown';
   @Input() x: number = 0;
   @Input() y: number = 0;
   @Input() width: number = 0;
   @Input() height: number = 0;
   @Input() confidence: number = 0;
   @Input() emotion: string = 'Neutral';
   @Input() emotionConfidence: number = 0;
   @Input() probabilities: Record<string, number> = {};
   @Input() rppg: any = null;
   @Input() screenWidth: number = 1920;

   get isPanelOnLeft(): boolean {
      // If the face is in the right 30% of the screen, flip panel to left
      const panelWidth = 240;
      const margin = 12;
      return (this.x + this.width + panelWidth + margin) > this.screenWidth;
   }
}
