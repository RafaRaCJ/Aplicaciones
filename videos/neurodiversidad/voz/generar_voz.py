#!/usr/bin/env python3
"""Genera la narración con la voz clonada en ElevenLabs (la clave la inyecta el entorno)."""
import json, sys, os, urllib.request
VOICE = "VHyaoTFDjvUbd3uKFxA1"  # Rafael Carriel Jordan (voz clonada)
KEY = os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")
here = os.path.dirname(os.path.abspath(__file__))
texts = json.load(open(os.path.join(here, "narracion.json")))
only = [int(x) for x in sys.argv[1:]] or range(1, len(texts) + 1)
for i in only:
    out = os.path.join(here, f"{i:02d}.mp3")
    prev = texts[i - 2] if i > 1 else None
    nxt = texts[i] if i < len(texts) else None
    body = {"text": texts[i - 1], "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2,
                               "use_speaker_boost": True, "speed": 0.95}}
    if prev: body["previous_text"] = prev
    if nxt: body["next_text"] = nxt
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=180) as r:
        open(out, "wb").write(r.read())
    print("ok", out, flush=True)
