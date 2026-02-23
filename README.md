# Chatterbox TTS — RunPod Serverless Worker

Serverless GPU worker for [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) (500M params) on RunPod.

## Deployment

Connect this repo to a RunPod Serverless endpoint via **GitHub integration** (Settings > GitHub > Connect).

**GPU**: 24GB VRAM recommended (RTX 4090, A5000, etc.)

## API

### Single request

```json
{
  "input": {
    "text": "Hello world",
    "voice": "narrator",
    "exaggeration": 0.6,
    "cfg_weight": 0.5
  }
}
```

### Batch request

```json
{
  "input": {
    "segments": [
      {"id": "N1", "text": "First line", "voice": "narrator", "exaggeration": 0.7},
      {"id": "N2", "text": "Second line", "voice": "narrator", "exaggeration": 0.5}
    ]
  }
}
```

### Response

```json
{
  "audio_base64": "<base64 WAV>",
  "format": "wav",
  "sample_rate": 24000,
  "duration_s": 2.3,
  "gen_time_s": 1.1
}
```

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `exaggeration` | 0.6 | 0.0 - 1.5 | Emotion intensity (0=flat, 0.5=natural, 1.0+=dramatic) |
| `cfg_weight` | 0.5 | 0.0 - 1.0 | Text adherence (lower=more natural pacing) |

## Voice cloning

Place `.wav` reference clips in `voices/` directory (baked into the Docker image). Reference by filename (without extension) via the `voice` parameter.
