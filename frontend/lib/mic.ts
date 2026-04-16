'use client';

// AudioWorklet processor registered as a Blob URL — avoids serving a separate JS file.
const WORKLET_SRC = `
class Pcm16Processor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buf = new Int16Array(0);
    this._flushAt = 640 * 5; // ~200ms at 16kHz
  }
  _f32ToI16(f32) {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      const s = Math.max(-1, Math.min(1, f32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const pcm = this._f32ToI16(input[0]);
    const merged = new Int16Array(this._buf.length + pcm.length);
    merged.set(this._buf);
    merged.set(pcm, this._buf.length);
    this._buf = merged;
    if (this._buf.length >= this._flushAt) {
      this.port.postMessage(this._buf.buffer, [this._buf.buffer]);
      this._buf = new Int16Array(0);
    }
    return true;
  }
}
registerProcessor('pcm16-processor', Pcm16Processor);
`;

export type MicStream = {
  stop: () => Promise<void>;
  isRunning: () => boolean;
  /** Returns normalized amplitudes [0..1] over `bins` bands. Safe to call from rAF. */
  getLevels: (bins?: number) => Float32Array;
};

/**
 * Capture mic as raw int16 PCM at 16 kHz mono AND expose a frequency analyser
 * so the UI can draw a waveform/spectrum.
 */
export async function startMic(onChunk: (chunk: ArrayBuffer) => void): Promise<MicStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      sampleRate: 16000,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
    video: false,
  });

  const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
  const ctx: AudioContext = new AudioCtx({ sampleRate: 16000 });

  const blob = new Blob([WORKLET_SRC], { type: 'application/javascript' });
  const url = URL.createObjectURL(blob);
  await ctx.audioWorklet.addModule(url);
  URL.revokeObjectURL(url);

  const source = ctx.createMediaStreamSource(stream);

  // Analyser for visualization — taps off the same source.
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.6;
  source.connect(analyser);

  const worklet = new AudioWorkletNode(ctx, 'pcm16-processor');
  worklet.port.onmessage = (e) => onChunk(e.data as ArrayBuffer);
  source.connect(worklet);

  const freq = new Uint8Array(analyser.frequencyBinCount);
  let stopped = false;

  return {
    isRunning: () => !stopped,
    getLevels: (bins = 32) => {
      if (stopped) return new Float32Array(bins);
      analyser.getByteFrequencyData(freq);
      const out = new Float32Array(bins);
      const per = Math.floor(freq.length / bins);
      for (let i = 0; i < bins; i++) {
        let sum = 0;
        for (let j = 0; j < per; j++) sum += freq[i * per + j];
        out[i] = per ? sum / per / 255 : 0;
      }
      return out;
    },
    async stop() {
      if (stopped) return;
      stopped = true;
      try {
        worklet.disconnect();
        analyser.disconnect();
        source.disconnect();
      } catch {}
      stream.getTracks().forEach((t) => t.stop());
      try {
        await ctx.close();
      } catch {}
    },
  };
}
