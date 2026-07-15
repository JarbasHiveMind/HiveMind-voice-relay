# Configuration

## CLI flags

All flags are optional when a node identity is stored via `hivemind-client set-identity`.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--host` | string | identity file | WebSocket URL or hostname of the `hivemind-core` server (running the `hivemind-audio-binary-protocol` plugin). A `ws://` scheme is prepended if no scheme is given. |
| `--key` | string | identity file | Access key issued by the server. |
| `--password` | string | identity file | Password used for key derivation. |
| `--port` | integer | identity file or `5678` | TCP port of the `hivemind-core` server. |
| `--selfsigned` | flag | false | Accept self-signed TLS certificates. Required when the server uses a certificate not trusted by your system. |
| `--siteid` | string | identity file or `"unknown"` | Location identifier added to message context. Useful when running multiple satellites. |

### Identity file

Credentials are resolved in order: CLI flag → identity file → error.

Manage the identity file with `hivemind-client`:

```bash
# Write
hivemind-client set-identity --key KEY --password PASS --host wss://host --port 5678

# Read
hivemind-client get-identity
```

The identity is stored at `~/.config/hivemind/identity2.json`.

---

## OVOS configuration

Voice Relay reads `~/.config/mycroft/mycroft.conf` (standard OVOS JSON config). Create or edit this file to configure plugins.

### Wake word

The wake word module and keyword are set under `listener`:

```json
{
  "listener": {
    "wake_word": "hey_mycroft"
  }
}
```

`wake_word` is the plugin entry-point name. To use a different wake word plugin, install it and set `wake_word` to its name.

Popular wake word plugins:

| Plugin | Entry-point name | Install |
|---|---|---|
| Precise Lite | `hey_mycroft` (default) | included with ovos-ww-plugin-precise-lite |
| OpenWakeWord | `hey_mycroft` (with openwakeword backend) | `pip install ovos-ww-plugin-openwakeword` |
| Vosk | depends on keyword | `pip install ovos-ww-plugin-vosk` |

Full list: [OVOS Wake Word Plugins](https://openvoiceos.github.io/ovos-technical-manual//312-wake_word_plugins/#list-of-wake-word-plugins)

### Microphone

```json
{
  "microphone": {
    "module": "ovos-microphone-plugin-alsa"
  }
}
```

The default `ovos-microphone-plugin-alsa` works for most Linux setups. For PyAudio:

```bash
pip install ovos-microphone-plugin-pyaudio
```

```json
{
  "microphone": {
    "module": "ovos-microphone-plugin-pyaudio"
  }
}
```

Full list: [OVOS Microphone Plugins](https://openvoiceos.github.io/ovos-technical-manual//310-mic_plugins/#microphone-plugins)

### VAD (Voice Activity Detection)

```json
{
  "listener": {
    "VAD": {
      "module": "ovos-vad-plugin-silero"
    }
  }
}
```

The default `ovos-vad-plugin-silero` works well in most environments. Alternatives:

| Plugin | Notes |
|---|---|
| `ovos-vad-plugin-silero` | Default, neural, accurate |
| `ovos-vad-plugin-webrtcvad` | Lighter, rule-based |

Full list: [OVOS VAD Plugins](https://openvoiceos.github.io/ovos-technical-manual//311-vad_plugins/#list-of-vad-plugins)

### Optional plugins

| Plugin type | Config path | Notes |
|---|---|---|
| G2P | `tts.g2p_module` | Grapheme-to-phoneme for mouth animation, not required for audio |
| Media Playback | `Audio.backends` | Enables media commands ("play Metallica") |
| OCP Plugins | n/a | URL resolvers for media backends |
| Dialog Transformers | n/a | Text post-processing before TTS request is sent |
| TTS Transformers | n/a | Audio post-processing after TTS audio received |
| PHAL | n/a | Platform hardware abstraction, auto-loaded if `ovos-PHAL` is installed |

### Transformer pipelines

The relay runs OVOS transformer plugins on-device, opt-in via this device's
`mycroft.conf`:

- **`audio_transformers`** — applied to captured speech before it is sent to
  the server for STT (e.g. denoise for a bad microphone).
- **`utterance_transformers`** — applied to the transcript before
  `recognizer_loop:utterance` is emitted; a plugin cancellation
  (OVOS-TRANSFORM §8.1, e.g. `ovos-utterance-plugin-cancel`) drops the
  utterance on-device.
- **`tts_transformers`** — applied to received TTS audio before playback
  (e.g. a per-device pitch or speed effect).

```json
{
  "utterance_transformers": {
    "ovos-utterance-plugin-cancel": {}
  },
  "tts_transformers": {
    "ovos-tts-transformer-sox-plugin": {"pitch": 300}
  }
}
```

Use device-side transformers for **per-device** effects; fleet-wide effects
belong on the server (hivemind-audio-binary-protocol / hivemind-core / a
shared tts-server). Remember the server may already rewrite things: TTS
audio saying **different text than the skill produced** usually means a
dialog transformer is centralizing a tone/persona server-side. Never enable
the same plugin on both sides, or the effect is applied twice. Full
contract: [ovos-plugin-manager transformer docs](https://github.com/OpenVoiceOS/ovos-plugin-manager/blob/dev/docs/transformers.md).

### Example mycroft.conf

```json
{
  "listener": {
    "wake_word": "hey_mycroft",
    "VAD": {
      "module": "ovos-vad-plugin-silero"
    }
  },
  "microphone": {
    "module": "ovos-microphone-plugin-alsa"
  }
}
```

---

## What is NOT configurable here

STT and TTS plugins are **not configured on the relay device**. They run on the `hivemind-core` server (via the `hivemind-audio-binary-protocol` plugin). Configure them in the server's OVOS config.

---
[← Getting started](getting-started.md) · [Home](index.md) · [Architecture →](architecture.md)
