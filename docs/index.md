# HiveMind Voice Relay — Documentation

**Local wakeword detection; STT and TTS handled remotely by hivemind-core running the hivemind-audio-binary-protocol plugin.**

---

## What is HiveMind Voice Relay?

HiveMind Voice Relay is a satellite client for the HiveMind mesh. It runs the microphone, voice-activity detection (VAD), and wakeword engine on-device, but forwards audio to **hivemind-core** running the **hivemind-audio-binary-protocol** plugin for speech-to-text (STT). The server synthesises speech (TTS) and sends audio back for local playback.

The point is architectural, not just resource savings: **the hive owns STT/TTS**. They run inside `hivemind-core` (via the `hivemind-audio-binary-protocol` plugin), **behind the same access-key authentication** as the rest of the mesh — so a relay does not, and cannot, choose its own STT/TTS engine, model, or voice. The hive operator decides, centrally, for every relay. (Contrast a [voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat), which can point at any plugin, including a public `ovos-stt-plugin-server`.) Relay also demonstrates the **base64 speech API** (`recognizer_loop:b64_transcribe` / `speak:b64_audio`) — the same job [mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) does over the binary protocol.

---

## Satellite spectrum

| Satellite | Mic | VAD | Wake word | STT | TTS | Connects to |
|---|---|---|---|---|---|---|
| [HiveMind-cli](https://github.com/JarbasHiveMind/HiveMind-cli) | — | — | — | — | — | hivemind-core |
| [hivemind-mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) | local | local | **server** | server | server | core + audio-binary-protocol |
| **HiveMind-voice-relay** | local | local | **local** | server | server | **core + audio-binary-protocol** |
| [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) | local | local | local | local | local | hivemind-core |

**Choose voice-relay when:**
- You want HiveMind to **own and govern STT/TTS as an authenticated service** — uniform engine/model/voice across all relays, decided by the hive operator, not the device.
- You want wakeword detection on-device (latency, privacy — audio is not streamed until activation).
- You do not want to run STT or TTS models on the device (a welcome consequence, not the main reason).
- Your `hivemind-core` server has the `hivemind-audio-binary-protocol` plugin installed.

---

## Navigation

| Page | Audience |
|---|---|
| [Getting started](getting-started.md) | First-time users |
| [Configuration](configuration.md) | Plugin setup, all CLI flags |
| [Architecture](architecture.md) | How the relay pipeline works internally |
| [Deployment](deployment.md) | systemd, Raspberry Pi, autostart |
| [Development & tests](development.md) | Install from source, run + understand the E2E suite |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |

---

## Quick links

- [GitHub](https://github.com/JarbasHiveMind/HiveMind-voice-relay)
- [PyPI](https://pypi.org/project/HiveMind-voice-relay/)
- [hivemind-audio-binary-protocol (required server-side plugin)](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol)
- [OVOS plugin documentation](https://openvoiceos.github.io/ovos-technical-manual/)
