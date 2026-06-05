# Architecture

## Overview

HiveMind Voice Relay splits the voice pipeline across two machines:

```
Device (relay)                          Server (hivemind-core + audio-binary-protocol)
──────────────────────────────          ─────────────────────────────────────
Microphone → VAD → Wakeword             STT model → Intent / Skills → TTS model
                       │                     ↑                           │
                       └──── audio (b64 WAV) ─┘                          │
                                                                          │
Speaker ←────── TTS audio (b64 WAV) ──────────────────────────────────────┘
```

The connection between the two is a `hivemind-bus-client` WebSocket session carrying `HiveMessage` packets.

---

## On-device pipeline

The device side is implemented in `HiveMindVoiceRelay` (a subclass of `ovos_simple_listener.SimpleListener`).

```
OVOSMicrophoneFactory.create()
        │ raw audio frames
        ▼
OVOSVADFactory.create()
        │ speech / silence frames
        ▼
OVOSWakeWordFactory.create_hotword(wake_word)
        │ wakeword detected
        ▼
HiveMindSTT.execute(audio)   ← sends audio to server, blocks for response
        │ transcription
        ▼
HMCallbacks.text_callback()  ← emits recognizer_loop:utterance → HiveMind bus
```

The wake word name is read from `Configuration().get("listener", {}).get("wake_word", "hey_mycroft")` at startup.

### What happens on wakeword detection

`HMCallbacks.listen_callback()` fires internal bus events:
- `mycroft.audio.play_sound` — plays the start-listening chime locally.
- `recognizer_loop:wakeword` — notifies local PHAL/audio subsystems.
- `recognizer_loop:record_begin` — marks the start of recording.

After recording ends, `recognizer_loop:record_end` is emitted, then the audio is passed to `HiveMindSTT`.

---

## STT relay

`HiveMindSTT` is a thin `ovos_plugin_manager.templates.stt.STT` subclass. Instead of running a local model, it:

1. Encodes the captured `AudioData` as a base64 WAV string.
2. Emits `recognizer_loop:b64_transcribe` on the HiveMind bus, carrying `{"audio": "<b64>", "lang": "<lang>"}`.
3. Blocks (up to 20 seconds) on a threading `Event`, waiting for `recognizer_loop:b64_transcribe.response` from the server.
4. Returns the top-ranked transcription string.

On timeout or empty response, it returns an empty string and logs the error.

hivemind-core — via the `hivemind-audio-binary-protocol` plugin — receives the `b64_transcribe` message, runs its configured STT plugin, and sends back the response.

---

## TTS relay

`HMPlayback` is a subclass of `ovos_audio.service.PlaybackService`. When OVOS core (on the server) sends a `speak` message:

1. `execute_tts()` is called with the utterance text.
2. Instead of synthesising locally, it emits `speak:b64_audio` on the HiveMind bus.
3. The server synthesises audio and sends back `speak:b64_audio.response` with `{"audio": "<b64>", "utterance": "...", "listen": bool}`.
4. The relay decodes the base64 data, writes it to a temp WAV file, and puts the file path on the `TTS.queue` for playback by the local audio service.

This means audio is synthesised on the server with full TTS plugin support; the device only needs a speaker.

---

## HiveMind bus and session

The relay connects to the server using `HiveMessageBusClient` (from `hivemind-bus-client`):

```python
bus = HiveMessageBusClient(
    key=key,
    password=password,
    port=port,
    host=host,               # ws:// or wss://
    useragent="VoiceRelayV1.0.0",
    self_signed=selfsigned,
)
bus.connect(site_id=siteid)
```

The `site_id` is attached to all outbound messages as a location context, allowing the server to route responses to the correct satellite when multiple are connected.

Messages flow as `HiveMessage` packets over the WebSocket. OVOS-style `Message` objects are wrapped/unwrapped transparently by the client library.

---

## Server-side audio: the `hivemind-audio-binary-protocol` plugin

| | hivemind-core | core + audio-binary-protocol |
|---|---|---|
| Intent routing | Yes | Yes |
| Skills | Yes | Yes |
| STT (b64_transcribe) | **No** | **Yes** |
| TTS (speak:b64_audio) | **No** | **Yes** |
| Required by voice-relay | **No** | **Yes** |

`hivemind-core` is a base mesh node. It routes HiveMessages between satellites and an OVOS instance but does not itself process audio. The [`hivemind-audio-binary-protocol`](https://github.com/JarbasHiveMind/hivemind-audio-binary-protocol) binary plugin adds the listener service that handles the `b64_transcribe` and `speak:b64_audio` protocol messages that voice-relay depends on.

Connecting voice-relay to a plain `hivemind-core` node will result in wakeword triggering, audio being sent, and silence — the STT request will time out and no TTS will arrive.

---

## PHAL (optional)

If `ovos-PHAL` is installed, the relay loads it using the HiveMind bus as its internal bus:

```python
try:
    from ovos_PHAL.service import PHAL
    phal = PHAL(bus=bus)
    phal.start()
except ImportError:
    phal = None
```

PHAL plugins handle platform-specific hardware (LEDs, buttons, display on devices like the Mark 1). They are entirely optional.

---

## Trade-off summary

| Concern | mic-satellite | **voice-relay** | voice-sat |
|---|---|---|---|
| Audio streamed before wakeword | Yes | **No** | No |
| Wakeword latency | Server RTT | **Local** | Local |
| STT model on device | No | **No** | Yes |
| TTS model on device | No | **No** | Yes |
| Requires `hivemind-audio-binary-protocol` plugin | Yes | **Yes** | No |
| Device resource requirement | Minimal | Low | High |

Voice relay is the best fit when: the device is resource-constrained (no STT/TTS), privacy or latency of wakeword detection matters, and a `hivemind-core` server with the `hivemind-audio-binary-protocol` plugin is available.
