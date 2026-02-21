import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit } from '@angular/core';

@Component({
  selector: 'app-emotion-wheel',
  template: `
    <div class="relative flex flex-col items-center">
      <!-- Radial Gauge -->
      <div class="relative" style="width: 190px; height: 190px;">
        <canvas #wheelCanvas width="380" height="380"
                style="width: 190px; height: 190px;"></canvas>
        <!-- Center Emoji -->
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span class="text-3xl drop-shadow-lg">{{ getDominantEmoji() }}</span>
        </div>
      </div>

      <!-- Dominant Emotion Summary -->
      <div class="flex items-center gap-2.5 mt-2 px-2">
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
    const R = 165; // Outer radius
    const r = 120; // Inner radius
    const mid = (R + r) / 2;
    const band = R - r;

    this.ctx.clearRect(0, 0, w, h);

    const N = this.emotions.length;
    const gap = 0.035; // gap between segments in radians
    const slice = (2 * Math.PI) / N;
    const off = -Math.PI / 2; // start from top

    // ── Background track ──
    for (let i = 0; i < N; i++) {
      const a0 = off + i * slice + gap;
      const a1 = off + (i + 1) * slice - gap;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, mid, a0, a1);
      this.ctx.lineWidth = band;
      this.ctx.lineCap = 'butt';
      this.ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      this.ctx.stroke();
    }

    // ── Tick marks ──
    this.ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    this.ctx.lineWidth = 1;
    const tickCount = 60;
    for (let i = 0; i < tickCount; i++) {
      const a = off + (i / tickCount) * 2 * Math.PI;
      const isMajor = i % (tickCount / N) === 0;
      const t0 = isMajor ? r - 6 : r - 2;
      const t1 = r + 2;
      this.ctx.beginPath();
      this.ctx.moveTo(cx + t0 * Math.cos(a), cy + t0 * Math.sin(a));
      this.ctx.lineTo(cx + t1 * Math.cos(a), cy + t1 * Math.sin(a));
      this.ctx.stroke();
    }

    // ── Filled arcs per emotion ──
    for (let i = 0; i < N; i++) {
      const em = this.emotions[i];
      const prob = this.probabilities?.[em.key] || 0;
      if (prob < 0.01) continue;

      const a0 = off + i * slice + gap;
      const a1 = off + (i + 1) * slice - gap;
      const fillEnd = a0 + (a1 - a0) * Math.min(1, prob);

      // Glow layer
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, mid, a0, fillEnd);
      this.ctx.lineWidth = band + 4;
      this.ctx.lineCap = 'butt';
      this.ctx.strokeStyle = em.color + '30'; // 30 = ~19% alpha
      this.ctx.stroke();

      // Main arc
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, mid, a0, fillEnd);
      this.ctx.lineWidth = band - 6;
      this.ctx.lineCap = 'round';

      // Gradient along arc
      const grd = this.ctx.createLinearGradient(
        cx + R * Math.cos(a0), cy + R * Math.sin(a0),
        cx + R * Math.cos(fillEnd), cy + R * Math.sin(fillEnd)
      );
      grd.addColorStop(0, em.color + 'cc');
      grd.addColorStop(1, em.color);
      this.ctx.strokeStyle = grd;

      // Extra glow on dominant
      if (em.key === this.dominantEmotion) {
        this.ctx.shadowColor = em.color;
        this.ctx.shadowBlur = 16;
      }
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;
    }

    // ── Labels around outside ──
    for (let i = 0; i < N; i++) {
      const em = this.emotions[i];
      const prob = this.probabilities?.[em.key] || 0;
      const a = off + (i + 0.5) * slice;
      const lr = R + 16;
      const lx = cx + lr * Math.cos(a);
      const ly = cy + lr * Math.sin(a);

      this.ctx.save();
      this.ctx.translate(lx, ly);
      const isDom = em.key === this.dominantEmotion;
      this.ctx.fillStyle = isDom ? '#ffffff' : 'rgba(255,255,255,0.35)';
      this.ctx.font = isDom ? 'bold 16px Inter, sans-serif' : '14px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(em.label, 0, 0);
      this.ctx.restore();

      // Percentage markers inside ring
      if (prob > 0.03) {
        const pr = r - 14;
        const px = cx + pr * Math.cos(a);
        const py = cy + pr * Math.sin(a);
        this.ctx.save();
        this.ctx.fillStyle = 'rgba(255,255,255,0.4)';
        this.ctx.font = '12px JetBrains Mono, monospace';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText((prob * 100).toFixed(0) + '%', px, py);
        this.ctx.restore();
      }
    }

    // ── Inner circle ──
    this.ctx.beginPath();
    this.ctx.arc(cx, cy, r - 8, 0, 2 * Math.PI);
    this.ctx.strokeStyle = 'rgba(251,191,36,0.1)';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();
  }
}
