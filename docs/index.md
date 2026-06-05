# HiveMind Voice Relay — Documentation

**Local wakeword detection; STT and TTS handled remotely by HiveMind-listener.**

---

## What is HiveMind Voice Relay?

HiveMind Voice Relay is a satellite client for the HiveMind mesh. It runs the microphone, voice-activity detection (VAD), and wakeword engine on-device, but forwards audio to a remote **HiveMind-listener** server for speech-to-text (STT). The server synthesises speech (TTS) and sends audio back for local playback.

This makes it the middle-ground option: wakeword privacy and low activation latency without the resource cost of running STT/TTS models locally.

---

## Satellite spectrum

| Satellite | Mic | VAD | Wake word | STT | TTS | Connects to |
|---|---|---|---|---|---|---|
| [HiveMind-cli](https://github.com/JarbasHiveMind/HiveMind-cli) | — | — | — | — | — | hivemind-core |
| [hivemind-mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) | local | local | **server** | server | server | HiveMind-listener |
| **HiveMind-voice-relay** | local | local | **local** | server | server | **HiveMind-listener** |
| [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) | local | local | local | local | local | hivemind-core |

**Choose voice-relay when:**
- You want wakeword detection to happen on-device (latency, privacy — audio is not streamed until activation).
- You do not want to run STT or TTS models on the device (CPU/memory constraints).
- You have a HiveMind-listener server available.

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
- [HiveMind-listener (required server)](https://github.com/JarbasHiveMind/HiveMind-listener)
- [OVOS plugin documentation](https://openvoiceos.github.io/ovos-technical-manual/)
