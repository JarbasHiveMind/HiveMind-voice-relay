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

Voice Relay keeps wakeword detection on-device (low latency, no audio leaves until activation) while STT and TTS run on the hive. The point is not mainly resource savings — it is **what it means for the hive to own speech services** (see below).

---

## Why voice-relay — HiveMind as a service

Voice-relay's real lesson is architectural. STT and TTS run *inside the hive* (the `hivemind-audio-binary-protocol` plugin on `hivemind-core`) and sit **behind the same access-key authentication** as the rest of the mesh. For a developer, the consequences matter more than the saved CPU:

- **The hive owns STT/TTS.** A [voice-sat](https://github.com/JarbasHiveMind/HiveMind-voice-sat) can point at any STT/TTS plugin it likes — including a public `ovos-stt-plugin-server` / `ovos-tts-plugin-server`. A relay **cannot**: it does not choose the engine, model, or voice. The **hive operator decides**, centrally and uniformly, for every relay that connects.
- **Speech is authenticated.** STT/TTS are not an open endpoint anyone can hit — access is gated by the client's HiveMind credentials, exactly like every other message on the protocol.
- **It is the reference for the b64 speech API.** The relay sends audio for STT and receives speech for TTS as base64-encoded WAV over the HiveMessage bus (`recognizer_loop:b64_transcribe`, `speak:b64_audio`) — the same work [mic-satellite](https://github.com/JarbasHiveMind/hivemind-mic-satellite) does over the binary protocol. Relay illustrates the b64 path; it could equally use binary.

Choose voice-relay when you want HiveMind to operate STT/TTS as a **governed, authenticated service** — uniform and centrally controlled — with wakeword kept local for latency and privacy. Lower device resource use is a consequence, not the goal.

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

## Development

Install from source with the end-to-end test extra, then run the suite:

```bash
uv pip install -e ".[e2e]"
pytest tests/
```

`pyproject.toml` is the single packaging source of truth. The E2E suite runs a
real `hivemind-core` master in-process and the real relay client over a real
`HiveMessageBusClient`, with the microphone/wakeword and the remote STT/TTS
endpoints mocked — see **[docs/development.md](docs/development.md)**.

---

## License

[Apache-2.0](LICENSE)
