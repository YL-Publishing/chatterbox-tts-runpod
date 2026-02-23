"""
RunPod Serverless Handler for Chatterbox TTS.

Loads the Chatterbox model once at cold start, then handles TTS requests
returning base64-encoded WAV audio.

GPU: RTX 4090 (24GB) or similar — Chatterbox needs ~4-6GB VRAM.
Model: resemble-ai/chatterbox (500M params)

Input (single):
    {"text": "Hello world", "voice": "narrator", "exaggeration": 0.6, "cfg_weight": 0.5}

Input (batch):
    {"segments": [{"id": "N1", "text": "...", "voice": "narrator", "exaggeration": 0.7}, ...]}

Output (single):
    {"audio_base64": "<base64 WAV>", "duration_s": 2.3, "gen_time_s": 1.1}

Output (batch):
    {"results": [{"id": "N1", "audio_base64": "...", ...}, ...]}
"""

import runpod
import base64
import io
import time
import os
import traceback

import torch
import torchaudio as ta

# ── Model loading (once at cold start) ──────────────────────────────

print("=" * 60)
print("Chatterbox TTS — RunPod Serverless Worker")
print("=" * 60)

load_start = time.time()
LOAD_ERROR = None
MODEL = None
VOICES_DIR = "/voices"
MAX_TEXT_LENGTH = 4000

try:
    print("Loading Chatterbox TTS model...")
    from chatterbox.tts import ChatterboxTTS
    MODEL = ChatterboxTTS.from_pretrained(device="cuda")
    print(f"Chatterbox loaded on cuda, sample_rate={MODEL.sr}")
    print(f"Model ready in {time.time() - load_start:.1f}s")
except Exception as e:
    LOAD_ERROR = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    print(f"FATAL: {LOAD_ERROR}")


# ── Voice resolution ────────────────────────────────────────────────

def get_voice_path(voice_name: str):
    """Resolve voice name to a reference audio file, or None for default."""
    if not voice_name or voice_name in ("default", "narrator"):
        return None

    for ext in (".wav", ".mp3", ".flac"):
        path = os.path.join(VOICES_DIR, f"{voice_name}{ext}")
        if os.path.exists(path):
            return path
    return None


# ── Single generation ───────────────────────────────────────────────

def generate_one(text: str, voice: str = "narrator",
                 exaggeration: float = 0.6, cfg_weight: float = 0.5) -> dict:
    """Generate WAV audio for a single text segment."""
    t0 = time.time()

    voice_path = get_voice_path(voice)

    kwargs = {
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight,
    }
    if voice_path:
        kwargs["audio_prompt_path"] = voice_path

    wav = MODEL.generate(text, **kwargs)
    gen_time = time.time() - t0

    # Encode to WAV bytes
    buffer = io.BytesIO()
    ta.save(buffer, wav, MODEL.sr, format="wav")
    buffer.seek(0)
    wav_bytes = buffer.read()

    audio_duration = max(0, (len(wav_bytes) - 44)) / (MODEL.sr * 2)

    return {
        "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
        "format": "wav",
        "sample_rate": MODEL.sr,
        "duration_s": round(audio_duration, 2),
        "gen_time_s": round(gen_time, 2),
        "voice": voice,
        "text_length": len(text),
    }


# ── Handler ─────────────────────────────────────────────────────────

def handler(event):
    if MODEL is None:
        return {"error": f"Model failed to load: {LOAD_ERROR}"}

    try:
        inp = event.get("input", {})

        # ── Batch mode ──
        if "segments" in inp:
            segments = inp["segments"]
            results = []
            total_start = time.time()

            for seg in segments:
                seg_id = seg.get("id", "unknown")
                text = seg.get("text", "").strip()
                voice = seg.get("voice", "narrator")
                exagg = float(seg.get("exaggeration", 0.6))
                cfg = float(seg.get("cfg_weight", 0.5))

                if not text:
                    results.append({"id": seg_id, "error": "empty text"})
                    continue
                if len(text) > MAX_TEXT_LENGTH:
                    text = text[:MAX_TEXT_LENGTH]

                try:
                    result = generate_one(text, voice, exagg, cfg)
                    result["id"] = seg_id
                    results.append(result)
                    print(f"  {seg_id}: {result['duration_s']:.1f}s audio in {result['gen_time_s']:.1f}s")
                except Exception as e:
                    results.append({"id": seg_id, "error": str(e)})
                    print(f"  {seg_id}: ERROR - {e}")
                    traceback.print_exc()

            total_time = time.time() - total_start
            return {
                "results": results,
                "total_segments": len(results),
                "total_time_s": round(total_time, 2),
            }

        # ── Single mode ──
        text = inp.get("text", "").strip()
        if not text:
            return {"error": "No text provided"}
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]

        voice = inp.get("voice", "narrator")
        exaggeration = float(inp.get("exaggeration", 0.6))
        cfg_weight = float(inp.get("cfg_weight", 0.5))

        return generate_one(text, voice, exaggeration, cfg_weight)

    except Exception as e:
        tb = traceback.format_exc()
        print(f"Handler error: {e}\n{tb}")
        return {"error": str(e), "traceback": tb}


# ── Entry point ─────────────────────────────────────────────────────

runpod.serverless.start({"handler": handler})
