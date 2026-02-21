import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit } from '@angular/core';

@Component({
  selector: 'app-emotion-wheel',
  template: `
    <div class="relative flex flex-col items-center">
      <!-- Radial Gauge -->
      <div class="relative" style="width: 200px; height: 200px;">
        <canvas #wheelCanvas width="400" height="400"
                style="width: 200px; height: 200px;"></canvas>
        <!-- Center Emoji -->
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span class="text-3xl drop-shadow-lg">{{ getDominantEmoji() }}</span>
        </div>
      </div>

      <!-- Dominant Emotion Summary -->
      <div class="flex items-center gap-2.5 mt-1.5">
        <span class="text-xl">{{ getDominantEmoji() }}</span>
        <div class="flex flex-col leading-tight">
          <span class="text-white font-bold text-base">{{ dominantEmotion }}</span>
          <span class="text-amber-300/80 text-lg font-mono font-bold">{{ (confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
  `,
  styles: [`:host { display: block; }`]
})
export class EmotionWheelComponent implements AfterViewInit, OnChanges {
  @Input() dominantEmotion: string = 'Neutral';
  @Input() confidence: number = 0;
  @Input() probabilities: Record<string, number> = {};

  @ViewChild('wheelCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;
  private ctx!: CanvasRenderingContext2D | null;

  private emotions = [
    { label: 'Happy', key: 'Happy', color: '#fbbf24', emoji: '😊' },
    { label: 'Surprise', key: 'Surprise', color: '#c084fc', emoji: '😲' },
    { label: 'Fear', key: 'Fear', color: '#818cf8', emoji: '😨' },
    { label: 'Sad', key: 'Sad', color: '#60a5fa', emoji: '😢' },
    { label: 'Disgust', key: 'Disgust', color: '#34d399', emoji: '🤢' },
    { label: 'Angry', key: 'Angry', color: '#fb7185', emoji: '😠' },
    { label: 'Neutral', key: 'Neutral', color: '#94a3b8', emoji: '😐' },
  ];

  ngAfterViewInit() {
    this.ctx = this.canvasRef?.nativeElement.getContext('2d');
    this.draw();
  }

  ngOnChanges(_: SimpleChanges) {
    if (this.ctx) this.draw();
  }

  getDominantEmoji(): string {
    return this.emotions.find(e => e.key === this.dominantEmotion)?.emoji || '😐';
  }

  private draw() {
    if (!this.ctx) return;
    const c = this.canvasRef.nativeElement;
    const w = c.width, h = c.height;
    const cx = w / 2, cy = h / 2;

    // Ring dimensions — thin and clean
    const outerR = 155;
    const innerR = 130;
    const midR = (outerR + innerR) / 2;
    const arcWidth = outerR - innerR;  // = 25px, thin band

    this.ctx.clearRect(0, 0, w, h);

    const N = this.emotions.length;
    const gap = 0.05;  // radians between segments
    const slice = (2 * Math.PI) / N;
    const startAngle = -Math.PI / 2;  // top

    // ── Background track segments ──
    for (let i = 0; i < N; i++) {
      const a0 = startAngle + i * slice + gap / 2;
      const a1 = startAngle + (i + 1) * slice - gap / 2;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, midR, a0, a1);
      this.ctx.lineWidth = arcWidth;
      this.ctx.lineCap = 'butt';
      this.ctx.strokeStyle = 'rgba(255,255,255,0.07)';
      this.ctx.stroke();
    }

    // ── Fine tick marks ──
    this.ctx.strokeStyle = 'rgba(255,255,255,0.10)';
    this.ctx.lineWidth = 1;
    for (let i = 0; i < 70; i++) {
      const a = startAngle + (i / 70) * 2 * Math.PI;
      const r0 = innerR - 2;
      const r1 = innerR + 4;
      this.ctx.beginPath();
      this.ctx.moveTo(cx + r0 * Math.cos(a), cy + r0 * Math.sin(a));
      this.ctx.lineTo(cx + r1 * Math.cos(a), cy + r1 * Math.sin(a));
      this.ctx.stroke();
    }

    // ── Filled probability arcs ──
    for (let i = 0; i < N; i++) {
      const em = this.emotions[i];
      const prob = this.probabilities?.[em.key] || 0;
      if (prob < 0.01) continue;

      const a0 = startAngle + i * slice + gap / 2;
      const a1 = startAngle + (i + 1) * slice - gap / 2;
      const fillEnd = a0 + (a1 - a0) * Math.min(1, prob);

      // Outer glow
      if (em.key === this.dominantEmotion) {
        this.ctx.beginPath();
        this.ctx.arc(cx, cy, midR, a0, fillEnd);
        this.ctx.lineWidth = arcWidth + 6;
        this.ctx.lineCap = 'butt';
        this.ctx.strokeStyle = em.color + '25';
        this.ctx.shadowColor = em.color;
        this.ctx.shadowBlur = 12;
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;
      }

      // Main filled arc
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, midR, a0, fillEnd);
      this.ctx.lineWidth = arcWidth - 4;
      this.ctx.lineCap = 'round';
      this.ctx.strokeStyle = em.color;
      this.ctx.stroke();
    }

    // ── Labels ──
    for (let i = 0; i < N; i++) {
      const em = this.emotions[i];
      const prob = this.probabilities?.[em.key] || 0;
      const midAngle = startAngle + (i + 0.5) * slice;
      const isDom = em.key === this.dominantEmotion;

      // Emotion label outside ring
      const labelR = outerR + 22;
      const lx = cx + labelR * Math.cos(midAngle);
      const ly = cy + labelR * Math.sin(midAngle);
      this.ctx.save();
      this.ctx.fillStyle = isDom ? '#ffffff' : 'rgba(255,255,255,0.4)';
      this.ctx.font = isDom ? 'bold 17px Inter, sans-serif' : '14px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(em.label, lx, ly);
      this.ctx.restore();

      // Percentage inside ring
      if (prob > 0.03) {
        const pctR = innerR - 16;
        const px = cx + pctR * Math.cos(midAngle);
        const py = cy + pctR * Math.sin(midAngle);
        this.ctx.save();
        this.ctx.fillStyle = isDom ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.3)';
        this.ctx.font = '13px JetBrains Mono, monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText((prob * 100).toFixed(0) + '%', px, py);
        this.ctx.restore();
      }
    }

    // ── Inner ring border ──
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, innerR - 8, 0, 2 * Math.PI);
    this.ctx.strokeStyle = 'rgba(251,191,36,0.08)';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();
  }
}
