import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit } from '@angular/core';

@Component({
    selector: 'app-bio-signal-waveform',
    template: `
    <div class="flex flex-col gap-1.5 w-full">
       <div class="flex justify-between items-end">
          <div class="flex items-center gap-1.5">
             <svg class="w-3 h-3 text-amber-400 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
               <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd" />
             </svg>
             <span class="text-[9px] font-medium tracking-wider text-white/60">HR (rPPG)</span>
          </div>
          <div class="flex items-baseline gap-0.5">
             <span class="text-lg font-bold font-mono text-amber-400">
               {{ state === 'CALIBRATING' ? '--' : bpm.toFixed(0) }}
             </span>
             <span class="text-[8px] text-white/35 font-mono">BPM</span>
          </div>
       </div>
       
       <div class="relative w-full overflow-hidden rounded-md" style="height: 48px;">
         <canvas #waveCanvas class="absolute inset-0 w-full h-full"></canvas>
         <div *ngIf="state === 'CALIBRATING'" 
              class="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <span class="text-[9px] font-mono tracking-widest text-white/50">Calculating...</span>
         </div>
       </div>
    </div>
  `,
    styles: [`:host { display: block; }`]
})
export class BioSignalWaveformComponent implements AfterViewInit, OnChanges {
    @Input() bpm: number = 0;
    @Input() quality: number = 0;
    @Input() waveform: number[] = [];
    @Input() state: string = 'CALIBRATING';

    @ViewChild('waveCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    private ctx!: CanvasRenderingContext2D | null;

    ngAfterViewInit() {
        if (this.canvasRef) {
            this.canvasRef.nativeElement.width = 480;
            this.canvasRef.nativeElement.height = 96;
            this.ctx = this.canvasRef.nativeElement.getContext('2d');
            this.draw();
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['waveform'] && this.ctx) this.draw();
    }

    private draw() {
        if (!this.ctx || !this.waveform || this.waveform.length === 0) return;

        const w = this.canvasRef.nativeElement.width;
        const h = this.canvasRef.nativeElement.height;
        const midY = h * 0.55;

        this.ctx.clearRect(0, 0, w, h);

        // Dark background
        this.ctx.fillStyle = 'rgba(15, 10, 5, 0.5)';
        this.ctx.fillRect(0, 0, w, h);

        // Faint baseline
        this.ctx.strokeStyle = 'rgba(251, 191, 36, 0.06)';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(0, midY);
        this.ctx.lineTo(w, midY);
        this.ctx.stroke();

        // Convert waveform data to smooth ECG-like curve using cardinal spline
        const scaleY = h / 3;
        const stepX = w / (this.waveform.length - 1);
        const pts: number[] = [];
        for (let i = 0; i < this.waveform.length; i++) {
            pts.push(i * stepX);
            pts.push(Math.max(4, Math.min(h - 4, midY - this.waveform[i] * scaleY)));
        }

        // Draw gradient fill under the curve
        this.ctx.beginPath();
        this.drawCardinalSpline(pts, 0.4);
        this.ctx.lineTo(w, h);
        this.ctx.lineTo(0, h);
        this.ctx.closePath();
        const fillGrd = this.ctx.createLinearGradient(0, 0, 0, h);
        fillGrd.addColorStop(0, 'rgba(251, 191, 36, 0.15)');
        fillGrd.addColorStop(0.6, 'rgba(217, 119, 6, 0.05)');
        fillGrd.addColorStop(1, 'rgba(0, 0, 0, 0)');
        this.ctx.fillStyle = fillGrd;
        this.ctx.fill();

        // Outer glow pass
        this.ctx.beginPath();
        this.drawCardinalSpline(pts, 0.4);
        this.ctx.strokeStyle = 'rgba(251, 191, 36, 0.2)';
        this.ctx.lineWidth = 5;
        this.ctx.lineJoin = 'round';
        this.ctx.lineCap = 'round';
        this.ctx.shadowColor = '#fbbf24';
        this.ctx.shadowBlur = 10;
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Crisp main line
        this.ctx.beginPath();
        this.drawCardinalSpline(pts, 0.4);
        this.ctx.strokeStyle = '#fbbf24';
        this.ctx.lineWidth = 2;
        this.ctx.lineJoin = 'round';
        this.ctx.lineCap = 'round';
        this.ctx.stroke();

        // Scanning dot at end
        const lastX = pts[pts.length - 2];
        const lastY = pts[pts.length - 1];
        this.ctx.beginPath();
        this.ctx.arc(lastX, lastY, 4, 0, 2 * Math.PI);
        this.ctx.fillStyle = '#fde68a';
        this.ctx.shadowColor = '#fbbf24';
        this.ctx.shadowBlur = 14;
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
    }

    /** Draw a smooth cardinal spline through the given flat [x,y,x,y,...] array */
    private drawCardinalSpline(pts: number[], tension: number) {
        if (!this.ctx || pts.length < 4) return;
        this.ctx.moveTo(pts[0], pts[1]);

        const n = pts.length;
        for (let i = 0; i < n - 2; i += 2) {
            const x0 = i > 0 ? pts[i - 2] : pts[i];
            const y0 = i > 0 ? pts[i - 1] : pts[i + 1];
            const x1 = pts[i], y1 = pts[i + 1];
            const x2 = pts[i + 2], y2 = pts[i + 3];
            const x3 = i + 4 < n ? pts[i + 4] : x2;
            const y3 = i + 5 < n ? pts[i + 5] : y2;

            const cp1x = x1 + (x2 - x0) * tension / 3;
            const cp1y = y1 + (y2 - y0) * tension / 3;
            const cp2x = x2 - (x3 - x1) * tension / 3;
            const cp2y = y2 - (y3 - y1) * tension / 3;

            this.ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, x2, y2);
        }
    }
}
