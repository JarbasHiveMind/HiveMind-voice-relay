# HiveMind Voice Relay — Documentation

**Local wakeword detection; STT and TTS handled remotely by hivemind-core running the hivemind-audio-binary-protocol plugin.**

---

## What is HiveMind Voice Relay?

HiveMind Voice Relay is a satellite client for the HiveMind mesh. It runs the microphone, voice-activity detection (VAD), and wakeword engine on-device, but forwards audio to **hivemind-core** running the **hivemind-audio-binary-protocol** plugin for speech-to-text (STT). The server synthesises speech (TTS) and sends audio back for local playback.

This makes it the middle-ground option: wakeword privacy and low activation latency without the resource cost of running STT/TTS models locally.

---

## Satellite spectrum

| Satellite | Mic | VAD | Wake word | STT | TTS | Connects to |
|---|---|---|---|---|---|---|
| [HiveMind-cli](https://github.com/JarbasHiveMind/HiveMind-cli) | — | — | — | — | — | hivemind-core |
| [hivemind-mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) | local | local | **server** | server | server | core + audio-binary-protocol |
| **HiveMind-voice-relay** | local | local | **local** | server | server | **core + audio-binary-protocol** |
| [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) | local | local | local | local | local | hivemind-core |

**Choose voice-relay when:**
- You want wakeword detection to happen on-device (latency, privacy — audio is not streamed until activation).
- You do not want to run STT or TTS models on the device (CPU/memory constraints).
- Your `hivemind-core` server has the `hivemind-audio-binary-protocol` plugin installed.

---

## Navigation

| Page | Audience |
|---|---|
| [Getting started](getting-started.md) | First-time users |
| [Configuration](configuration.md) | Plugin setup, all CLI flags |
| [Architecture](architecture.md) | How the relay pipeline works internally |
| [Deployment](deployment.md) | systemd, Raspberry Pi, autostart |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |

---

## Quick links

- [GitHub](https://github.com/JarbasHiveMind/HiveMind-voice-relay)
- [PyPI](https://pypi.org/project/HiveMind-voice-relay/)
- [hivemind-audio-binary-protocol (required server-side plugin)](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol)
- [OVOS plugin documentation](https://openvoiceos.github.io/ovos-technical-manual/)
