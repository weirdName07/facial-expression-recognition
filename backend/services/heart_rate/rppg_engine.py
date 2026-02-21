"""
rPPG Engine — Remote Photoplethysmography for Heart Rate Estimation.
Extracts blood volume pulse (BVP) signal from facial Green channel intensity.
"""

import numpy as np
import time
import logging
from collections import deque
from scipy.signal import butter, filtfilt

log = logging.getLogger(__name__)

class RPPGEngine:
    def __init__(self, buffer_size: int = 150, fs: float = 30.0):
        """
        buffer_size: Number of frames to keep for signal processing (e.g. 5 sec @ 30fps)
        fs: Sampling frequency (expected FPS)
        """
        self.fs = fs
        self.buffer_size = buffer_size
        self.signal_buffer = deque(maxlen=buffer_size)
        self.times = deque(maxlen=buffer_size)
        self.current_bpm = 0.0
        self.is_calibrated = False

    def _butter_bandpass(self, lowcut, highcut, fs, order=5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return b, a

    def _apply_filter(self, data):
        # Human heart rate is typically between 45-180 BPM (0.75 - 3.0 Hz)
        try:
            b, a = self._butter_bandpass(0.75, 3.0, self.fs, order=2)
            y = filtfilt(b, a, data)
            return y
        except Exception:
            return data

    def update(self, face_crop: np.ndarray) -> float:
        """
        Updates engine with a new face crop.
        Returns the current estimated BPM.
        """
        if face_crop is None or face_crop.size == 0:
            return self.current_bpm, 0.0

        # ROI: Forehead or Malar (cheeks) regions are best. 
        # For simplicity, we use the center 60% of the face ROI.
        h, w = face_crop.shape[:2]
        roi = face_crop[int(h*0.2):int(h*0.5), int(w*0.2):int(w*0.8)]
        
        if roi.size == 0:
            return self.current_bpm, 0.0

        # Extract Green channel mean (G is usually strongest for BVP)
        # BGR format → Index 1 is Green
        green_mean = np.mean(roi[:, :, 1])
        
        self.signal_buffer.append(green_mean)
        self.times.append(time.time())

        if len(self.signal_buffer) < self.buffer_size:
            # Not enough data for FFT yet
            return self.current_bpm, 0.0

        # Signal Processing Phase
        signal = np.array(self.signal_buffer)
        
        # 1. Detrend (remove slow drift)
        signal = signal - np.mean(signal)
        
        # 2. Filter (Bandpass 0.75-3Hz)
        filtered = self._apply_filter(signal)
        
        # 3. FFT to find dominant frequency
        L = len(filtered)
        freqs = np.fft.fftfreq(L, 1.0/self.fs)
        fft_vals = np.abs(np.fft.fft(filtered))
        
        # Look only at positive frequencies in the HR range
        mask = (freqs >= 0.75) & (freqs <= 3.0)
        relevant_freqs = freqs[mask]
        relevant_fft = fft_vals[mask]
        
        if len(relevant_fft) > 0:
            max_idx = np.argmax(relevant_fft)
            best_freq = relevant_freqs[max_idx]
            
            # Simple SNR-based quality score
            peak_val = relevant_fft[max_idx]
            mean_val = np.mean(relevant_fft)
            quality = min(1.0, peak_val / (mean_val * 5.0 + 1e-6))
            
            bpm = best_freq * 60.0
            
            # Simple Smoothing (EMA)
            if self.current_bpm == 0:
                self.current_bpm = bpm
            else:
                self.current_bpm = 0.9 * self.current_bpm + 0.1 * bpm
                
        return round(self.current_bpm, 1), round(quality, 2)

    def get_state(self) -> dict:
        """Returns calibration metadata for the UI."""
        progress = len(self.signal_buffer) / self.buffer_size
        return {
            "is_active": progress >= 1.0,
            "progress": round(progress, 2),
            "state_text": "ACTIVE" if progress >= 1.0 else "CALIBRATING"
        }

    def get_waveform(self, window_size: int = 60) -> list[float]:
        """
        Returns a rolling window of normalized signal points for the UI.
        """
        if len(self.signal_buffer) < 2:
            return []
            
        # Get latest window
        signal = list(self.signal_buffer)[-window_size:]
        
        # Normalize for visualization (-1 to 1 range approx)
        signal_np = np.array(signal)
        avg = np.mean(signal_np)
        std = np.std(signal_np) + 1e-6
        normalized = (signal_np - avg) / std
        
        # Clip to avoid extreme spikes and round for JSON
        return [round(float(v), 3) for v in np.clip(normalized, -3, 3)]
