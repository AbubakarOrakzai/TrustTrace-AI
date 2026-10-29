# ElevenLabs voice settings

## Selected voice

- **Voice:** Daniel — Steady Broadcaster
- **Voice ID:** `onwK4e9ZLuTAKqWW03F9`
- **Voice page:** <https://elevenlabs.io/voice-library?voiceId=onwK4e9ZLuTAKqWW03F9>
- **Use:** Clear, measured, professional narration. This premade voice is
  listed as available to the configured account.

## Generation settings

- **Model:** Eleven Multilingual v2 (`eleven_multilingual_v2`)
- **Speed:** `0.96` for a slightly measured, conversational pace
- **Stability:** `0.66` to keep chapter delivery consistent
- **Similarity boost:** `0.80`
- **Style:** `0` to avoid exaggerated delivery
- **Speaker boost:** On
- **Text normalization:** Automatic
- **Output:** MP3, 44.1 kHz, 128 kbps
- Use the same settings for each scene. Generate each scene in
  `elevenlabs-voiceover.txt` separately so the narration stays aligned to the
  video chapters. The completed video uses one narration clip per scene.

## Delivery direction

Read in a clear, professional, warm, confident educational tone. Keep the
pace medium and even. Use natural sentence pauses, articulate the technical
terms, and avoid dramatic emphasis or a sales-like delivery. Do not speak
scene labels.

## Pronunciation notes

- **Nebius:** “NEB-ee-us”
- **Nemotron:** “NEH-muh-tron”
- **FastAPI:** “fast A-P-I”
- **SQLite:** “S-Q-L-ite”
- **Ed25519:** “E-D twenty-five five nineteen”
- **SHA-256:** “S-H-A two five six”
- **JSON:** “J-S-O-N”
- **SQL:** “S-Q-L”
- **CRM:** “C-R-M”
- **HTTP:** “H-T-T-P”
- **AI:** “A-I”

The voiceover text spells out initialisms where needed to encourage clear
spoken pronunciation. Keep captions sourced from the normal project script,
not the pronunciation spellings.

## References

- [ElevenLabs text-to-speech best practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)
- [ElevenLabs create speech API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
