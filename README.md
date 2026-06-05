# HiveMind Voice Relay

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/HiveMind-voice-relay)](https://pypi.org/project/HiveMind-voice-relay/)
[![Python](https://img.shields.io/pypi/pyversions/HiveMind-voice-relay)](https://pypi.org/project/HiveMind-voice-relay/)

**Local wakeword detection; STT and TTS handled remotely by hivemind-core running the hivemind-audio-binary-protocol plugin.**

Voice Relay runs the microphone, VAD, and wakeword engine on-device — keeping wake-word detection private and low-latency — while forwarding audio to **hivemind-core** (running the **hivemind-audio-binary-protocol** plugin) for speech-to-text, and receiving synthesised audio back for playback. No STT or TTS models run on the device.

> Full documentation: **[docs/](docs/index.md)**

---

## Satellite spectrum

| Satellite | Mic | VAD | Wake word | STT | TTS | Connects to |
|---|---|---|---|---|---|---|
| [HiveMind-cli](https://github.com/JarbasHiveMind/HiveMind-cli) | — | — | — | — | — | hivemind-core |
| [hivemind-mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) | local | local | **server** | server | server | core + audio-binary-protocol |
| **HiveMind-voice-relay** (this repo) | local | local | **local** | server | server | **core + audio-binary-protocol** |
| [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) | local | local | local | local | local | hivemind-core |

Voice Relay is the middle-ground: wakeword detection stays on-device (low latency, no audio leaves until activation), while the heavier STT and TTS models run on the server.

---

## Server requirements

> ⚠️ **Your `hivemind-core` server must have the [hivemind-audio-binary-protocol](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol) binary plugin installed.** Plain `hivemind-core` does not handle STT or TTS — connecting to it will result in silence (no transcription, no spoken response).
>
> Alternatively, run `hivemind-core` together with `ovos-audio` and `ovos-dinkum-listener` to provide the same capabilities.

---

## Install

```bash
pip install HiveMind-voice-relay
```

---

## 60-second quickstart

**1. Configure identity** (one-time):

```bash
hivemind-client set-identity --key YOUR_ACCESS_KEY --password YOUR_PASSWORD --host wss://your-listener-host
```

**2. Run:**

```bash
hivemind-voice-relay
```

**3. Speak your wake word.** The default wake word is `hey mycroft` (configured in `~/.config/mycroft/mycroft.conf`).

---

## CLI flags

```
Usage: hivemind-voice-relay [OPTIONS]

  connect to hivemind-core running the audio binary protocol

Options:
  --host TEXT      hivemind host (ws:// or wss://)
  --key TEXT       Access Key
  --password TEXT  Password for key derivation
  --port INTEGER   HiveMind port number (default: 5678)
  --selfsigned     Accept self-signed TLS certificates
  --siteid TEXT    Location identifier for message context
  --help           Show this message and exit.
```

All flags fall back to values stored by `hivemind-client set-identity`.

---

## Configuration

Voice Relay reads `~/.config/mycroft/mycroft.conf` (standard OVOS config).

| Plugin type | Config key | Default | Required |
|---|---|---|---|
| Microphone | `microphone.module` | `ovos-microphone-plugin-alsa` | Yes |
| VAD | `listener.VAD.module` | `ovos-vad-plugin-silero` | Yes |
| Wake word | `listener.wake_word` | `hey_mycroft` | Yes |
| G2P | `tts.g2p_module` | — | No |
| Media Playback | `Audio.backends` | — | No |
| OCP Plugins | — | — | No |
| Dialog Transformers | — | — | No |
| TTS Transformers | — | — | No |
| PHAL | — | — | No (auto-loaded if installed) |

See [docs/configuration.md](docs/configuration.md) for full details and plugin swap instructions.

---

## Features and limitations

Built on [ovos-simple-listener](https://github.com/TigreGotico/ovos-simple-listener). Compared to the full voice-satellite:

**Present:**
- Microphone capture, VAD, wakeword detection — all local
- Audio forwarded to hivemind-core (hivemind-audio-binary-protocol plugin) for STT (base64-encoded WAV over the HiveMessage bus)
- TTS audio synthesised server-side and streamed back for local playback
- PHAL (platform hardware abstraction) auto-loaded if installed
- Standard OVOS plugin system for mic, VAD, and wakeword

**Not supported** (use [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) if you need these):
- Local STT / TTS plugins
- Audio Transformers
- Continuous / Hybrid / Recording / Sleep listening modes
- Multiple wake words

---

## Related

| Project | Role |
|---|---|
| [hivemind-audio-binary-protocol](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol) | Required `hivemind-core` plugin — provides server-side STT + TTS |
| [hivemind-core](https://github.com/JarbasHiveMind/HiveMind-core) | Base mesh node (no STT/TTS) |
| [HiveMind-cli](https://github.com/JarbasHiveMind/HiveMind-cli) | Text-only satellite |
| [hivemind-mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) | Thinnest audio satellite (no local wakeword) |
| [HiveMind-voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) | Full local stack satellite |
| [hivemind-bus-client](https://github.com/JarbasHiveMind/hivemind-bus-client) | HiveMind WebSocket client library |
| [ovos-simple-listener](https://github.com/TigreGotico/ovos-simple-listener) | Lightweight listener library used internally |

---

## License

[Apache-2.0](LICENSE)
